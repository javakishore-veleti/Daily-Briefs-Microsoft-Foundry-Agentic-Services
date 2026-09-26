from typing import override

from middleware.common.app_exec_contants import AppExecConstants
from middleware.common.dtos.weather_info_dtos import WeatherInfoCtx
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.facades.weather_info.interfaces import WeatherInfoFacade, WeatherInfoTask
from middleware.facades.weather_info.tasks.azure_weather_info import AzureWeatherInfoTask


@log_methods
class WeatherInfoFacadeImpl(WeatherInfoFacade):
    def __init__(self) -> None:
        super().__init__()
        self.tasks: list[WeatherInfoTask] = []
        self.initialized = False

    @override
    def initialize(self) -> None:
        if self.initialized:
            return
        self.initialized = True
        self.tasks.append(AzureWeatherInfoTask.get_instance())

    @override
    def execute(self, ctx: WeatherInfoCtx) -> int:
        get_logger(__name__).info("session_id=%s", ctx.req.session_id)
        self.initialize()
        for task in self.tasks:
            if task.execute(ctx) != AppExecConstants.SUCCESS:
                return AppExecConstants.FAILURE
        return AppExecConstants.SUCCESS
