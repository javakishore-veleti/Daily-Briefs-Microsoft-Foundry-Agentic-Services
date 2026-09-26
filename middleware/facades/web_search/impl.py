from typing import override
from middleware.common.app_exec_contants import AppExecConstants
from middleware.common.dtos.web_search_dtos import WebSearchCtx
from middleware.facades.web_search.interfaces import WebSearchFacade, WebSearchTask
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.facades.web_search.tasks.azure_web_search import AzureWebSearchTask


@log_methods
class WebSearchFacadeImpl(WebSearchFacade):
    def __init__(self) -> None:
        super().__init__()
        self.tasks: list[WebSearchTask] = []
        self.initialized = False

    def initialize(self) -> None:
        if self.initialized:
            return
        self.initialized = True
        self.tasks.append(AzureWebSearchTask.get_instance())

    @override
    def execute(self, ctx: WebSearchCtx) -> int:
        get_logger(__name__).info("session_id=%s", ctx.req.session_id)
        self.initialize()
        for task in self.tasks:
            if task.execute(ctx) != AppExecConstants.SUCCESS:
                return AppExecConstants.FAILURE
        return AppExecConstants.SUCCESS