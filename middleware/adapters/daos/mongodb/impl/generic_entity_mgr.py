import os
import threading
from datetime import datetime
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

from middleware.adapters.daos.mongodb.util.db_conn_mgr import DbConnMgr
from middleware.common.daos.interfaces import AbstractCrudDao
from middleware.common.entity.abstract_base_entity import AbstractBaseEntity
from middleware.common.entity.chat_history import (
    ANONYMOUS_USER_ID,
    ChatHistory,
    ChatSession,
    ChatUser,
)
from middleware.common.entity.joiner import JoinerInfo, JoinerPreferences


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

    def touch(self, entity_id: str) -> None:
        if not entity_id.strip():
            return
        self._collection().update_one(
            {"_id": entity_id},
            {"$set": {"updated_at": datetime.now()}},
        )

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
        text = _user_prompt(item)
        if text:
            compact = " ".join(text.split())
            if len(compact) <= 42:
                return compact
            return f"{compact[:42].rstrip()}…"
    return "New chat"


def _user_prompt(item: ChatHistory) -> str:
    if str(getattr(item, "user_prompt_id", "") or "").strip():
        return ""
    prompt = str(getattr(item, "user_prompt", "") or "").strip()
    if prompt:
        return prompt
    if str(getattr(item, "role", "") or "") == "user":
        return str(getattr(item, "message", "") or "").strip()
    return ""


