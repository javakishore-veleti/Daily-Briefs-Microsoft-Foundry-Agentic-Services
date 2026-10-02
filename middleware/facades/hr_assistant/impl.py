from typing import override

from middleware.adapters.daos.hr_sample_dataset import HrSampleDatasetService
from middleware.adapters.daos.objects_factory import ObjectsFactory as DaoObjectsFactory
from middleware.common.app_exec_contants import AppExecConstants
from middleware.common.dtos.hr_assistant_dtos import (
    HrAssistantCtx,
    HrFoundryMemoryClearResponse,
    HrSampleDatasetBulkPopulateResponse,
    HrSampleDatasetPopulateResponse,
    HrSampleDatasetStatusResponse,
    JoinerInfoResponse,
    JoinerListResponse,
)
from middleware.common.entity.joiner import JoinerInfo, JoinerPreferences
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.facades.hr_assistant.interfaces import HrAssistantFacade, HrAssistantTask
from middleware.facades.hr_assistant.tasks.azure_hr_assistant import AzureHrAssistantTask


@log_methods
class HrAssistantFacadeImpl(HrAssistantFacade):
    def __init__(self) -> None:
        super().__init__()
        self.tasks: list[HrAssistantTask] = []
        self.initialized = False
        self.sample_dataset = HrSampleDatasetService()

    @override
    def initialize(self) -> None:
        if self.initialized:
            return
        self.initialized = True
        self.tasks.append(AzureHrAssistantTask.get_instance())

    @override
    def execute(self, ctx: HrAssistantCtx) -> int:
        get_logger(__name__).info("session_id=%s joiner_info_id=%s", ctx.req.session_id, ctx.req.joiner_info_id)
        self.initialize()
        for task in self.tasks:
            if task.execute(ctx) != AppExecConstants.SUCCESS:
                return AppExecConstants.FAILURE
        return AppExecConstants.SUCCESS

    @override
    def list_joiners(
        self,
        joining_date_from: str,
        joining_date_to: str,
        limit: int,
        skip: int,
    ) -> JoinerListResponse:
        start = joining_date_from.strip()
        end = joining_date_to.strip()
        info_mgr = DaoObjectsFactory.get_instance().get_joiner_info_mgr()
        rows, has_more = info_mgr.page_for_date_range(
            start,
            end,
            limit,
            skip,
        )
        total = info_mgr.count_for_date_range(start, end)
        preferences = DaoObjectsFactory.get_instance().get_joiner_preferences_mgr()
        return JoinerListResponse(
            joining_date=start,
            joining_date_from=start,
            joining_date_to=end,
            joiners=[_joiner_response(row, preferences.for_joiner(row.id)) for row in rows],
            has_more=has_more,
            total=total,
            limit=limit,
            skip=skip,
        )

    @override
    def get_joiner(self, joiner_info_id: str) -> JoinerInfoResponse | None:
        dao = DaoObjectsFactory.get_instance()
        joiner = dao.get_joiner_info_mgr().get(joiner_info_id)
        if joiner is None:
            return None
        return _joiner_response(joiner, dao.get_joiner_preferences_mgr().for_joiner(joiner.id))

    @override
    def sample_dataset_status(self) -> HrSampleDatasetStatusResponse:
        return self.sample_dataset.status()

    @override
    def populate_sample_dataset(self) -> HrSampleDatasetPopulateResponse:
        return self.sample_dataset.populate(seed_memory=True)

    @override
    def populate_bulk_sample_dataset(self, seed_memory: bool = False) -> HrSampleDatasetBulkPopulateResponse:
        return self.sample_dataset.populate_bulk(seed_memory=seed_memory)

    @override
    def clear_foundry_memory(self) -> HrFoundryMemoryClearResponse:
        return self.sample_dataset.clear_foundry_memory()


def _joiner_response(joiner: JoinerInfo, preferences: JoinerPreferences | None) -> JoinerInfoResponse:
    return JoinerInfoResponse(
        id=joiner.id,
        first_name=joiner.first_name,
        middle_name=joiner.middle_name,
        last_name=joiner.last_name,
        email=joiner.email,
        contact_phone=joiner.contact_phone,
        contact_address=joiner.contact_address,
        interviewed_by_employee_ids=list(joiner.interviewed_by_employee_ids or []),
        interviewed_by_employee_names=list(joiner.interviewed_by_employee_names or []),
        official_role_name=joiner.official_role_name,
        internal_role_name=joiner.internal_role_name,
        joining_official_role_name=joiner.joining_official_role_name,
        salary_accepted_usd=float(joiner.salary_accepted_usd or 0),
        joining_date=joiner.joining_date,
        resumes=preferences.resumes if preferences is not None else "",
        personal_interests=preferences.personal_interests if preferences is not None else "",
        food_preferences=preferences.food_preferences if preferences is not None else "",
    )
