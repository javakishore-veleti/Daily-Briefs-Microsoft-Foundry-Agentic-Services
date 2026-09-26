import os
from typing import ClassVar

from dotenv import load_dotenv


class DbConnMgr:
    _instance: ClassVar["DbConnMgr | None"] = None

    def __init__(self) -> None:
        self.name = "DbConnMgr"
        self.description = "Azure Cosmos DB connection"
        self.endpoint = ""
        self.database_name = ""
        self.initialized = False

    @staticmethod
    def get_instance() -> "DbConnMgr":
        if DbConnMgr._instance is None:
            DbConnMgr._instance = DbConnMgr()
        return DbConnMgr._instance

    def init(self) -> None:
        if self.initialized:
            return
        load_dotenv()
        endpoint = os.getenv("COSMOSDB_ENDPOINT", "").strip()
        database_name = os.getenv("COSMOSDB_DATABASE", "").strip()
        if not endpoint or not database_name:
            raise RuntimeError(
                "COSMOSDB_ENDPOINT and COSMOSDB_DATABASE are required when DB_TECHNOLOGY=cosmosdb"
            )
        self.endpoint = endpoint
        self.database_name = database_name
        self.initialized = True
