from middleware.common.dtos.user_dtos import UserCtx
from middleware.common.utils.logger_util import log_methods


@log_methods
class UserTask:
    def execute(self, ctx: UserCtx) -> int:
        raise NotImplementedError("Subclasses must implement this method")


@log_methods
class UserFacade:
    def initialize(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def execute(self, ctx: UserCtx) -> int:
        raise NotImplementedError("Subclasses must implement this method")
