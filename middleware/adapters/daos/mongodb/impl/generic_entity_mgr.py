import os
import threading
from datetime import datetime
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING
from pymongo.collection import Collection

from middleware.adapters.daos.mongodb.util.db_conn_mgr import DbConnMgr
from middleware.common.daos.interfaces import AbstractCrudDao
from middleware.common.entity.abstract_base_entity import AbstractBaseEntity
from middleware.common.entity.chat_history import ChatHistory, ChatSession, ChatUser


class GenericEntityMgr[T: AbstractBaseEntity](AbstractCrudDao[T]):
    def __init__(self, entity_type: type[T]):
        super().__init__()
        self.entity_type = entity_type
        self.collection_name = collection_name_for(entity_type)
        self.name = "GenericEntityMgr"
        self.description = "A mgr that can store and retrieve generic entity"
        self.initialized = False
        self.latest_limit = 0
        self.indexed_collections: set[str] = set()
        self.index_guard = threading.Lock()

    def init(self) -> None:
        if self.initialized:
            return
        self.latest_limit = 100
        self.indexed_collections = set()
        self.index_guard = threading.Lock()
        self.initialized = True

    def get(self, id: str) -> T | None:
        document = self._collection().find_one({"_id": id})
        if document is None:
            return None
        return self._entity(document)

    def store(self, entity: T) -> None:
        if not str(getattr(entity, "id", "") or ""):
            setattr(entity, "id", str(uuid4()))
        self._collection().insert_one(_document(entity))

    def update(self, entity: T) -> None:
        entity_id = str(getattr(entity, "id", "") or "")
        if not entity_id:
            raise ValueError("entity id is required")
        if hasattr(entity, "updated_at"):
            setattr(entity, "updated_at", datetime.now())
        result = self._collection().replace_one({"_id": entity_id}, _document(entity))
        if result.matched_count == 0:
            raise ValueError(f"entity id {entity_id} was not found")

    def delete(self, id: str) -> None:
        self._collection().delete_one({"_id": id})

    def get_latest(self, limit: int = 10) -> list[T]:
        self._require_init()
        if limit < 1 or limit > self.latest_limit:
            raise ValueError(f"limit must be from 1 to {self.latest_limit}")
        collection = self._collection()
        self._ensure_created_at_index(collection)
        cursor = collection.find().sort("created_at", DESCENDING).limit(limit)
        return [self._entity(document) for document in cursor]

    def _require_init(self) -> None:
        if not self.initialized:
            raise RuntimeError("GenericEntityMgr.init was not called")

    def _collection(self) -> Collection:
        return DbConnMgr.get_instance().get_collection(self.collection_name)

    def _entity(self, document: dict[str, Any]) -> T:
        entity = self.entity_type()
        for key, value in document.items():
            if key == "_id":
                continue
            setattr(entity, key, value)
        if not str(getattr(entity, "id", "") or ""):
            setattr(entity, "id", str(document.get("_id", "")))
        return entity

    def _ensure_created_at_index(self, collection: Collection) -> None:
        self._ensure_index(collection, "created_at_desc", [("created_at", DESCENDING)])

    def _ensure_index(self, collection: Collection, index_name: str, keys: list[tuple[str, int]]) -> None:
        marker = f"{collection.full_name}:{index_name}"
        if marker in self.indexed_collections:
            return
        with self.index_guard:
            if marker in self.indexed_collections:
                return
            collection.create_index(keys, name=index_name)
            self.indexed_collections.add(marker)


def collection_name_for(entity_type: type) -> str:
    load_dotenv()
    configured = os.getenv(f"MONGODB_COLLECTION_{entity_type.__name__.upper()}", "")
    if isinstance(configured, str) and configured.strip():
        return configured.strip()
    return entity_type.__name__.lower()


def _session_title(messages: list[ChatHistory]) -> str:
    for item in messages:
        if item.role == "user" and item.message.strip():
            compact = " ".join(item.message.split())
            if len(compact) <= 42:
                return compact
            return f"{compact[:42].rstrip()}…"
    return "New chat"


def _document(entity: object) -> dict[str, Any]:
    document = {
        key: value
        for key, value in vars(entity).items()
        if not key.startswith("_")
    }
    entity_id = str(document.get("id") or "")
    document["id"] = entity_id
    document["_id"] = entity_id
    return document


class ChatHistoryMgr(GenericEntityMgr[ChatHistory]):
    def __init__(self) -> None:
        super().__init__(ChatHistory)
        self.name = "ChatHistoryMgr"
        self.description = "A mgr that can store and retrieve chat history"

    def latest_sessions(self, app_module: str, limit: int = 10, skip: int = 0) -> tuple[list[dict[str, Any]], bool]:
        self._require_init()
        if limit < 1 or limit > self.latest_limit:
            raise ValueError(f"limit must be from 1 to {self.latest_limit}")
        if skip < 0:
            raise ValueError("skip must be 0 or greater")
        collection = self._collection()
        self._ensure_index(
            collection,
            "app_module_created_at_desc",
            [("app_module", ASCENDING), ("created_at", DESCENDING)],
        )
        grouped = list(
            collection.aggregate(
                [
                    {"$match": {"app_module": app_module}},
                    {
                        "$group": {
                            "_id": "$chat_session_id",
                            "created_at": {"$min": "$created_at"},
                            "updated_at": {"$max": "$created_at"},
                            "conversation_id": {"$last": "$conversation_id"},
                        }
                    },
                    {"$sort": {"updated_at": DESCENDING}},
                    {"$skip": skip},
                    {"$limit": limit + 1},
                ]
            )
        )
        has_more = len(grouped) > limit
        page = grouped[:limit]
        session_ids = [str(item.get("_id") or "") for item in page if item.get("_id")]
        if not session_ids:
            return [], False
        stored = [
            self._entity(document)
            for document in collection.find(
                {"app_module": app_module, "chat_session_id": {"$in": session_ids}}
            ).sort("created_at", ASCENDING)
        ]
        by_session: dict[str, list[ChatHistory]] = {}
        for item in stored:
            by_session.setdefault(item.chat_session_id, []).append(item)
        sessions: list[dict[str, Any]] = []
        for item in page:
            session_id = str(item.get("_id") or "")
            messages = by_session.get(session_id, [])
            conversation_id = next((message.conversation_id for message in reversed(messages) if message.conversation_id), "")
            sessions.append(
                {
                    "session_id": session_id,
                    "conversation_id": conversation_id,
                    "title": _session_title(messages),
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at"),
                    "messages": messages,
                }
            )
        return sessions, has_more


class ChatSessionMgr(GenericEntityMgr[ChatSession]):
    def __init__(self) -> None:
        super().__init__(ChatSession)
        self.name = "ChatSessionMgr"
        self.description = "A mgr that can store and retrieve chat session"


class ChatUserMgr(GenericEntityMgr[ChatUser]):
    def __init__(self) -> None:
        super().__init__(ChatUser)
        self.name = "ChatUserMgr"
        self.description = "A mgr that can store and retrieve chat user"
