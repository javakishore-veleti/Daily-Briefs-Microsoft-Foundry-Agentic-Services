from datetime import datetime

from pydantic import BaseModel, Field

from middleware.common.utils.logger_util import log_methods


@log_methods
class ChatHistoryMessageResponse(BaseModel):
    id: str = ""
    role: str = ""
    message: str = ""
    sequence: int = 0
    created_at: datetime | None = None
    conversation_id: str = ""


@log_methods
class ChatHistorySessionResponse(BaseModel):
    session_id: str = ""
    conversation_id: str = ""
    title: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    messages: list[ChatHistoryMessageResponse] = Field(default_factory=list)


@log_methods
class ChatHistoryListResponse(BaseModel):
    sessions: list[ChatHistorySessionResponse] = Field(default_factory=list)
    has_more: bool = False
