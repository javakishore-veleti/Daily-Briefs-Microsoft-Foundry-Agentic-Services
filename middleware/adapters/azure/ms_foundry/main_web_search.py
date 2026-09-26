from middleware.adapters.azure.ms_foundry.constants import AGENT_NAME_WEB_SEARCH
from middleware.adapters.azure.ms_foundry.objects_factory import ObjectsFactory
from middleware.common.dtos.web_search_dtos import WebSearchCtx


class WebSearchAdapter:
    def __init__(self):
        self.name = "WebSearchAdapter"
        self.description = "An adapter that can search the web for information"

    def run(self, ctx: WebSearchCtx) -> int:
        objects_factory = ObjectsFactory.get_instance()
        objects_factory.get_open_ai_client().responses.create(
            conversation=conversation.id,
            extra_body={
                "agent": {
                    "name": AGENT_NAME_WEB_SEARCH
                }
            }
        )

        return 0