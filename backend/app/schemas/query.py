"""NL2SQL 查询相关 Schema"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class QueryAskRequest(BaseModel):
    question: str
    datasource_id: Optional[int] = None
    conversation_id: Optional[int] = None
    stream: bool = False


class QueryResponse(BaseModel):
    id: int
    question: str
    sql: Optional[str] = None
    result: Optional[list[dict]] = None
    explanation: Optional[str] = None
    chart_suggestion: Optional[str] = None
    created_at: datetime


class StreamEvent(BaseModel):
    type: str  # intent / schema / sql / result / error / done
    data: dict[str, Any]


class QueryHistoryResponse(BaseModel):
    id: int
    title: str
    question: str
    created_at: datetime
    message_count: int = 0