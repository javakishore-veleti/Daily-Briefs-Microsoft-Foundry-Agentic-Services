from typing import ClassVar, override

from middleware.adapters.azure.ms_foundry.objects_factory import ObjectsFactory
from middleware.common.dtos.weather_info_dtos import WeatherInfoCtx
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.facades.weather_info.interfaces import WeatherInfoTask


@log_methods
class AzureWeatherInfoTask(WeatherInfoTask):
    _instance: ClassVar["AzureWeatherInfoTask | None"] = None

    def __init__(self) -> None:
        super().__init__()
        self.name = "AzureWeatherInfoTask"
        self.description = "A task that can get weather information using Azure"

    @staticmethod
    def get_instance() -> "AzureWeatherInfoTask":
        if AzureWeatherInfoTask._instance is None:
            AzureWeatherInfoTask._instance = AzureWeatherInfoTask()
        return AzureWeatherInfoTask._instance

    @override
    def execute(self, ctx: WeatherInfoCtx) -> int:
        get_logger(__name__).info("session_id=%s", ctx.req.session_id)
        return ObjectsFactory.get_instance().get_weather_info_adapter().run(ctx)
