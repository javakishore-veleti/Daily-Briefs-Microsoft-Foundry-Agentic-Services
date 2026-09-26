from middleware.common.dtos.web_search_dtos import WebSearchCtx, WebSearchReq, WebSearchResp
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.facades.objects_factory import ObjectsFactory


@log_methods
class WebSearchApi:

    def web_search(self, req: WebSearchReq) -> dict[str, str]:
        logger = get_logger(__name__)
        logger.info("session_id=%s", req.session_id)
        ctx = WebSearchCtx(req=req, resp=WebSearchResp(results={}))
        ObjectsFactory.get_instance().get_web_search_facade().execute(ctx)
        logger.info(
            "session_id=%s conversation_id=%s",
            req.session_id,
            ctx.resp.ctx_data.get("conversation_id", ""),
        )
        return ctx.resp.results