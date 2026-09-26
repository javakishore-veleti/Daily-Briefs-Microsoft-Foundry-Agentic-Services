from middleware.common.entity.abstract_base_entity import AbstractBaseEntity
from middleware.common.entity.chat_history import ChatHistory, ChatSession, ChatUser


class AbstractCrudDao[T: AbstractBaseEntity]:
    def __init__(self):
        self.name = "AbstractCrudDao"
        self.description = "A dao that can store and retrieve chat history"

    def get(self, id: str) -> T:
        return None

    def store(self, entity: T) -> None:
        return

    def update(self, entity: T) -> None:
        return

    def delete(self, id: str) -> None:
        return
    
    def get_latest(self, limit: int = 10) -> list[T]:
        return []

class ChatHistoryDao(AbstractCrudDao[ChatHistory]):
    def __init__(self):
        self.name = "ChatHistoryDao"
        self.description = "A dao that can store and retrieve chat history"

class ChatSessionDao(AbstractCrudDao[ChatSession]):
    def __init__(self):
        self.name = "ChatSessionDao"
        self.description = "A dao that can store and retrieve chat session"

class ChatUserDao(AbstractCrudDao[ChatUser]):
    def __init__(self):
        self.name = "ChatUserDao"
        self.description = "A dao that can store and retrieve chat user"