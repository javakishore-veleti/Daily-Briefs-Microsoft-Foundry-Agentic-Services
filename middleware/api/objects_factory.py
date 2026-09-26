from typing import ClassVar

from middleware.api.chat_history_api import ChatHistoryApi
from middleware.api.user_api import UserApi
from middleware.api.weather_info_api import WeatherInfoApi
from middleware.api.web_search_api import WebSearchApi
from middleware.common.utils.logger_util import log_methods


@log_methods
class ObjectsFactory:
    _instance: ClassVar["ObjectsFactory | None"] = None

    def __init__(self) -> None:
        self.apis: dict[str, WebSearchApi | WeatherInfoApi | ChatHistoryApi | UserApi] = {}

    @staticmethod
    def get_instance() -> "ObjectsFactory":
        if ObjectsFactory._instance is None:
            ObjectsFactory._instance = ObjectsFactory()
        return ObjectsFactory._instance

    def get_web_search_api(self) -> WebSearchApi:
        if "web_search_api" not in self.apis:
            self.apis["web_search_api"] = WebSearchApi()
        return self.apis["web_search_api"]

    def get_chat_history_api(self) -> ChatHistoryApi:
        if "chat_history_api" not in self.apis:
            self.apis["chat_history_api"] = ChatHistoryApi()
        return self.apis["chat_history_api"]

    def get_user_api(self) -> UserApi:
        if "user_api" not in self.apis:
            self.apis["user_api"] = UserApi()
        return self.apis["user_api"]

    def get_weather_info_api(self) -> WeatherInfoApi:
        if "weather_info_api" not in self.apis:
            self.apis["weather_info_api"] = WeatherInfoApi()
        return self.apis["weather_info_api"]
