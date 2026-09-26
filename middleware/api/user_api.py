from fastapi import HTTPException

from middleware.common.app_exec_contants import AppExecConstants
from middleware.common.dtos.user_dtos import (
    ForgotPasswordReq,
    ForgotPasswordResponse,
    ResetPasswordReq,
    SigninReq,
    SignupReq,
    UserCommand,
    UserCtx,
    UserProfileUpdateReq,
    UserPublicResponse,
    UserResult,
)
from middleware.common.utils.logger_util import log_methods
from middleware.facades.objects_factory import ObjectsFactory


@log_methods
class UserApi:
    def signup(self, req: SignupReq) -> UserPublicResponse:
        result = self._run(
            UserCommand(
                action="signup",
                email=req.email,
                password=req.password,
                name=req.name,
                phone=req.phone,
            )
        )
        return self._public(result)

    def signin(self, req: SigninReq) -> UserPublicResponse:
        result = self._run(UserCommand(action="signin", email=req.email, password=req.password))
        return self._public(result)

    def forgot_password(self, req: ForgotPasswordReq) -> ForgotPasswordResponse:
        result = self._run(UserCommand(action="forgot-password", email=req.email))
        return ForgotPasswordResponse(detail=result.detail, reset_code=result.reset_code)

    def reset_password(self, req: ResetPasswordReq) -> UserPublicResponse:
        result = self._run(
            UserCommand(
                action="reset-password",
                email=req.email,
                reset_code=req.reset_code,
                password=req.password,
            )
        )
        return self._public(result)

    def get_profile(self, user_id: str) -> UserPublicResponse:
        return self._public(self._run(UserCommand(action="get", user_id=user_id)))

    def update_profile(self, user_id: str, req: UserProfileUpdateReq) -> UserPublicResponse:
        result = self._run(
            UserCommand(
                action="update",
                user_id=user_id,
                name=req.name,
                email=req.email,
                phone=req.phone,
                password=req.password,
            )
        )
        return self._public(result)

    def delete_profile(self, user_id: str) -> UserPublicResponse:
        result = self._run(UserCommand(action="delete", user_id=user_id))
        return UserPublicResponse(id=result.id)

    def require(self, user_id: str) -> str:
        if not user_id.strip():
            raise HTTPException(status_code=401, detail="Sign in is required.")
        return self._run(UserCommand(action="get", user_id=user_id)).id

    def _run(self, command: UserCommand) -> UserResult:
        ctx = UserCtx(req=command, resp=UserResult())
        code = ObjectsFactory.get_instance().get_user_facade().execute(ctx)
        if code != AppExecConstants.SUCCESS or ctx.resp.status_code >= 400:
            status_code = ctx.resp.status_code if ctx.resp.status_code >= 400 else 400
            raise HTTPException(status_code=status_code, detail=ctx.resp.detail or "Sign in is required.")
        return ctx.resp

    def _public(self, result: UserResult) -> UserPublicResponse:
        return UserPublicResponse(
            id=result.id,
            name=result.name,
            email=result.email,
            phone=result.phone,
            created_at=result.created_at,
        )
