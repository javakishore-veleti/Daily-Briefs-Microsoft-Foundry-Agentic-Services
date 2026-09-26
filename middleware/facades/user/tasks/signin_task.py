from typing import ClassVar, override

from middleware.adapters.daos.objects_factory import ObjectsFactory
from middleware.common.app_exec_contants import AppExecConstants
from middleware.common.dtos.user_dtos import UserCtx
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.common.utils.password_hasher import PasswordHasher
from middleware.facades.user.account import UserAccount
from middleware.facades.user.interfaces import UserTask


@log_methods
class SigninTask(UserTask):
    _instance: ClassVar["SigninTask | None"] = None

    def __init__(self) -> None:
        super().__init__()
        self.name = "SigninTask"
        self.description = "Signs in a chat user with email and password"

    @staticmethod
    def get_instance() -> "SigninTask":
        if SigninTask._instance is None:
            SigninTask._instance = SigninTask()
        return SigninTask._instance

    @override
    def execute(self, ctx: UserCtx) -> int:
        try:
            email = UserAccount.login(ctx.req.email)
        except ValueError as error:
            return UserAccount.reject(ctx, 400, str(error))
        if not ctx.req.password:
            return UserAccount.reject(ctx, 400, "Enter your password.")
        user = ObjectsFactory.get_instance().get_chat_user_mgr().find_by_email(email)
        if not UserAccount.signed_in(user) or user is None or not PasswordHasher.verify(ctx.req.password, user.password_hash):
            return UserAccount.reject(ctx, 401, "Email or password is incorrect.")
        get_logger(__name__).info("email=%s user_id=%s signed in", email, user.id)
        UserAccount.fill(ctx, user)
        return AppExecConstants.SUCCESS
