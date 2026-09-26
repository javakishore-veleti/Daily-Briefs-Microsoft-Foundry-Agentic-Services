from typing import ClassVar, override

from pymongo.errors import DuplicateKeyError

from middleware.adapters.daos.objects_factory import ObjectsFactory
from middleware.common.app_exec_contants import AppExecConstants
from middleware.common.dtos.user_dtos import UserCtx
from middleware.common.entity.chat_history import ChatUser
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.common.utils.password_hasher import PasswordHasher
from middleware.facades.user.account import UserAccount
from middleware.facades.user.interfaces import UserTask


@log_methods
class SignupTask(UserTask):
    _instance: ClassVar["SignupTask | None"] = None

    def __init__(self) -> None:
        super().__init__()
        self.name = "SignupTask"
        self.description = "Creates a chat user from an email and password"

    @staticmethod
    def get_instance() -> "SignupTask":
        if SignupTask._instance is None:
            SignupTask._instance = SignupTask()
        return SignupTask._instance

    @override
    def execute(self, ctx: UserCtx) -> int:
        try:
            email = UserAccount.email(ctx.req.email)
            password = UserAccount.password(ctx.req.password)
        except ValueError as error:
            return UserAccount.reject(ctx, 400, str(error))
        users = ObjectsFactory.get_instance().get_chat_user_mgr()
        if users.find_by_email(email) is not None:
            return UserAccount.reject(ctx, 409, "An account with that email already exists.")
        user = ChatUser()
        user.name = ctx.req.name.strip()
        user.email = email
        user.phone = ctx.req.phone.strip()
        user.password_hash = PasswordHasher.hash_password(password)
        try:
            users.store(user)
        except DuplicateKeyError:
            return UserAccount.reject(ctx, 409, "An account with that email already exists.")
        get_logger(__name__).info("email=%s user_id=%s signed up", email, user.id)
        UserAccount.fill(ctx, user)
        return AppExecConstants.SUCCESS
