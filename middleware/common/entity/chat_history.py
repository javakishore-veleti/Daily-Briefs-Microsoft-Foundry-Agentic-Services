from middleware.common.entity.abstract_base_entity import AbstractBaseEntity

ANONYMOUS_USER_ID = "anonymous"


class ChatUser(AbstractBaseEntity):
    def __init__(self):
        super().__init__()
        self.name:str = ""
        self.email:str = ""
        self.phone:str = ""

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
        self.message:str = ""     
        self.role:str = ""
        self.model_name:str = ""
        self.model_version:str = ""
        self.model_provider:str = ""
