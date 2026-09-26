from typing import ClassVar

from middleware.common.utils.logger_util import get_logger, log_methods


@log_methods
class SessionCache:
    _instance: ClassVar["SessionCache | None"] = None

    def __init__(self):
        self.cache = {}

    def get(self, session_id: str) -> dict:
        get_logger(__name__).info("session_id=%s", session_id)
        return self.cache.get(session_id, {})

    def set(self, session_id: str, value: dict):
        conversation_id = value.get("conversation_id", "")
        get_logger(__name__).info(
            "session_id=%s conversation_id=%s",
            session_id,
            conversation_id,
        )
        self.cache[session_id] = value

    def delete(self, session_id: str):
        get_logger(__name__).info("session_id=%s", session_id)
        self.cache.pop(session_id, None)

    @staticmethod
    def get_instance() -> "SessionCache":
        if SessionCache._instance is None:
            SessionCache._instance = SessionCache()
        return SessionCache._instance