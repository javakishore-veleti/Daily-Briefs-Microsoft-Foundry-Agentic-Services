from uuid import uuid4

from pydantic import Field

from middleware.common.dtos.common import AppCtx, AppReq, AppResp
from middleware.common.utils.logger_util import log_methods


@log_methods
class WeatherInfoReq(AppReq):
    query: str = ""
    session_id: str = Field(default_factory=lambda: str(uuid4()))


@log_methods
class WeatherInfoUsage(AppResp):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0


@log_methods
class WeatherInfoResp(AppResp):
    results: dict[str, str] = Field(default_factory=dict)
    ctx_data: dict[str, str] = Field(default_factory=dict)
    usage: WeatherInfoUsage = Field(default_factory=WeatherInfoUsage)


@log_methods
class WeatherInfoApiResponse(AppResp):
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
class WeatherInfoCtx(AppCtx[WeatherInfoReq, WeatherInfoResp]):
    def __init__(self, req: WeatherInfoReq, resp: WeatherInfoResp):
        super().__init__(req, resp)
