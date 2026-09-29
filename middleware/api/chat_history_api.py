from fastapi import HTTPException

from middleware.adapters.daos.objects_factory import ObjectsFactory as DaoObjectsFactory
from middleware.common.app_module import AppModule
from middleware.common.dtos.chat_history_dtos import (
    ChatHistoryListResponse,
    ChatHistoryMessageResponse,
    ChatHistorySessionResponse,
)
from middleware.common.entity.chat_history import ChatHistory
from middleware.common.utils.logger_util import get_logger, log_methods


@log_methods
class ChatHistoryApi:
    def latest(
        self,
        brief: str,
        user_id: str,
        limit: int = 10,
        skip: int = 0,
        joiner_info_id: str = "",
    ) -> ChatHistoryListResponse:
        app_module = AppModule.from_brief(brief)
        if not app_module:
            raise HTTPException(
                status_code=400,
                detail="brief must be daily-briefs-search, weather-agent, or hr-daily-brief",
            )
        from middleware.api.objects_factory import ObjectsFactory as ApiObjectsFactory

        signed_in = ApiObjectsFactory.get_instance().get_user_api().require(user_id)
        return self._latest(app_module, signed_in, limit, skip, joiner_info_id)

    def _latest(
        self,
        app_module: str,
        user_id: str,
        limit: int,
        skip: int,
        joiner_info_id: str,
    ) -> ChatHistoryListResponse:
        logger = get_logger(__name__)
        logger.info("app_module=%s user_id=%s limit=%s skip=%s", app_module, user_id, limit, skip)
        dao = DaoObjectsFactory.get_instance()
        owned = dao.get_chat_session_mgr().ids_for_user(user_id)
        sessions, has_more = dao.get_chat_history_mgr().latest_sessions(
            app_module,
            limit,
            skip,
            owned,
            joiner_info_id,
        )
        return ChatHistoryListResponse(
            sessions=[self._session(item) for item in sessions],
            has_more=has_more,
        )

    def _session(self, item: dict) -> ChatHistorySessionResponse:
        messages = item.get("messages", [])
        return ChatHistorySessionResponse(
            session_id=str(item.get("session_id", "")),
            conversation_id=str(item.get("conversation_id", "")),
            title=str(item.get("title", "")),
            created_at=item.get("created_at"),
            updated_at=item.get("updated_at"),
            messages=[
                part
                for message in messages
                if isinstance(message, ChatHistory)
                for part in self._parts(message)
            ],
        )

    def _parts(self, message: ChatHistory) -> list[ChatHistoryMessageResponse]:
        sequence = int(getattr(message, "sequence", 0) or 0)
        prompt_id = str(getattr(message, "user_prompt_id", "") or "").strip()
        response = str(getattr(message, "agent_response", "") or "").strip()
        if prompt_id:
            if not response:
                return []
            return [self._part(message, "assistant", response, message.id, sequence)]
        prompt = str(getattr(message, "user_prompt", "") or "").strip()
        if prompt:
            return [self._part(message, "user", prompt, message.id, sequence)]
        text = str(getattr(message, "message", "") or "").strip()
        if not text:
            return []
        role = str(getattr(message, "role", "") or "") or "assistant"
        return [self._part(message, role, text, message.id, sequence)]

    def _part(
        self,
        message: ChatHistory,
        role: str,
        text: str,
        part_id: str,
        sequence: int,
    ) -> ChatHistoryMessageResponse:
        return ChatHistoryMessageResponse(
            id=part_id,
            role=role,
            message=text,
            sequence=sequence,
            created_at=message.created_at,
            conversation_id=message.conversation_id,
        )
