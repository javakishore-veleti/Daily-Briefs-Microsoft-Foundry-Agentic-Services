from middleware.common.dtos.hr_assistant_dtos import (
    HrAssistantCtx,
    HrFoundryMemoryClearResponse,
    HrSampleDatasetBulkPopulateResponse,
    HrSampleDatasetPopulateResponse,
    HrSampleDatasetStatusResponse,
    JoinerInfoResponse,
    JoinerListResponse,
)
from middleware.common.utils.logger_util import log_methods


@log_methods
class HrAssistantTask:
    def execute(self, ctx: HrAssistantCtx) -> int:
        raise NotImplementedError("Subclasses must implement this method")


@log_methods
class HrAssistantFacade:
    def initialize(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def execute(self, ctx: HrAssistantCtx) -> int:
        raise NotImplementedError("Subclasses must implement this method")

    def list_joiners(
        self,
        joining_date_from: str,
        joining_date_to: str,
        limit: int,
        skip: int,
    ) -> JoinerListResponse:
        raise NotImplementedError("Subclasses must implement this method")

    def get_joiner(self, joiner_info_id: str) -> JoinerInfoResponse | None:
        raise NotImplementedError("Subclasses must implement this method")

    def sample_dataset_status(self) -> HrSampleDatasetStatusResponse:
        raise NotImplementedError("Subclasses must implement this method")

    def populate_sample_dataset(self) -> HrSampleDatasetPopulateResponse:
        raise NotImplementedError("Subclasses must implement this method")

    def populate_bulk_sample_dataset(self, seed_memory: bool = False) -> HrSampleDatasetBulkPopulateResponse:
        raise NotImplementedError("Subclasses must implement this method")

    def clear_foundry_memory(self) -> HrFoundryMemoryClearResponse:
        raise NotImplementedError("Subclasses must implement this method")
