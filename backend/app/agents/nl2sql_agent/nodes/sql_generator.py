"""
SQL 生成节点
基于意图、Schema 上下文和 Chain-of-Thought 推理生成 SQL 查询。
"""

from __future__ import annotations

from typing import Any

from app.agents.nl2sql_agent.parser import extract_json
from app.agents.nl2sql_agent.state import AgentState
from app.agents.shared.llm_factory import LLMFactory


# Maximum schema fields to include in the prompt context
_MAX_SCHEMA_IN_PROMPT = 50


_SYSTEM_PROMPT = """你是一个专业的 NL2SQL 生成器。你的任务是将自然语言问题转换为可执行的 SQL 查询。

## 规则

1. **只生成 SELECT 查询**。禁止 DDL、DML、DDL 语句（INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, TRUNCATE）。
2. **使用标准 SQL**，兼容 MySQL/PostgreSQL 语法。根据用户提供的 Schema 信息选择合适的方言。
3. **只在用户提供的 Schema 字段范围内生成 SQL**，不要猜测不存在的表或字段。
4. **善用字段描述**理解业务含义，确保生成的 SQL 符合业务语义。
5. **对数值型字段做聚合时**（SUM, AVG, COUNT 等），使用明确的别名。
6. **对时间字段做筛选时**，使用 WHERE 条件而非 HAVING。
7. **当问题涉及排序时**，使用 ORDER BY 子句。
8. **当问题涉及分组时**，使用 GROUP BY 子句。
9. **当需要去重时**，使用 DISTINCT。
10. **结果行数不超过 1000 行**，使用 LIMIT 1000。

## 输出格式

以 JSON 格式返回，包含 Chain-of-Thought 推理过程和最终 SQL：

```json
{
  "reasoning": "分析用户需求的逐步推理过程",
  "sql": "SELECT ...",
  "explanation": "SQL 查询的简要说明"
}
```

## 工作步骤（Chain-of-Thought）

1. **理解问题**：分析用户想查什么数据
2. **匹配 Schema**：将问题中的业务概念与 Schema 字段对应
3. **确定表名和字段**：找出涉及的表和字段
4. **确定聚合和分组**：是否需要 GROUP BY、聚合函数
5. **确定过滤条件**：WHERE 子句的条件
6. **确定排序**：ORDER BY 子句
7. **生成 SQL**：组装最终的 SQL"""


async def sql_generator_node(state: AgentState) -> dict[str, Any]:
    """SQL 生成节点

    基于用户问题、检索到的 Schema 信息和意图，通过 Chain-of-Thought
    推理生成 SQL 查询语句。

    Args:
        state: 当前 AgentState，需包含 question、pruned_schemas、intent

    Returns:
        更新到 state 的字段字典（generated_sql）
    """
    question: str = state.get("question", "")
    schemas: list[dict[str, Any]] = state.get("pruned_schemas", [])
    intent: str = state.get("intent", "data_query")
    entities: dict[str, Any] = state.get("entities", {})
    time_range: dict[str, Any] | None = state.get("time_range")

    if not question:
        return {"error": "问题为空"}

    if intent == "schema_explore":
        # Schema 探索类问题无需生成 SQL，直接返回
        return {
            "generated_sql": None,
        }

    if not schemas:
        return {
            "error": "缺少 Schema 上下文，无法生成 SQL",
        }

    # 构建 Schema 上下文文本
    schema_context = _build_schema_context(schemas)
    # 构建实体上下文
    entity_context = _build_entity_context(entities, time_range)

    llm = LLMFactory(temperature=0.0)

    user_prompt = f"""## 用户问题
{question}

## Schema 上下文
{schema_context}

## 实体信息
{entity_context}

## 意图类型
{intent}

请按照 Chain-of-Thought 步骤分析并生成 SQL。"""

    raw = await llm.generate(
        [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )

    parsed = _parse_llm_response(raw)

    return {
        "generated_sql": parsed.get("sql"),
    }


def _build_schema_context(schemas: list[dict[str, Any]]) -> str:
    """将 Schema 字段列表转换为文本描述"""
    limited = schemas[:_MAX_SCHEMA_IN_PROMPT]

    # 按表名分组
    tables: dict[str, list[dict[str, Any]]] = {}
    for s in limited:
        tbl = s.get("table_name", "unknown")
        if tbl not in tables:
            tables[tbl] = []
        tables[tbl].append(s)

    lines: list[str] = []
    for tbl, cols in tables.items():
        lines.append(f"表 {tbl}:")
        for c in cols:
            col_name = c.get("column_name", "?")
            data_type = c.get("data_type", "?")
            desc = c.get("description") or c.get("column_comment") or ""
            pk = " [PK]" if c.get("is_primary_key") else ""
            fk = " [FK]" if c.get("is_foreign_key") else ""
            nullable = " NULL" if c.get("is_nullable") else " NOT NULL"
            lines.append(f"  - {col_name} ({data_type}){nullable}{pk}{fk}  {desc}")
        lines.append("")

    return "\n".join(lines)


def _build_entity_context(
    entities: dict[str, Any],
    time_range: dict[str, Any] | None,
) -> str:
    """将实体信息转换为文本"""
    parts: list[str] = []
    metrics = entities.get("metrics", [])
    dimensions = entities.get("dimensions", [])
    filters = entities.get("filters", [])

    if metrics:
        parts.append(f"度量指标: {', '.join(metrics)}")
    if dimensions:
        parts.append(f"维度: {', '.join(dimensions)}")
    if filters:
        parts.append(f"过滤条件: {', '.join(filters)}")
    if time_range:
        if time_range.get("start") and time_range.get("end"):
            parts.append(
                f"时间范围: {time_range['start']} ~ {time_range['end']}"
            )
        if time_range.get("granularity"):
            parts.append(f"时间粒度: {time_range['granularity']}")

    return "\n".join(parts) if parts else "未提取到明确实体"


def _parse_llm_response(raw: str) -> dict[str, Any]:
    """从 LLM 响应中提取 JSON"""
    result = extract_json(raw)
    if result is not None:
        # 兼容不同模型的字段命名（sql / query / SQL）
        sql = result.get("sql") or result.get("SQL") or result.get("query")
        return {"sql": sql}

    # 如果 LLM 直接返回了 SQL（没有 JSON 包裹），将其作为 sql 字段
    stripped = raw.strip()
    if stripped.upper().startswith("SELECT") or stripped.upper().startswith("WITH"):
        return {"sql": stripped}

    return {"sql": None}