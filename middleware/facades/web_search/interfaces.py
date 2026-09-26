from middleware.common.dtos.web_search_dtos import WebSearchCtx

class WebSearchTask:
    def execute(self, ctx: WebSearchCtx) -> int:
        raise NotImplementedError("Subclasses must implement this method")

class WebSearchFacade:
    def execute(self, ctx: WebSearchCtx) -> int:
        raise NotImplementedError("Subclasses must implement this method")