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
    def latest(self, brief: str, limit: int = 10, skip: int = 0) -> ChatHistoryListResponse:
        app_module = AppModule.from_brief(brief)
        if not app_module:
            raise HTTPException(status_code=400, detail="brief must be daily-briefs-search or weather-agent")
        return self._latest(app_module, limit, skip)

    def _latest(self, app_module: str, limit: int, skip: int) -> ChatHistoryListResponse:
        logger = get_logger(__name__)
        logger.info("app_module=%s limit=%s skip=%s", app_module, limit, skip)
        sessions, has_more = DaoObjectsFactory.get_instance().get_chat_history_mgr().latest_sessions(
            app_module,
            limit,
            skip,
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
            messages=[self._message(message) for message in messages if isinstance(message, ChatHistory)],
        )

    def _message(self, message: ChatHistory) -> ChatHistoryMessageResponse:
        return ChatHistoryMessageResponse(
            id=message.id,
            role=message.role,
            message=message.message,
            created_at=message.created_at,
            conversation_id=message.conversation_id,
        )
