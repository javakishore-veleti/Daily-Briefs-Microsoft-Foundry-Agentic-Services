from typing import ClassVar
from middleware.facades.web_search.impl import WebSearchFacadeImpl
from middleware.facades.web_search.interfaces import WebSearchFacade


class ObjectsFactory:
    _instance: ClassVar["ObjectsFactory | None"] = None

    def __init__(self) -> None:
        self.facades: dict[str, WebSearchFacade] = {}
        self.initialized = False
        
    @staticmethod
    def get_instance() -> "ObjectsFactory":
        if ObjectsFactory._instance is None:
            ObjectsFactory._instance = ObjectsFactory()
        return ObjectsFactory._instance

    def get_web_search_facade(self) -> WebSearchFacade:
        if "web_search_facade" not in self.facades:
            self.facades["web_search_facade"] = WebSearchFacadeImpl()
        return self.facades["web_search_facade"]