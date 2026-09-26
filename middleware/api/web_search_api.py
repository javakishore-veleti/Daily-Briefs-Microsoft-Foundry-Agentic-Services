from middleware.common.dtos.web_search_dtos import WebSearchCtx, WebSearchReq, WebSearchResp
from middleware.facades.objects_factory import ObjectsFactory


class WebSearchApi:

    def search(self, req: WebSearchReq) -> dict[str, str]:
        ctx = WebSearchCtx(req=req, resp=WebSearchResp(results={}))
        ObjectsFactory.get_instance().get_web_search_facade().execute(ctx)
        return ctx.resp.results