from pydantic import BaseModel


class AppReq(BaseModel):
    pass


class AppResp(BaseModel):
    pass


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
