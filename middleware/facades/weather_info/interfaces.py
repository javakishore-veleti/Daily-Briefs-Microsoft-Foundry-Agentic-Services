from middleware.common.dtos.weather_info_dtos import WeatherInfoCtx
from middleware.common.utils.logger_util import log_methods


@log_methods
class WeatherInfoTask:
    def execute(self, ctx: WeatherInfoCtx) -> int:
        raise NotImplementedError("Subclasses must implement this method")


@log_methods
class WeatherInfoFacade:
    def initialize(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def execute(self, ctx: WeatherInfoCtx) -> int:
        raise NotImplementedError("Subclasses must implement this method")
