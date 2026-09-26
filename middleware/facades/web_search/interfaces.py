from middleware.common.dtos.web_search_dtos import WebSearchCtx
from middleware.common.utils.logger_util import log_methods

@log_methods
class WebSearchTask:
    def execute(self, ctx: WebSearchCtx) -> int:
        raise NotImplementedError("Subclasses must implement this method")

@log_methods
class WebSearchFacade:
    def initialize(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def execute(self, ctx: WebSearchCtx) -> int:
        raise NotImplementedError("Subclasses must implement this method")