def _ordered_turns(messages: list[ChatHistory]) -> list[ChatHistory]:
    prompts: list[ChatHistory] = []
    replies: dict[str, list[ChatHistory]] = {}
    for item in messages:
        prompt_id = str(getattr(item, "user_prompt_id", "") or "").strip()
        if prompt_id:
            replies.setdefault(prompt_id, []).append(item)
            continue
        if _user_prompt(item):
            prompts.append(item)
    prompts.sort(key=lambda item: (int(getattr(item, "sequence", 0) or 0), item.created_at))
    ordered: list[ChatHistory] = []
    for prompt in prompts:
        ordered.append(prompt)
        group = replies.get(prompt.id, [])
        group.sort(key=lambda item: (int(getattr(item, "sequence", 0) or 0), item.created_at))
        ordered.extend(group)
    return ordered


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

    def init(self) -> None:
        super().init()
        self.pair_turns()

    def latest_sessions(
        self,
        app_module: str,
        limit: int = 10,
        skip: int = 0,
        owned_session_ids: list[str] | None = None,
        joiner_info_id: str = "",
    ) -> tuple[list[dict[str, Any]], bool]:
        self._require_init()
        if limit < 1 or limit > self.latest_limit:
            raise ValueError(f"limit must be from 1 to {self.latest_limit}")
        if skip < 0:
            raise ValueError("skip must be 0 or greater")
        if owned_session_ids is not None and not owned_session_ids:
            return [], False
        collection = self._collection()
        self._ensure_index(
            collection,
            "app_module_created_at_desc",
            [("app_module", ASCENDING), ("created_at", DESCENDING)],
        )
        match: dict[str, Any] = {"app_module": app_module}
        if owned_session_ids is not None:
            match["chat_session_id"] = {"$in": owned_session_ids}
        if joiner_info_id.strip():
            match["joiner_info_id"] = joiner_info_id.strip()
        grouped = list(
            collection.aggregate(
                [
                    {"$match": match},
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
        message_match: dict[str, Any] = {"app_module": app_module, "chat_session_id": {"$in": session_ids}}
        if joiner_info_id.strip():
            message_match["joiner_info_id"] = joiner_info_id.strip()
        stored = [
            self._entity(document)
            for document in collection.find(message_match).sort("created_at", ASCENDING)
        ]
        by_session: dict[str, list[ChatHistory]] = {}
        for item in stored:
            by_session.setdefault(item.chat_session_id, []).append(item)
        sessions: list[dict[str, Any]] = []
        for item in page:
            session_id = str(item.get("_id") or "")
            messages = _ordered_turns(by_session.get(session_id, []))
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

    def user_messages(self, app_module: str, session_id: str) -> list[str]:
        self._require_init()
        documents = self._collection().find(
            {
                "app_module": app_module,
                "chat_session_id": session_id,
                "user_prompt": {"$nin": [None, ""]},
                "user_prompt_id": {"$in": [None, ""]},
            },
            {"user_prompt": 1},
        ).sort("updated_at", DESCENDING)
        return [str(document.get("user_prompt") or "").strip() for document in documents if document.get("user_prompt")]

    def find_prompt(
        self,
        app_module: str,
        session_id: str,
        text: str,
        joiner_info_id: str = "",
    ) -> ChatHistory | None:
        self._require_init()
        prompt = text.strip()
        if not prompt:
            return None
        query: dict[str, Any] = {
            "app_module": app_module,
            "chat_session_id": session_id,
            "user_prompt": prompt,
            "user_prompt_id": {"$in": [None, ""]},
        }
        if joiner_info_id.strip():
            query["joiner_info_id"] = joiner_info_id.strip()
        document = self._collection().find_one(query)
        if document is None:
            return None
        return self._entity(document)

    def next_prompt_sequence(self, app_module: str, session_id: str) -> int:
        self._require_init()
        document = self._collection().find_one(
            {
                "app_module": app_module,
                "chat_session_id": session_id,
                "user_prompt": {"$nin": [None, ""]},
                "user_prompt_id": {"$in": [None, ""]},
            },
            sort=[("sequence", DESCENDING)],
        )
        if document is None:
            return 1
        return int(document.get("sequence") or 0) + 1

    def next_response_sequence(self, user_prompt_id: str) -> int:
        self._require_init()
        document = self._collection().find_one(
            {"user_prompt_id": user_prompt_id},
            sort=[("sequence", DESCENDING)],
        )
        if document is None:
            return 1
        return int(document.get("sequence") or 0) + 1

    def pair_turns(self) -> None:
        self._require_init()
        self._link_role_rows()
        self._split_combined_rows()

    def _link_role_rows(self) -> None:
        collection = self._collection()
        pending = list(
            collection.find(
                {
                    "role": {"$in": ["user", "assistant"]},
                    "user_prompt_id": {"$in": [None, ""]},
                }
            ).sort([("chat_session_id", ASCENDING), ("created_at", ASCENDING)])
        )
        grouped: dict[str, list[dict[str, Any]]] = {}
        for document in pending:
            grouped.setdefault(str(document.get("chat_session_id") or ""), []).append(document)
        for documents in grouped.values():
            canonical: dict[str, str] = {}
            counts: dict[str, int] = {}
            prompt_sequence = 0
            current_id = ""
            for document in documents:
                if document.get("role") == "user":
                    text = str(document.get("message") or "").strip()
                    existing_id = canonical.get(text, "")
                    if text and existing_id:
                        current_id = existing_id
                        collection.delete_one({"_id": document.get("_id")})
                        continue
                    prompt_sequence += 1
                    collection.update_one(
                        {"_id": document.get("_id")},
                        {
                            "$set": {
                                "user_prompt": text,
                                "sequence": prompt_sequence,
                                "updated_at": datetime.now(),
                            },
                            "$unset": {"message": "", "role": "", "agent_response": "", "user_prompt_id": ""},
                        },
                    )
                    current_id = str(document.get("_id") or "")
                    if text:
                        canonical[text] = current_id
                    continue
                if document.get("role") != "assistant" or not current_id:
                    continue
                counts[current_id] = counts.get(current_id, 0) + 1
                collection.update_one(
                    {"_id": document.get("_id")},
                    {
                        "$set": {
                            "agent_response": str(document.get("message") or ""),
                            "user_prompt_id": current_id,
                            "sequence": counts[current_id],
                            "updated_at": datetime.now(),
                        },
                        "$unset": {"message": "", "role": "", "user_prompt": ""},
                    },
                )

    def _split_combined_rows(self) -> None:
        collection = self._collection()
        combined = list(
            collection.find(
                {
                    "user_prompt": {"$nin": [None, ""]},
                    "agent_response": {"$nin": [None, ""]},
                    "user_prompt_id": {"$in": [None, ""]},
                }
            )
        )
        for document in combined:
            prompt_id = str(document.get("_id") or "")
            response = ChatHistory()
            response.app_module = str(document.get("app_module") or "")
            response.chat_session_id = str(document.get("chat_session_id") or "")
            response.conversation_id = str(document.get("conversation_id") or "")
            response.model_name = str(document.get("model_name") or "")
            response.user_prompt_id = prompt_id
            response.agent_response = str(document.get("agent_response") or "")
            response.sequence = self.next_response_sequence(prompt_id)
            del response.user_prompt
            del response.message
            del response.role
            self.store(response)
            collection.update_one({"_id": document.get("_id")}, {"$unset": {"agent_response": ""}})

    def session_ids(self) -> list[str]:
        values = self._collection().distinct("chat_session_id")
        return [str(value) for value in values if str(value or "").strip()]


class ChatSessionMgr(GenericEntityMgr[ChatSession]):
    def __init__(self) -> None:
        super().__init__(ChatSession)
        self.name = "ChatSessionMgr"
        self.description = "A mgr that can store and retrieve chat session"

    def ensure(self, session_id: str, user_id: str) -> ChatSession:
        existing = self.get(session_id)
        if existing is not None:
            existing.session_id = session_id
            if user_id and user_id != ANONYMOUS_USER_ID:
                existing.user_id = user_id
            elif not existing.user_id:
                existing.user_id = user_id
            self.update(existing)
            return existing
        session = ChatSession()
        session.id = session_id
        session.session_id = session_id
        session.user_id = user_id
        try:
            self.store(session)
        except DuplicateKeyError:
            stored = self.get(session_id)
            if stored is not None:
                return stored
            raise
        return session

    def ids_for_user(self, user_id: str) -> list[str]:
        if not user_id.strip():
            return []
        found = self._collection().find({"user_id": user_id}, {"session_id": 1, "_id": 1})
        session_ids: list[str] = []
        for document in found:
            session_id = str(document.get("session_id") or document.get("_id") or "")
            if session_id:
                session_ids.append(session_id)
        return session_ids


class ChatUserMgr(GenericEntityMgr[ChatUser]):
    def __init__(self) -> None:
        super().__init__(ChatUser)
        self.name = "ChatUserMgr"
        self.description = "A mgr that can store and retrieve chat user"

    def ensure_anonymous(self) -> ChatUser:
        existing = self.get(ANONYMOUS_USER_ID)
        if existing is not None:
            return existing
        user = ChatUser()
        user.id = ANONYMOUS_USER_ID
        user.name = "Anonymous"
        try:
            self.store(user)
        except DuplicateKeyError:
            stored = self.get(ANONYMOUS_USER_ID)
            if stored is not None:
                return stored
            raise
        return user

    def find_by_email(self, email: str) -> ChatUser | None:
        self._ensure_email_index()
        document = self._collection().find_one({"email": email})
        if document is None:
            return None
        return self._entity(document)

    def _ensure_email_index(self) -> None:
        collection = self._collection()
        marker = f"{collection.full_name}:email_unique"
        if marker in self.indexed_collections:
            return
        with self.index_guard:
            if marker in self.indexed_collections:
                return
            collection.create_index([("email", ASCENDING)], name="email_unique", unique=True)
            self.indexed_collections.add(marker)


class JoinerInfoMgr(GenericEntityMgr[JoinerInfo]):
    def __init__(self) -> None:
        super().__init__(JoinerInfo)
        self.collection_name = "joiner-info"
        self.name = "JoinerInfoMgr"
        self.description = "A mgr that can store and retrieve joiner info"

    def page_for_date(self, joining_date: str, limit: int = 10, skip: int = 0) -> tuple[list[JoinerInfo], bool]:
        self._require_init()
        if limit < 1 or limit > self.latest_limit:
            raise ValueError(f"limit must be from 1 to {self.latest_limit}")
        if skip < 0:
            raise ValueError("skip must be 0 or greater")
        collection = self._collection()
        self._ensure_index(
            collection,
            "joining_date_last_name",
            [("joining_date", ASCENDING), ("last_name", ASCENDING), ("first_name", ASCENDING)],
        )
        cursor = (
            collection.find({"joining_date": joining_date})
            .sort([("last_name", ASCENDING), ("first_name", ASCENDING)])
            .skip(skip)
            .limit(limit + 1)
        )
        rows = [self._entity(document) for document in cursor]
        has_more = len(rows) > limit
        return rows[:limit], has_more

    def ensure_samples(self, today: str) -> None:
        if self._collection().count_documents({}) > 0:
            return
        from datetime import date, timedelta

        day = date.fromisoformat(today)
        samples = [
            ("Asha", "R", "Reddy", "asha.reddy@example.com", "555-0101", "12 River Road, Vijayawada", ["e-101"], ["Mina Rao"], "Software Engineer", "IC3", "Software Engineer", 92000, today),
            ("Luis", "", "Martinez", "luis.martinez@example.com", "555-0102", "40 Oak Street, Charlotte", ["e-102", "e-108"], ["Jon Hale", "Priya Shah"], "Program Manager", "M1", "Program Manager", 110000, today),
            ("Mei", "Lin", "Chen", "mei.chen@example.com", "555-0103", "8 Harbor Lane, Seattle", ["e-104"], ["Noah Kim"], "Data Analyst", "IC2", "Data Analyst", 86000, (day + timedelta(days=1)).isoformat()),
        ]
        preferences = JoinerPreferencesMgr()
        preferences.init()
        for first, middle, last, email, phone, address, ids, names, official, internal, joining, salary, joining_date in samples:
            joiner = JoinerInfo()
            joiner.first_name = first
            joiner.middle_name = middle
            joiner.last_name = last
            joiner.email = email
            joiner.contact_phone = phone
            joiner.contact_address = address
            joiner.interviewed_by_employee_ids = ids
            joiner.interviewed_by_employee_names = names
            joiner.official_role_name = official
            joiner.internal_role_name = internal
            joiner.joining_official_role_name = joining
            joiner.salary_accepted_usd = salary
            joiner.joining_date = joining_date
            self.store(joiner)
            preference = JoinerPreferences()
            preference.joiner_info_id = joiner.id
            preference.resumes = f"{first} {last} resume: previous role before joining as {joining}."
            preference.personal_interests = "Reading, hiking, and team sports."
            preference.food_preferences = "No peanuts."
            preferences.store(preference)


class JoinerPreferencesMgr(GenericEntityMgr[JoinerPreferences]):
    def __init__(self) -> None:
        super().__init__(JoinerPreferences)
        self.collection_name = "joiner-preferences"
        self.name = "JoinerPreferencesMgr"
        self.description = "A mgr that can store and retrieve joiner preferences"

    def for_joiner(self, joiner_info_id: str) -> JoinerPreferences | None:
        self._require_init()
        document = self._collection().find_one({"joiner_info_id": joiner_info_id})
        if document is None:
            return None
        return self._entity(document)
