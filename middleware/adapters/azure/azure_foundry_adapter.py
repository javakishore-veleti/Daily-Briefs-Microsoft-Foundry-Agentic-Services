from middleware.adapters.azure.ms_foundry.objects_factory import ObjectsFactory
from middleware.common.dtos.common import AppReq, AppResp
from middleware.common.interfaces.adapters import AppAdapter
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.common.utils.session_cache import SessionCache


@log_methods
class AzureMsFoundryAppAdapter[ReqT: AppReq, RespT: AppResp](AppAdapter[ReqT, RespT]):
    def get_or_create_conversation_id(self, session_id: str, objects_factory: ObjectsFactory) -> str:
        session_cache = SessionCache.get_instance()
        session = session_cache.get(session_id)
        logger = get_logger(__name__)
        conversation_id = session.get("conversation_id")
        if isinstance(conversation_id, str) and conversation_id:
            logger.info("session_id=%s conversation_id=%s reused", session_id, conversation_id)
            return conversation_id

        conversation = objects_factory.get_open_ai_client().conversations.create()
        conversation_id = conversation.id
        session_cache.set(session_id, {**session, "conversation_id": conversation_id})
        logger.info("session_id=%s conversation_id=%s created", session_id, conversation_id)
        return conversation_id
