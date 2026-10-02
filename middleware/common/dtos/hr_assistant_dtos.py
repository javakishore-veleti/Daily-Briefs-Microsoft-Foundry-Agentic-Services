from uuid import uuid4

from pydantic import Field

from middleware.common.dtos.common import AppCtx, AppReq, AppResp
from middleware.common.utils.logger_util import log_methods


@log_methods
class HrAssistantReq(AppReq):
    query: str = ""
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    joiner_info_id: str = ""


@log_methods
class HrAssistantUsage(AppResp):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0


@log_methods
class HrAssistantResp(AppResp):
    results: dict[str, str] = Field(default_factory=dict)
    ctx_data: dict[str, str] = Field(default_factory=dict)
    usage: HrAssistantUsage = Field(default_factory=HrAssistantUsage)


@log_methods
class HrAssistantApiResponse(AppResp):
    output_text: str = ""
    conversation_id: str = ""
    response_id: str = ""
    model: str = ""
    status: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    total_ms: int = 0
    memory_search_ms: int = 0
    memory_update_ms: int = 0
    agent_ms: int = 0
    slowest_step: str = ""
    slowest_ms: int = 0


@log_methods
class HrAssistantCtx(AppCtx[HrAssistantReq, HrAssistantResp]):
    def __init__(self, req: HrAssistantReq, resp: HrAssistantResp):
        super().__init__(req, resp)


@log_methods
class JoinerInfoResponse(AppResp):
    id: str = ""
    first_name: str = ""
    middle_name: str = ""
    last_name: str = ""
    email: str = ""
    contact_phone: str = ""
    contact_address: str = ""
    interviewed_by_employee_ids: list[str] = Field(default_factory=list)
    interviewed_by_employee_names: list[str] = Field(default_factory=list)
    official_role_name: str = ""
    internal_role_name: str = ""
    joining_official_role_name: str = ""
    salary_accepted_usd: float = 0
    joining_date: str = ""
    resumes: str = ""
    personal_interests: str = ""
    food_preferences: str = ""


@log_methods
class JoinerListResponse(AppResp):
    joining_date: str = ""
    joining_date_from: str = ""
    joining_date_to: str = ""
    joiners: list[JoinerInfoResponse] = Field(default_factory=list)
    has_more: bool = False
    total: int = 0
    limit: int = 10
    skip: int = 0


@log_methods
class HrSampleDatasetJoineeStatus(AppResp):
    folder: str = ""
    display_name: str = ""
    email: str = ""
    joiner_info_id: str = ""
    mongo_populated: bool = False
    memory_populated: bool = False
    joining_date: str = ""


@log_methods
class HrSampleDatasetStatusResponse(AppResp):
    dataset_path: str = ""
    joinee_count: int = 0
    populated: bool = False
    mongo_populated: bool = False
    memory_populated: bool = False
    populated_at: str = ""
    joinees: list[HrSampleDatasetJoineeStatus] = Field(default_factory=list)
    bulk_target_count: int = 1000
    bulk_span_days: int = 30
    bulk_mongo_count: int = 0
    bulk_populated: bool = False
    bulk_memory_seeded: bool = False
    bulk_populated_at: str = ""


@log_methods
class HrSampleDatasetPopulateResponse(AppResp):
    message: str = ""
    status: HrSampleDatasetStatusResponse = Field(default_factory=HrSampleDatasetStatusResponse)
    created: int = 0
    skipped: int = 0
    memory_seeded: int = 0


@log_methods
class HrSampleDatasetBulkPopulateResponse(AppResp):
    message: str = ""
    status: HrSampleDatasetStatusResponse = Field(default_factory=HrSampleDatasetStatusResponse)
    created: int = 0
    skipped: int = 0
    memory_seeded: int = 0
    target_count: int = 0
    span_days: int = 0
    seed_memory: bool = False


@log_methods
class HrFoundryMemoryClearResponse(AppResp):
    message: str = ""
    status: HrSampleDatasetStatusResponse = Field(default_factory=HrSampleDatasetStatusResponse)
    memory_store_name: str = ""
    cleared: bool = False
