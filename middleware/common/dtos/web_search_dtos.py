from uuid import uuid4

from pydantic import Field

from middleware.common.dtos.common import AppCtx, AppReq, AppResp
from middleware.common.utils.logger_util import log_methods

@log_methods
class WebSearchReq(AppReq):
    query: str = ""
    session_id: str = Field(default_factory=lambda: str(uuid4()))

@log_methods
class WebSearchResp(AppResp):
    results: dict[str, str] = Field(default_factory=dict)
    ctx_data: dict[str, str] = Field(default_factory=dict)

@log_methods
class WebSearchCtx(AppCtx[WebSearchReq, WebSearchResp]):
    def __init__(self, req: WebSearchReq, resp: WebSearchResp):
        super().__init__(req, resp)
