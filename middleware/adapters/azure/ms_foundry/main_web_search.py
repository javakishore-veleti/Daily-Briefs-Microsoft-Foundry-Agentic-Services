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
        usage = response.usage
        input_tokens = usage.input_tokens if usage is not None else 0
        output_tokens = usage.output_tokens if usage is not None else 0
        total_tokens = usage.total_tokens if usage is not None else 0
        cached_tokens = (
            usage.input_tokens_details.cached_tokens
            if usage is not None and usage.input_tokens_details is not None
            else 0
        )
        reasoning_tokens = (
            usage.output_tokens_details.reasoning_tokens
            if usage is not None and usage.output_tokens_details is not None
            else 0
        )
        ctx.resp.results["output_text"] = response.output_text
        ctx.resp.results["response_id"] = response.id
        ctx.resp.results["model"] = response.model
        ctx.resp.results["status"] = str(response.status)
        ctx.resp.ctx_data["conversation_id"] = conversation_id
        ctx.resp.usage.input_tokens = input_tokens
        ctx.resp.usage.output_tokens = output_tokens
        ctx.resp.usage.total_tokens = total_tokens
        ctx.resp.usage.cached_tokens = cached_tokens
        ctx.resp.usage.reasoning_tokens = reasoning_tokens
        get_logger(__name__).info(
            "session_id=%s conversation_id=%s response_id=%s model=%s status=%s input_tokens=%s output_tokens=%s total_tokens=%s cached_tokens=%s reasoning_tokens=%s",
            ctx.req.session_id,
            conversation_id,
            response.id,
            response.model,
            response.status,
            input_tokens,
            output_tokens,
            total_tokens,
            cached_tokens,
            reasoning_tokens,
        )
        return AppExecConstants.SUCCESS