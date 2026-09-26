from middleware.common.dtos.user_dtos import UserCtx
from middleware.common.entity.chat_history import ANONYMOUS_USER_ID, ChatUser
from middleware.common.utils.logger_util import log_methods


@log_methods
class UserAccount:
    @staticmethod
    def login(value: str) -> str:
        login = value.strip().lower()
        if not login:
            raise ValueError("Enter your user name.")
        if "@" in login:
            return UserAccount.email(value)
        return login

    @staticmethod
    def email(value: str) -> str:
        email = value.strip().lower()
        domain = email.split("@")[-1] if "@" in email else ""
        if not email or "@" not in email or "." not in domain:
            raise ValueError("Enter an email address.")
        return email

    @staticmethod
    def password(value: str) -> str:
        if len(value) < 8:
            raise ValueError("Use a password with at least 8 characters.")
        return value

    @staticmethod
    def fill(ctx: UserCtx, user: ChatUser) -> None:
        ctx.resp.status_code = 200
        ctx.resp.detail = ""
        ctx.resp.id = user.id
        ctx.resp.name = user.name
        ctx.resp.email = user.email
        ctx.resp.phone = user.phone
        ctx.resp.created_at = user.created_at

    @staticmethod
    def reject(ctx: UserCtx, status_code: int, detail: str) -> int:
        ctx.resp.status_code = status_code
        ctx.resp.detail = detail
        return 1

    @staticmethod
    def signed_in(user: ChatUser | None) -> bool:
        return user is not None and user.id != ANONYMOUS_USER_ID and bool(user.email)
