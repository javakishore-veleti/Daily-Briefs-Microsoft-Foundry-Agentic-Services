from typing import override

from middleware.adapters.azure.ms_foundry.constants import AGENT_NAME_WEB_SEARCH
from middleware.adapters.azure.ms_foundry.objects_factory import ObjectsFactory
from middleware.common.app_exec_contants import AppExecConstants
from middleware.common.dtos.common import AppCtx
from middleware.common.dtos.web_search_dtos import WebSearchReq, WebSearchResp
from middleware.common.interfaces.adapters import AppAdapter
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.common.utils.session_cache import SessionCache


@log_methods
class WebSearchAdapter(AppAdapter[WebSearchReq, WebSearchResp]):
    def __init__(self):
        self.name = "WebSearchAdapter"
        self.description = "An adapter that can search the web for information"

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

    @override
    def run(self, ctx: AppCtx[WebSearchReq, WebSearchResp]) -> int:
        objects_factory = ObjectsFactory.get_instance()
        conversation_id = self.get_or_create_conversation_id(ctx.req.session_id, objects_factory)
        get_logger(__name__).info(
            "session_id=%s conversation_id=%s",
            ctx.req.session_id,
            conversation_id,
        )

        response = objects_factory.get_open_ai_client().responses.create(
            conversation=conversation_id,
            extra_body={
                "agent_reference": {
                    "name": AGENT_NAME_WEB_SEARCH,
                    "type": "agent_reference",
                }
            },
            input = ctx.req.query
        )
        output_text = response.output_text
        ctx.resp.results["output_text"] = output_text
        ctx.resp.ctx_data["conversation_id"] = conversation_id
        return AppExecConstants.SUCCESS