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
    joiners: list[JoinerInfoResponse] = Field(default_factory=list)
    has_more: bool = False
