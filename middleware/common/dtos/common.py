from pydantic import BaseModel

from middleware.common.utils.logger_util import log_methods


@log_methods
class AppReq(BaseModel):
    pass


@log_methods
class AppResp(BaseModel):
    pass


@log_methods
class AppCtx[ReqT: AppReq, RespT: AppResp]:
    req: ReqT
    resp: RespT
    ctx_data: dict[str, object]

    def __init__(self, req: ReqT, resp: RespT, ctx_data: dict[str, object] | None = None) -> None:
        self.req = req
        self.resp = resp
        self.ctx_data = {} if ctx_data is None else ctx_data

    def get_req(self) -> ReqT:
        return self.req

    def get_resp(self) -> RespT:
        return self.resp

    def get_ctx_data(self) -> dict[str, object]:
        return self.ctx_data
