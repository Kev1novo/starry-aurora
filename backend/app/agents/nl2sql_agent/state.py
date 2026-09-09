"""NL2SQL Agent 状态定义"""
from typing import Any, Optional

from langgraph.graph import StateGraph
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """NL2SQL Agent 状态"""

    # 输入
    question: str
    user_id: int
    datasource_id: Optional[int]
    conversation_id: Optional[str]

    # 意图解析
    intent: Optional[str]
    entities: dict[str, Any]
    time_range: Optional[dict]

    # Schema 检索
    retrieved_schemas: list[dict]
    pruned_schemas: list[dict]

    # SQL
    generated_sql: Optional[str]
    validated: bool
    validation_errors: list[str]
    fix_attempts: int

    # 执行
    execution_result: Optional[list[dict]]
    execution_error: Optional[str]

    # 输出
    formatted_result: Optional[str]
    chart_suggestion: Optional[str]
    error: Optional[str]