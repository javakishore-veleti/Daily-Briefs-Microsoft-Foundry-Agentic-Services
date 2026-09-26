from middleware.common.dtos.common import AppCtx, AppReq, AppResp
from middleware.common.utils.logger_util import log_methods


@log_methods
class AppAdapter[ReqT: AppReq, RespT: AppResp]:
    def run(self, ctx: AppCtx[ReqT, RespT]) -> int:
        return 0
