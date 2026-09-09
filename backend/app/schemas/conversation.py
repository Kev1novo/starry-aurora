"""会话工作区 Pydantic Schema"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class MessageCreate(BaseModel):
    role: str = "user"
    content: str
    message_type: str = "text"


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    message_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationCreate(BaseModel):
    title: str = "新对话"
    workspace_type: str = "query"


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None


class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    workspace_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    """含消息列表的会话详情"""
    id: int
    user_id: int
    title: str
    workspace_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse]

    model_config = {"from_attributes": True}