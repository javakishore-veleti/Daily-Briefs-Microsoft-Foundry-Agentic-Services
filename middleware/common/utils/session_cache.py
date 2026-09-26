from typing import ClassVar
from uuid import uuid4


class SessionCache:
    _instance: ClassVar["SessionCache | None"] = None

    def __init__(self):
        self.cache = {}

    def get(self, session_id: str) -> dict:
        return self.cache.get(session_id, {})

    def set(self, session_id: str, value: dict):
        self.cache[session_id] = value

    def delete(self, session_id: str):
        self.cache.pop(session_id, None)

    @staticmethod
    def get_instance() -> "SessionCache":
        if SessionCache._instance is None:
            SessionCache._instance = SessionCache()
        return SessionCache._instance