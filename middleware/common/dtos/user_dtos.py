from datetime import datetime

from middleware.common.dtos.common import AppCtx, AppReq, AppResp
from middleware.common.utils.logger_util import log_methods


@log_methods
class SignupReq(AppReq):
    email: str = ""
    password: str = ""
    name: str = ""
    phone: str = ""


@log_methods
class SigninReq(AppReq):
    email: str = ""
    password: str = ""


@log_methods
class ForgotPasswordReq(AppReq):
    email: str = ""


@log_methods
class ResetPasswordReq(AppReq):
    email: str = ""
    reset_code: str = ""
    password: str = ""


@log_methods
class UserProfileUpdateReq(AppReq):
    name: str = ""
    email: str = ""
    phone: str = ""
    password: str = ""


@log_methods
class UserCommand(AppReq):
    action: str = ""
    user_id: str = ""
    email: str = ""
    password: str = ""
    name: str = ""
    phone: str = ""
    reset_code: str = ""


@log_methods
class UserResult(AppResp):
    status_code: int = 200
    detail: str = ""
    id: str = ""
    name: str = ""
    email: str = ""
    phone: str = ""
    created_at: datetime | None = None
    reset_code: str = ""


@log_methods
class UserPublicResponse(AppResp):
    id: str = ""
    name: str = ""
    email: str = ""
    phone: str = ""
    created_at: datetime | None = None


@log_methods
class ForgotPasswordResponse(AppResp):
    detail: str = ""
    reset_code: str = ""


@log_methods
class UserCtx(AppCtx[UserCommand, UserResult]):
    def __init__(self, req: UserCommand, resp: UserResult):
        super().__init__(req, resp)
