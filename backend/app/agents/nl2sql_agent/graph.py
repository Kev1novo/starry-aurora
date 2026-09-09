"""
NL2SQL LangGraph 流程定义
定义 StateGraph：intent_parser → schema_retriever → sql_generator
→ sql_validator → (if fail → sql_generator, max 3) → sql_executor → result_formatter
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.nl2sql_agent.nodes.intent_parser import intent_parser_node
from app.agents.nl2sql_agent.nodes.result_formatter import result_formatter_node
from app.agents.nl2sql_agent.nodes.schema_retriever import schema_retriever_node
from app.agents.nl2sql_agent.nodes.sql_executor import sql_executor_node
from app.agents.nl2sql_agent.nodes.sql_generator import sql_generator_node
from app.agents.nl2sql_agent.nodes.sql_validator import (
    should_retry,
    sql_validator_node,
)
from app.agents.nl2sql_agent.state import AgentState


def build_graph() -> StateGraph:
    """构建并编译 NL2SQL LangGraph

    Graph 拓扑：
        intent_parser → schema_retriever → sql_generator → sql_validator
        ┌───────────────────────────────────────────┘  │
        │  (if not validated and fix_attempts < 3)      │
        └───────────────────────────────────────────────┘
                                                         │
                                            (if validated or fix_attempts >= 3)
                                                         ↓
                                                  sql_executor → result_formatter → END

    Returns:
        编译后的 StateGraph，可传入状态执行
    """
    workflow = StateGraph(AgentState)

    # ---- 注册所有节点 ----
    workflow.add_node("intent_parser", intent_parser_node)
    workflow.add_node("schema_retriever", schema_retriever_node)
    workflow.add_node("sql_generator", sql_generator_node)
    workflow.add_node("sql_validator", sql_validator_node)
    workflow.add_node("sql_executor", sql_executor_node)
    workflow.add_node("result_formatter", result_formatter_node)

    # ---- 设置入口 ----
    workflow.set_entry_point("intent_parser")

    # ---- 主流程边 ----
    workflow.add_edge("intent_parser", "schema_retriever")
    workflow.add_edge("schema_retriever", "sql_generator")
    workflow.add_edge("sql_generator", "sql_validator")

    # ---- 条件路由：验证后重试或执行 ----
    workflow.add_conditional_edges(
        "sql_validator",
        should_retry,
        {
            "fix": "sql_generator",
            "execute": "sql_executor",
        },
    )

    # ---- 执行后格式化并结束 ----
    workflow.add_edge("sql_executor", "result_formatter")
    workflow.add_edge("result_formatter", END)

    # ---- 编译 ----
    compiled = workflow.compile()
    return compiled