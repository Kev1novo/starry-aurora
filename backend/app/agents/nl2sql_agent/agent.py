"""NL2SQL Agent——能力支撑层·手脚/数据专家"""
from typing import Any, AsyncGenerator, Optional

from app.agents.base import BaseAgent
from app.agents.shared.llm_factory import LLMFactory


class DataAgent(BaseAgent):
    """NL2SQL Agent：数据查询执行者"""

    name = "DataAgent"
    description = "NL2SQL 数据查询引擎，负责意图解析、Schema 检索、SQL 生成/校验/执行/格式化"

    def __init__(self, db=None):
        self.db = db
        self.llm = LLMFactory()
        self._graph = None

    async def validate_input(self, input_data: dict) -> bool:
        return bool(input_data.get("question"))

    async def run(self, input_data: dict, **kwargs) -> dict[str, Any]:
        """完整同步执行 NL2SQL 流程"""
        from app.agents.nl2sql_agent.graph import build_graph

        graph = build_graph()
        state = {
            "question": input_data["question"],
            "user_id": input_data.get("user_id", 0),
            "datasource_id": input_data.get("datasource_id"),
            "conversation_id": input_data.get("conversation_id"),
            "intent": None,
            "entities": {},
            "time_range": None,
            "retrieved_schemas": [],
            "pruned_schemas": [],
            "generated_sql": None,
            "validated": False,
            "validation_errors": [],
            "fix_attempts": 0,
            "execution_result": None,
            "execution_error": None,
            "formatted_result": None,
            "chart_suggestion": None,
            "error": None,
        }

        final_state = await graph.ainvoke(state)

        return {
            "sql": final_state.get("generated_sql"),
            "result": final_state.get("execution_result"),
            "explanation": final_state.get("formatted_result"),
            "chart_suggestion": final_state.get("chart_suggestion"),
            "error": final_state.get("error"),
        }

    async def stream_run(self, input_data: dict) -> AsyncGenerator[dict, None]:
        """流式执行 NL2SQL，逐步输出事件"""
        from copy import deepcopy

        from app.agents.nl2sql_agent.graph import build_graph

        graph = build_graph()
        state = {
            "question": input_data["question"],
            "user_id": input_data.get("user_id", 0),
            "datasource_id": input_data.get("datasource_id"),
            "conversation_id": input_data.get("conversation_id"),
            "intent": None,
            "entities": {},
            "time_range": None,
            "retrieved_schemas": [],
            "pruned_schemas": [],
            "generated_sql": None,
            "validated": False,
            "validation_errors": [],
            "fix_attempts": 0,
            "execution_result": None,
            "execution_error": None,
            "formatted_result": None,
            "chart_suggestion": None,
            "error": None,
        }

        yield {"type": "start", "data": {"message": "开始处理查询..."}}

        # 单次遍历 graph：astream 同时产出中间事件和最终结果
        final = deepcopy(state)
        async for step in graph.astream(state):
            for node_name, output in step.items():
                if node_name == "__end__":
                    continue
                if isinstance(output, dict):
                    final.update(output)
                yield {"type": "progress", "data": {"node": node_name, "message": f"正在执行: {node_name}"}}
                if isinstance(output, dict) and output.get("error"):
                    yield {"type": "error", "data": {"error": output["error"]}}

        yield {"type": "intent", "data": {"intent": final.get("intent"), "entities": final.get("entities")}}
        yield {"type": "schema", "data": {"count": len(final.get("pruned_schemas", []))}}
        yield {"type": "sql", "data": {"sql": final.get("generated_sql")}}
        yield {"type": "result", "data": {
            "rows": final.get("execution_result", []),
            "explanation": final.get("formatted_result"),
            "chart": final.get("chart_suggestion"),
        }}
        yield {"type": "done", "data": {}}