from typing import override

from pymongo.errors import DuplicateKeyError

from middleware.adapters.daos.objects_factory import ObjectsFactory as DaoObjectsFactory
from middleware.common.app_exec_contants import AppExecConstants
from middleware.common.dtos.user_dtos import UserCtx
from middleware.common.entity.chat_history import DEFAULT_USER_LOGIN, DEFAULT_USER_PASSWORD, ChatUser
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.common.utils.password_hasher import PasswordHasher
from middleware.facades.user.interfaces import UserFacade, UserTask
from middleware.facades.user.tasks.forgot_password_task import ForgotPasswordTask
from middleware.facades.user.tasks.reset_password_task import ResetPasswordTask
from middleware.facades.user.tasks.signin_task import SigninTask
from middleware.facades.user.tasks.signup_task import SignupTask
from middleware.facades.user.tasks.user_profile_task import UserProfileTask


@log_methods
class UserFacadeImpl(UserFacade):
    def __init__(self) -> None:
        super().__init__()
        self.tasks: dict[str, UserTask] = {}
        self.initialized = False

    @override
    def initialize(self) -> None:
        if self.initialized:
            return
        self._ensure_default_user()
        profile = UserProfileTask.get_instance()
        self.tasks = {
            "signup": SignupTask.get_instance(),
            "signin": SigninTask.get_instance(),
            "forgot-password": ForgotPasswordTask.get_instance(),
            "reset-password": ResetPasswordTask.get_instance(),
            "get": profile,
            "update": profile,
            "delete": profile,
        }
        self.initialized = True

    @override
    def execute(self, ctx: UserCtx) -> int:
        get_logger(__name__).info("action=%s", ctx.req.action)
        self.initialize()
        task = self.tasks.get(ctx.req.action)
        if task is None:
            ctx.resp.status_code = 400
            ctx.resp.detail = "Unknown user action."
            return AppExecConstants.FAILURE
        return task.execute(ctx)

    def _ensure_default_user(self) -> None:
        users = DaoObjectsFactory.get_instance().get_chat_user_mgr()
        if users.find_by_email(DEFAULT_USER_LOGIN) is not None:
            return
        user = ChatUser()
        user.name = "Enterprise User"
        user.email = DEFAULT_USER_LOGIN
        user.password_hash = PasswordHasher.hash_password(DEFAULT_USER_PASSWORD)
        try:
            users.store(user)
        except DuplicateKeyError:
            return
        get_logger(__name__).info("default user %s is ready", DEFAULT_USER_LOGIN)
