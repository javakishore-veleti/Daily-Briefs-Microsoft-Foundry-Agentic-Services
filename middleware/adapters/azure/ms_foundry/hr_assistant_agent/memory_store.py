from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    MemorySearchOptions,
    MemoryStoreDefaultDefinition,
    MemoryStoreDefaultOptions,
)
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError

from middleware.common.dtos.app_config import AppConfig
from middleware.common.utils.logger_util import get_logger, log_methods


@log_methods
class HrMemoryStore:
    def __init__(self) -> None:
        self.name = AppConfig.get_instance().get_hr_memory_store_name()

    def ensure(self, project_client: AIProjectClient) -> None:
        config = AppConfig.get_instance()
        self.name = config.get_hr_memory_store_name()
        embedding_model = config.get_text_embedding_model_name().strip()
        chat_model = config.get_model_deployment_name().strip()
        if not embedding_model or not chat_model:
            get_logger(__name__).info("hr memory store skipped because a model name is missing")
            return
        stores = project_client.beta.memory_stores
        profile_details = config.get_hr_memory_profile_details()
        try:
            existing = stores.get(self.name)
            if _profile_details(existing) == profile_details:
                get_logger(__name__).info("memory_store=%s found", self.name)
                return
            stores.delete(self.name)
            get_logger(__name__).info("memory_store=%s replaced so profile details match", self.name)
        except ResourceNotFoundError:
            pass
        except HttpResponseError:
            get_logger(__name__).exception("memory_store=%s lookup failed", self.name)
            return
        try:
            stores.create(
                name=self.name,
                definition=MemoryStoreDefaultDefinition(
                    chat_model=chat_model,
                    embedding_model=embedding_model,
                    options=MemoryStoreDefaultOptions(
                        user_profile_enabled=True,
                        chat_summary_enabled=True,
                        user_profile_details=config.get_hr_memory_profile_details(),
                    ),
                ),
                description="Memories for each new joiner in the HR daily brief",
            )
            get_logger(__name__).info("memory_store=%s created", self.name)
        except HttpResponseError:
            get_logger(__name__).exception("memory_store=%s create failed", self.name)

    def search(self, project_client: AIProjectClient, joiner_info_id: str, query: str) -> list[str]:
        self.name = AppConfig.get_instance().get_hr_memory_store_name()
        if not joiner_info_id.strip() or not query.strip():
            return []
        try:
            result = project_client.beta.memory_stores.search_memories(
                name=self.name,
                scope=joiner_info_id,
                items=[{"role": "user", "type": "message", "content": query}],
                options=MemorySearchOptions(max_memories=5),
            )
        except HttpResponseError:
            get_logger(__name__).exception("memory_store=%s search failed", self.name)
            return []
        lines: list[str] = []
        placeholders = 0
        for memory in getattr(result, "memories", None) or []:
            item = getattr(memory, "memory_item", None)
            content = str(getattr(item, "content", "") or "").strip()
            if not content:
                continue
            if content.endswith("(HTTP)"):
                placeholders += 1
                continue
            lines.append(content)
        get_logger(__name__).info(
            "memory_store=%s scope=%s memories=%s placeholders=%s",
            self.name,
            joiner_info_id,
            len(lines),
            placeholders,
        )
        return lines

    def remember(self, project_client: AIProjectClient, joiner_info_id: str, text: str) -> None:
        self.name = AppConfig.get_instance().get_hr_memory_store_name()
        if not joiner_info_id.strip() or not text.strip():
            return
        try:
            poller = project_client.beta.memory_stores.begin_update_memories(
                name=self.name,
                scope=joiner_info_id,
                items=[{"role": "user", "type": "message", "content": text}],
                update_delay=0,
            )
            poller.result()
        except HttpResponseError:
            get_logger(__name__).exception("memory_store=%s update failed", self.name)


def _profile_details(store: object) -> str:
    definition = getattr(store, "definition", None)
    options = getattr(definition, "options", None)
    details = getattr(options, "user_profile_details", None)
    return str(details or "").strip()
