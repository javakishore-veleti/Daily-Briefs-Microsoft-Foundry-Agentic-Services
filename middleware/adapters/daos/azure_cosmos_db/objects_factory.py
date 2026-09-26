from typing import ClassVar

from middleware.adapters.daos.azure_cosmos_db.util.db_conn_mgr import DbConnMgr
from middleware.common.utils.logger_util import log_methods


@log_methods
class ObjectsFactory:
    _instance: ClassVar["ObjectsFactory | None"] = None

    def __init__(self) -> None:
        self.name = "ObjectsFactory"
        self.description = "A factory that can create Cosmos DB dao objects"

    @staticmethod
    def get_instance() -> "ObjectsFactory":
        if ObjectsFactory._instance is None:
            ObjectsFactory._instance = ObjectsFactory()
        return ObjectsFactory._instance

    def init(self) -> None:
        DbConnMgr.get_instance().init()
