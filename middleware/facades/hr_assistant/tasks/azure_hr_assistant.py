from typing import ClassVar, override

from middleware.adapters.azure.ms_foundry.objects_factory import ObjectsFactory
from middleware.common.dtos.hr_assistant_dtos import HrAssistantCtx
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.facades.hr_assistant.interfaces import HrAssistantTask


@log_methods
class AzureHrAssistantTask(HrAssistantTask):
    _instance: ClassVar["AzureHrAssistantTask | None"] = None

    def __init__(self) -> None:
        super().__init__()
        self.name = "AzureHrAssistantTask"
        self.description = "A task that asks the HR assistant agent"

    @staticmethod
    def get_instance() -> "AzureHrAssistantTask":
        if AzureHrAssistantTask._instance is None:
            AzureHrAssistantTask._instance = AzureHrAssistantTask()
        return AzureHrAssistantTask._instance

    @override
    def execute(self, ctx: HrAssistantCtx) -> int:
        get_logger(__name__).info("session_id=%s joiner_info_id=%s", ctx.req.session_id, ctx.req.joiner_info_id)
        return ObjectsFactory.get_instance().get_hr_assistant_adapter().run(ctx)
