from typing import ClassVar

from datetime import date

from middleware.adapters.daos.mongodb.impl.generic_entity_mgr import (
    ChatHistoryMgr,
    ChatSessionMgr,
    ChatUserMgr,
    GenericEntityMgr,
    JoinerInfoMgr,
    JoinerPreferencesMgr,
)
from middleware.common.dtos.app_config import AppConfig
from middleware.common.entity.abstract_base_entity import AbstractBaseEntity
from middleware.common.utils.logger_util import log_methods


@log_methods
class ObjectsFactory:
    _instance: ClassVar["ObjectsFactory | None"] = None

    def __init__(self) -> None:
        self.name = "ObjectsFactory"
        self.description = "A factory that can create dao objects"
        self.db_technology = "mongodb"
        self.objects: dict[str, GenericEntityMgr[AbstractBaseEntity]] = {}

    @staticmethod
    def get_instance() -> "ObjectsFactory":
        if ObjectsFactory._instance is None:
            ObjectsFactory._instance = ObjectsFactory()
        return ObjectsFactory._instance

    def init(self) -> None:
        self.db_technology = AppConfig.get_instance().get_db_technology()
        if self.db_technology == "cosmosdb":
            from middleware.adapters.daos.azure_cosmos_db.objects_factory import (
                ObjectsFactory as CosmosObjectsFactory,
            )

            CosmosObjectsFactory.get_instance().init()
            return
        self.get_chat_history_mgr()
        self.get_chat_session_mgr()
        self.get_chat_user_mgr()
        self.get_joiner_info_mgr()
        self.get_joiner_preferences_mgr()
        self._ensure_sessions_for_history()
        self.get_joiner_info_mgr().ensure_samples(date.today().isoformat())

    def get_chat_history_mgr(self) -> ChatHistoryMgr:
        return self._ensure_mgr("chat_history_mgr", ChatHistoryMgr)

    def get_chat_session_mgr(self) -> ChatSessionMgr:
        return self._ensure_mgr("chat_session_mgr", ChatSessionMgr)

    def get_chat_user_mgr(self) -> ChatUserMgr:
        return self._ensure_mgr("chat_user_mgr", ChatUserMgr)

    def get_joiner_info_mgr(self) -> JoinerInfoMgr:
        return self._ensure_mgr("joiner_info_mgr", JoinerInfoMgr)

    def get_joiner_preferences_mgr(self) -> JoinerPreferencesMgr:
        return self._ensure_mgr("joiner_preferences_mgr", JoinerPreferencesMgr)

    def _ensure_sessions_for_history(self) -> None:
        user = self.get_chat_user_mgr().ensure_anonymous()
        sessions = self.get_chat_session_mgr()
        for session_id in self.get_chat_history_mgr().session_ids():
            sessions.ensure(session_id, user.id)

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
