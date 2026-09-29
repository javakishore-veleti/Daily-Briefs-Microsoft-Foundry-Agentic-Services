from uuid import uuid4

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
        user_id: str = "",
        joiner_info_id: str = "",
    ) -> None:
        factory = ObjectsFactory.get_instance()
        owner = user_id.strip()
        if not owner:
            owner = factory.get_chat_user_mgr().ensure_anonymous().id
        if session_id.strip():
            factory.get_chat_session_mgr().ensure(session_id, owner)
        mgr = factory.get_chat_history_mgr()
        prompt_text = user_text.strip()
        if not prompt_text and not assistant_text.strip():
            return
        prompt = (
            mgr.find_prompt(app_module, session_id, prompt_text, joiner_info_id) if prompt_text else None
        )
        if prompt is None and prompt_text:
            prompt = self._prompt(
                app_module,
                session_id,
                conversation_id,
                prompt_text,
                model_name,
                joiner_info_id,
            )
            prompt.sequence = mgr.next_prompt_sequence(app_module, session_id)
            mgr.store(prompt)
        if prompt is None or not assistant_text.strip():
            return
        response = self._response(
            app_module,
            session_id,
            conversation_id,
            prompt.id,
            assistant_text,
            mgr.next_response_sequence(prompt.id),
            model_name,
            joiner_info_id,
        )
        mgr.store(response)
        mgr.touch(prompt.id)

    def _prompt(
        self,
        app_module: str,
        session_id: str,
        conversation_id: str,
        user_text: str,
        model_name: str,
        joiner_info_id: str,
    ) -> ChatHistory:
        entry = self._base(app_module, session_id, conversation_id, model_name, joiner_info_id)
        entry.id = str(uuid4())
        entry.user_prompt = user_text
        del entry.agent_response
        del entry.user_prompt_id
        return entry

    def _response(
        self,
        app_module: str,
        session_id: str,
        conversation_id: str,
        user_prompt_id: str,
        assistant_text: str,
        sequence: int,
        model_name: str,
        joiner_info_id: str,
    ) -> ChatHistory:
        entry = self._base(app_module, session_id, conversation_id, model_name, joiner_info_id)
        entry.user_prompt_id = user_prompt_id
        entry.agent_response = assistant_text
        entry.sequence = sequence
        del entry.user_prompt
        return entry

    def _base(
        self,
        app_module: str,
        session_id: str,
        conversation_id: str,
        model_name: str,
        joiner_info_id: str,
    ) -> ChatHistory:
        entry = ChatHistory()
        entry.app_module = app_module
        entry.chat_session_id = session_id
        entry.conversation_id = conversation_id
        entry.model_name = model_name
        entry.joiner_info_id = joiner_info_id.strip()
        if not entry.joiner_info_id:
            del entry.joiner_info_id
        del entry.message
        del entry.role
        return entry
