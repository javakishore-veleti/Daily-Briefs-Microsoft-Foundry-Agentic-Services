from middleware.common.dtos.web_search_dtos import WebSearchCtx


class WebSearchAgent:
    def __init__(self):
        self.name = "WebSearchAgent"
        self.description = "A agent that can search the web for information"

    def run(self, ctx: WebSearchCtx) -> int:
        return 0