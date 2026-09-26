from typing import ClassVar

from middleware.adapters.daos.mongodb.impl.generic_entity_mgr import (
    ChatHistoryMgr,
    ChatSessionMgr,
    ChatUserMgr,
    GenericEntityMgr,
)
from middleware.common.entity.abstract_base_entity import AbstractBaseEntity
from middleware.common.utils.logger_util import log_methods


@log_methods
class ObjectsFactory:
    _instance: ClassVar["ObjectsFactory | None"] = None

    def __init__(self) -> None:
        self.name = "ObjectsFactory"
        self.description = "A factory that can create dao objects"
        self.objects: dict[str, GenericEntityMgr[AbstractBaseEntity]] = {}

    @staticmethod
    def get_instance() -> "ObjectsFactory":
        if ObjectsFactory._instance is None:
            ObjectsFactory._instance = ObjectsFactory()
        return ObjectsFactory._instance

    def init_dao_objects(self) -> None:
        self.get_chat_history_mgr()
        self.get_chat_session_mgr()
        self.get_chat_user_mgr()

    def get_chat_history_mgr(self) -> ChatHistoryMgr:
        return self._ensure_mgr("chat_history_mgr", ChatHistoryMgr)

    def get_chat_session_mgr(self) -> ChatSessionMgr:
        return self._ensure_mgr("chat_session_mgr", ChatSessionMgr)

    def get_chat_user_mgr(self) -> ChatUserMgr:
        return self._ensure_mgr("chat_user_mgr", ChatUserMgr)

    def _ensure_mgr[T: AbstractBaseEntity](
        self,
        key: str,
        mgr_type: type[GenericEntityMgr[T]],
    ) -> GenericEntityMgr[T]:
        existing = self.objects.get(key)
        if isinstance(existing, mgr_type):
            return existing
        mgr = mgr_type()
        mgr.init()
        self.objects[key] = mgr
        return mgr
