from typing import ClassVar

from middleware.api.web_search_api import WebSearchApi
from middleware.common.utils.logger_util import log_methods


@log_methods
class ObjectsFactory:
    _instance: ClassVar["ObjectsFactory | None"] = None

    def __init__(self) -> None:
        self.apis: dict[str, WebSearchApi] = {}

    @staticmethod
    def get_instance() -> "ObjectsFactory":
        if ObjectsFactory._instance is None:
            ObjectsFactory._instance = ObjectsFactory()
        return ObjectsFactory._instance

    def get_web_search_api(self) -> WebSearchApi:
        if "web_search_api" not in self.apis:
            self.apis["web_search_api"] = WebSearchApi()
        return self.apis["web_search_api"]
