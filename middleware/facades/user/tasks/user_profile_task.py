from typing import ClassVar, override

from pymongo.errors import DuplicateKeyError

from middleware.adapters.daos.mongodb.impl.generic_entity_mgr import ChatUserMgr
from middleware.adapters.daos.objects_factory import ObjectsFactory
from middleware.common.app_exec_contants import AppExecConstants
from middleware.common.dtos.user_dtos import UserCtx
from middleware.common.entity.chat_history import ChatUser
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.common.utils.password_hasher import PasswordHasher
from middleware.facades.user.account import UserAccount
from middleware.facades.user.interfaces import UserTask


@log_methods
class UserProfileTask(UserTask):
    _instance: ClassVar["UserProfileTask | None"] = None

    def __init__(self) -> None:
        super().__init__()
        self.name = "UserProfileTask"
        self.description = "Reads, updates, and deletes a signed-in chat user"

    @staticmethod
    def get_instance() -> "UserProfileTask":
        if UserProfileTask._instance is None:
            UserProfileTask._instance = UserProfileTask()
        return UserProfileTask._instance

    @override
    def execute(self, ctx: UserCtx) -> int:
        users = ObjectsFactory.get_instance().get_chat_user_mgr()
        user = users.get(ctx.req.user_id.strip())
        if not UserAccount.signed_in(user) or user is None:
            return UserAccount.reject(ctx, 401, "Sign in is required.")
        if ctx.req.action == "get":
            UserAccount.fill(ctx, user)
            return AppExecConstants.SUCCESS
        if ctx.req.action == "delete":
            users.delete(user.id)
            get_logger(__name__).info("user_id=%s deleted", user.id)
            ctx.resp.status_code = 200
            ctx.resp.id = user.id
            ctx.resp.detail = "Account deleted."
            return AppExecConstants.SUCCESS
        return self._update(ctx, users, user)

    def _update(self, ctx: UserCtx, users: ChatUserMgr, user: ChatUser) -> int:
        try:
            email = UserAccount.email(ctx.req.email)
        except ValueError as error:
            return UserAccount.reject(ctx, 400, str(error))
        existing = users.find_by_email(email)
        if existing is not None and existing.id != user.id:
            return UserAccount.reject(ctx, 409, "An account with that email already exists.")
        user.name = ctx.req.name.strip()
        user.email = email
        user.phone = ctx.req.phone.strip()
        if ctx.req.password:
            try:
                password = UserAccount.password(ctx.req.password)
            except ValueError as error:
                return UserAccount.reject(ctx, 400, str(error))
            user.password_hash = PasswordHasher.hash_password(password)
        try:
            users.update(user)
        except DuplicateKeyError:
            return UserAccount.reject(ctx, 409, "An account with that email already exists.")
        get_logger(__name__).info("user_id=%s profile updated", user.id)
        UserAccount.fill(ctx, user)
        return AppExecConstants.SUCCESS
