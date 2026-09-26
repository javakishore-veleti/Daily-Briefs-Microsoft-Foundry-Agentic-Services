import secrets
from datetime import datetime, timedelta
from typing import ClassVar, override

from middleware.adapters.daos.objects_factory import ObjectsFactory
from middleware.common.app_exec_contants import AppExecConstants
from middleware.common.dtos.user_dtos import UserCtx
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.common.utils.password_hasher import PasswordHasher
from middleware.facades.user.account import UserAccount
from middleware.facades.user.interfaces import UserTask


@log_methods
class ForgotPasswordTask(UserTask):
    _instance: ClassVar["ForgotPasswordTask | None"] = None

    def __init__(self) -> None:
        super().__init__()
        self.name = "ForgotPasswordTask"
        self.description = "Creates a short-lived password reset code for an email"

    @staticmethod
    def get_instance() -> "ForgotPasswordTask":
        if ForgotPasswordTask._instance is None:
            ForgotPasswordTask._instance = ForgotPasswordTask()
        return ForgotPasswordTask._instance

    @override
    def execute(self, ctx: UserCtx) -> int:
        try:
            email = UserAccount.login(ctx.req.email)
        except ValueError as error:
            return UserAccount.reject(ctx, 400, str(error))
        users = ObjectsFactory.get_instance().get_chat_user_mgr()
        user = users.find_by_email(email)
        if not UserAccount.signed_in(user) or user is None:
            return UserAccount.reject(ctx, 404, "No account uses that email.")
        reset_code = f"{secrets.randbelow(1_000_000):06d}"
        user.reset_code_hash = PasswordHasher.hash_password(reset_code)
        user.reset_code_expires_at = datetime.now() + timedelta(minutes=15)
        users.update(user)
        get_logger(__name__).info("email=%s reset code created", email)
        ctx.resp.status_code = 200
        ctx.resp.detail = "Enter this reset code and a new password. The code expires in 15 minutes."
        ctx.resp.reset_code = reset_code
        return AppExecConstants.SUCCESS
