from middleware.adapters.daos.objects_factory import ObjectsFactory
from middleware.common.entity.chat_history import ChatHistory
from middleware.common.utils.logger_util import log_methods


@log_methods
class ChatHistoryRecorder:
    def record_turn(
        self,
        app_module: str,
        session_id: str,
        conversation_id: str,
        user_text: str,
        assistant_text: str,
        model_name: str,
    ) -> None:
        factory = ObjectsFactory.get_instance()
        user = factory.get_chat_user_mgr().ensure_anonymous()
        if session_id.strip():
            factory.get_chat_session_mgr().ensure(session_id, user.id)
        mgr = factory.get_chat_history_mgr()
        if user_text.strip():
            mgr.store(self._entry(app_module, session_id, conversation_id, "user", user_text, model_name))
        if assistant_text.strip():
            mgr.store(self._entry(app_module, session_id, conversation_id, "assistant", assistant_text, model_name))

    def _entry(
        self,
        app_module: str,
        session_id: str,
        conversation_id: str,
        role: str,
        text: str,
        model_name: str,
    ) -> ChatHistory:
        entry = ChatHistory()
        entry.app_module = app_module
        entry.chat_session_id = session_id
        entry.conversation_id = conversation_id
        entry.role = role
        entry.message = text
        entry.model_name = model_name
        return entry
