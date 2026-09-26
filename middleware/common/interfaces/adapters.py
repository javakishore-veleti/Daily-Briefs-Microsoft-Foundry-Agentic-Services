from middleware.common.dtos.common import AppCtx, AppReq, AppResp


class AppAdapter[ReqT: AppReq, RespT: AppResp]:
    def run(self, ctx: AppCtx[ReqT, RespT]) -> int:
        return 0
