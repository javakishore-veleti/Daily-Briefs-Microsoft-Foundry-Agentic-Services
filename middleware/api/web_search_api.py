from middleware.common.dtos.web_search_dtos import (
    WebSearchApiResponse,
    WebSearchCtx,
    WebSearchReq,
    WebSearchResp,
)
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.facades.objects_factory import ObjectsFactory


@log_methods
class WebSearchApi:

    def web_search(self, req: WebSearchReq) -> WebSearchApiResponse:
        logger = get_logger(__name__)
        logger.info("session_id=%s", req.session_id)
        ctx = WebSearchCtx(req=req, resp=WebSearchResp(results={}))
        ObjectsFactory.get_instance().get_web_search_facade().execute(ctx)
        conversation_id = ctx.resp.ctx_data.get("conversation_id", "")
        logger.info(
            "session_id=%s conversation_id=%s input_tokens=%s output_tokens=%s",
            req.session_id,
            conversation_id,
            ctx.resp.usage.input_tokens,
            ctx.resp.usage.output_tokens,
        )
        return WebSearchApiResponse(
            output_text=ctx.resp.results.get("output_text", ""),
            conversation_id=conversation_id,
            response_id=ctx.resp.results.get("response_id", ""),
            model=ctx.resp.results.get("model", ""),
            status=ctx.resp.results.get("status", ""),
            input_tokens=ctx.resp.usage.input_tokens,
            output_tokens=ctx.resp.usage.output_tokens,
            total_tokens=ctx.resp.usage.total_tokens,
            cached_tokens=ctx.resp.usage.cached_tokens,
            reasoning_tokens=ctx.resp.usage.reasoning_tokens,
        )