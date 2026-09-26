from typing import ClassVar, override

from middleware.adapters.azure.ms_foundry.objects_factory import ObjectsFactory
from middleware.common.dtos.web_search_dtos import WebSearchCtx
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.facades.web_search.interfaces import WebSearchTask


@log_methods
class AzureWebSearchTask(WebSearchTask):
    _instance: ClassVar["AzureWebSearchTask | None"] = None

    def __init__(self) -> None:
        super().__init__()
        self.name = "AzureWebSearchTask"
        self.description = "An task that can search the web for information using Azure"

    @staticmethod
    def get_instance() -> "AzureWebSearchTask":
        if AzureWebSearchTask._instance is None:
            AzureWebSearchTask._instance = AzureWebSearchTask()
        return AzureWebSearchTask._instance

    @override
    def execute(self, ctx: WebSearchCtx) -> int:
        get_logger(__name__).info("session_id=%s", ctx.req.session_id)
        return ObjectsFactory.get_instance().get_web_search_adapter().run(ctx)


