import os
import threading
from typing import ClassVar

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from middleware.common.utils.logger_util import get_logger

# One process-wide client. pymongo checks a socket out of this pool for each
# operation and returns it when the operation finishes.
# 500 is the number of requests that can hold a connection at the same time.
_DEFAULT_MAX_POOL_SIZE = 500
_DEFAULT_MIN_POOL_SIZE = 50
_DEFAULT_MAX_CONNECTING = 20
_DEFAULT_MAX_IDLE_TIME_MS = 60_000
_DEFAULT_WAIT_QUEUE_TIMEOUT_MS = 2_000
_DEFAULT_CONNECT_TIMEOUT_MS = 5_000
_DEFAULT_SOCKET_TIMEOUT_MS = 10_000
_DEFAULT_SERVER_SELECTION_TIMEOUT_MS = 5_000


class DbConnMgr:
    _instance: ClassVar["DbConnMgr | None"] = None
    _guard: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        self.name = "DbConnMgr"
        self.description = "Process-wide MongoDB connection pool"
        self._client: MongoClient | None = None
        self._client_guard = threading.Lock()

    @classmethod
    def get_instance(cls) -> "DbConnMgr":
        if cls._instance is None:
            with cls._guard:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_collection(self, collection_name: str) -> Collection:
        name = collection_name.strip()
        if not name:
            raise ValueError("collection name is required")
        return self.get_database()[name]

    def get_database(self) -> Database:
        return self.get_client()[self._database_name()]

    def get_client(self) -> MongoClient:
        client = self._client
        if client is not None:
            return client
        with self._client_guard:
            if self._client is None:
                self._client = self._open_client()
            return self._client

    def close(self) -> None:
        with self._client_guard:
            client = self._client
            self._client = None
        if client is not None:
            client.close()

    def _open_client(self) -> MongoClient:
        load_dotenv()
        uri = os.getenv("MONGODB_URI", "").strip()
        if not uri:
            raise RuntimeError("MONGODB_URI is not configured")
        max_pool_size = _int_env("MONGODB_MAX_POOL_SIZE", _DEFAULT_MAX_POOL_SIZE)
        min_pool_size = min(_int_env("MONGODB_MIN_POOL_SIZE", _DEFAULT_MIN_POOL_SIZE), max_pool_size)
        get_logger(__name__).info(
            "mongodb pool ready maxPoolSize=%s minPoolSize=%s",
            max_pool_size,
            min_pool_size,
        )
        return MongoClient(
            uri,
            appname="daily-briefs",
            maxPoolSize=max_pool_size,
            minPoolSize=min_pool_size,
            maxConnecting=_int_env("MONGODB_MAX_CONNECTING", _DEFAULT_MAX_CONNECTING),
            maxIdleTimeMS=_int_env("MONGODB_MAX_IDLE_TIME_MS", _DEFAULT_MAX_IDLE_TIME_MS),
            waitQueueTimeoutMS=_int_env("MONGODB_WAIT_QUEUE_TIMEOUT_MS", _DEFAULT_WAIT_QUEUE_TIMEOUT_MS),
            connectTimeoutMS=_int_env("MONGODB_CONNECT_TIMEOUT_MS", _DEFAULT_CONNECT_TIMEOUT_MS),
            socketTimeoutMS=_int_env("MONGODB_SOCKET_TIMEOUT_MS", _DEFAULT_SOCKET_TIMEOUT_MS),
            serverSelectionTimeoutMS=_int_env(
                "MONGODB_SERVER_SELECTION_TIMEOUT_MS",
                _DEFAULT_SERVER_SELECTION_TIMEOUT_MS,
            ),
            retryWrites=True,
            retryReads=True,
        )

    def _database_name(self) -> str:
        load_dotenv()
        name = os.getenv("MONGODB_DATABASE", "").strip()
        if not name:
            raise RuntimeError("MONGODB_DATABASE is not configured")
        return name


def _int_env(key: str, default: int) -> int:
    raw = os.getenv(key, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if value < 0:
        return default
    return value
