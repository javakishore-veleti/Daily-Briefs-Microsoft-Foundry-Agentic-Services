from uuid import uuid4

from pydantic import Field

from middleware.common.dtos.common import AppCtx, AppReq, AppResp

class WebSearchReq(AppReq):
    query: str = ""
    session_id: str = Field(default_factory=lambda: str(uuid4()))

class WebSearchResp(AppResp):
    results: dict[str, str] = Field(default_factory=dict)
    ctx_data: dict[str, str] = Field(default_factory=dict)

class WebSearchCtx(AppCtx[WebSearchReq, WebSearchResp]):
    def __init__(self, req: WebSearchReq, resp: WebSearchResp):
        super().__init__(req, resp)
