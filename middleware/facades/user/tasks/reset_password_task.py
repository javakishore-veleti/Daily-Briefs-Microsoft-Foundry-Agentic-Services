from datetime import datetime
from typing import ClassVar, override

from middleware.adapters.daos.objects_factory import ObjectsFactory
from middleware.common.app_exec_contants import AppExecConstants
from middleware.common.dtos.user_dtos import UserCtx
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.common.utils.password_hasher import PasswordHasher
from middleware.facades.user.account import UserAccount
from middleware.facades.user.interfaces import UserTask


@log_methods
class ResetPasswordTask(UserTask):
    _instance: ClassVar["ResetPasswordTask | None"] = None

    def __init__(self) -> None:
        super().__init__()
        self.name = "ResetPasswordTask"
        self.description = "Sets a new password when the reset code is valid"

    @staticmethod
    def get_instance() -> "ResetPasswordTask":
        if ResetPasswordTask._instance is None:
            ResetPasswordTask._instance = ResetPasswordTask()
        return ResetPasswordTask._instance

    @override
    def execute(self, ctx: UserCtx) -> int:
        try:
            email = UserAccount.login(ctx.req.email)
            password = UserAccount.password(ctx.req.password)
        except ValueError as error:
            return UserAccount.reject(ctx, 400, str(error))
        code = ctx.req.reset_code.strip()
        if not code:
            return UserAccount.reject(ctx, 400, "Enter the reset code.")
        users = ObjectsFactory.get_instance().get_chat_user_mgr()
        user = users.find_by_email(email)
        if not UserAccount.signed_in(user) or user is None or not user.reset_code_hash:
            return UserAccount.reject(ctx, 400, "That reset code is incorrect.")
        expires = user.reset_code_expires_at
        if expires is None or expires < datetime.now():
            return UserAccount.reject(ctx, 400, "That reset code has expired. Request a new one.")
        if not PasswordHasher.verify(code, user.reset_code_hash):
            return UserAccount.reject(ctx, 400, "That reset code is incorrect.")
        user.password_hash = PasswordHasher.hash_password(password)
        user.reset_code_hash = ""
        user.reset_code_expires_at = None
        users.update(user)
        get_logger(__name__).info("email=%s password reset", email)
        UserAccount.fill(ctx, user)
        return AppExecConstants.SUCCESS
