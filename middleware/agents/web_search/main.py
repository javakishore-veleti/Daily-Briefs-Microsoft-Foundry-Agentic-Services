from middleware.common.dtos.web_search_dtos import WebSearchCtx
from middleware.common.utils.logger_util import get_logger, log_methods


@log_methods
class WebSearchAgent:
    def __init__(self):
        self.name = "WebSearchAgent"
        self.description = "A agent that can search the web for information"

    def run(self, ctx: WebSearchCtx) -> int:
        get_logger(__name__).info("session_id=%s", ctx.req.session_id)
        return 0