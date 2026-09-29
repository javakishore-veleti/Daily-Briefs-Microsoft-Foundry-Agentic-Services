from typing import ClassVar
from middleware.facades.hr_assistant.impl import HrAssistantFacadeImpl
from middleware.facades.hr_assistant.interfaces import HrAssistantFacade
from middleware.facades.user.impl import UserFacadeImpl
from middleware.facades.weather_info.impl import WeatherInfoFacadeImpl
from middleware.facades.web_search.impl import WebSearchFacadeImpl
from middleware.common.utils.logger_util import log_methods
from middleware.facades.user.interfaces import UserFacade
from middleware.facades.weather_info.interfaces import WeatherInfoFacade
from middleware.facades.web_search.interfaces import WebSearchFacade


@log_methods
class ObjectsFactory:
    _instance: ClassVar["ObjectsFactory | None"] = None

    def __init__(self) -> None:
        self.facades: dict[str, WebSearchFacade | WeatherInfoFacade | UserFacade | HrAssistantFacade] = {}
        self.initialized = False
        
    @staticmethod
    def get_instance() -> "ObjectsFactory":
        if ObjectsFactory._instance is None:
            ObjectsFactory._instance = ObjectsFactory()
        return ObjectsFactory._instance

    def init(self) -> None:
        if self.initialized:
            return
        self.get_web_search_facade().initialize()
        self.get_weather_info_facade().initialize()
        self.get_hr_assistant_facade().initialize()
        self.get_user_facade().initialize()
        self.initialized = True

    def get_web_search_facade(self) -> WebSearchFacade:
        if "web_search_facade" not in self.facades:
            self.facades["web_search_facade"] = WebSearchFacadeImpl()
        return self.facades["web_search_facade"]

    def get_user_facade(self) -> UserFacade:
        if "user_facade" not in self.facades:
            self.facades["user_facade"] = UserFacadeImpl()
        return self.facades["user_facade"]

    def get_weather_info_facade(self) -> WeatherInfoFacade:
        if "weather_info_facade" not in self.facades:
            self.facades["weather_info_facade"] = WeatherInfoFacadeImpl()
        return self.facades["weather_info_facade"]

    def get_hr_assistant_facade(self) -> HrAssistantFacade:
        if "hr_assistant_facade" not in self.facades:
            self.facades["hr_assistant_facade"] = HrAssistantFacadeImpl()
        return self.facades["hr_assistant_facade"]