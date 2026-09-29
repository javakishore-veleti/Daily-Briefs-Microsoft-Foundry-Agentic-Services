from datetime import datetime

from middleware.common.entity.abstract_base_entity import AbstractBaseEntity

ANONYMOUS_USER_ID = "anonymous"
DEFAULT_USER_LOGIN = "enterprise-user"
DEFAULT_USER_PASSWORD = "password"


class ChatUser(AbstractBaseEntity):
    def __init__(self):
        super().__init__()
        self.name:str = ""
        self.email:str = ""
        self.phone:str = ""
        self.password_hash:str = ""
        self.reset_code_hash:str = ""
        self.reset_code_expires_at:datetime | None = None

class ChatSession(AbstractBaseEntity):
    def __init__(self):
        super().__init__()
        self.session_id:str = ""
        self.user_id:str = ""

class ChatHistory(AbstractBaseEntity):
    def __init__(self):
        super().__init__()
        self.app_module:str = ""
        # Foreign key to ChatSession
        self.chat_session_id:str = ""
        self.conversation_id:str = ""
        self.user_prompt:str = ""
        self.agent_response:str = ""
        self.user_prompt_id:str = ""
        self.sequence:int = 0
        self.message:str = ""
        self.role:str = ""
        self.model_name:str = ""
        self.model_version:str = ""
        self.model_provider:str = ""
        # Foreign key to the joiner-info document. Set on HR daily brief chats.
        self.joiner_info_id:str = ""
