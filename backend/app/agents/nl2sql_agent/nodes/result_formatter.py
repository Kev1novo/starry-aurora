"""
结果格式化节点
将 SQL 执行结果生成自然语言解释和图表类型建议。
"""

from __future__ import annotations

from typing import Any

from app.agents.nl2sql_agent.state import AgentState
from app.agents.shared.llm_factory import LLMFactory


async def result_formatter_node(state: AgentState) -> dict[str, Any]:
    """结果格式化节点

    基于执行结果，生成：
        1. 自然语言解释（通过 LLM）
        2. 图表类型建议（基于数据形状规则）

    Args:
        state: 当前 AgentState

    Returns:
        更新到 state 的字段字典（formatted_result, chart_suggestion）
    """
    question: str = state.get("question", "")
    execution_result: list[dict[str, Any]] | None = state.get("execution_result")
    execution_error: str | None = state.get("execution_error")
    generated_sql: str | None = state.get("generated_sql")

    # 执行失败时的格式化
    if execution_error or execution_result is None:
        return {
            "formatted_result": f"查询执行失败: {execution_error or '未知错误'}",
            "chart_suggestion": None,
            "error": execution_error,
        }

    if not execution_result:
        return {
            "formatted_result": "查询执行成功，但未返回任何数据（结果集为空）。",
            "chart_suggestion": "table",
        }

    # 生成自然语言解释
    formatted = await _generate_explanation(question, execution_result, generated_sql)

    # 生成图表类型建议
    chart = _suggest_chart_type(execution_result)

    return {
        "formatted_result": formatted,
        "chart_suggestion": chart,
        "error": None,
    }


async def _generate_explanation(
    question: str,
    results: list[dict[str, Any]],
    sql: str | None,
) -> str:
    """使用 LLM 生成结果的自然语言解释"""
    # 截取前 20 行作为上下文，避免超出 token 限制
    sample_size = min(len(results), 20)
    sample = results[:sample_size]

    # 构建数据摘要
    num_rows = len(results)
    columns = list(results[0].keys()) if results else []
    num_cols = len(columns)
    sample_text = "\n".join(
        f"  Row {i + 1}: {dict(row)}" for i, row in enumerate(sample)
    )

    llm = LLMFactory(temperature=0.3, max_tokens=512)
    prompt = f"""## 用户问题
{question}

## SQL 查询
{sql or '（未记录）'}

## 查询结果
- 返回行数: {num_rows}
- 返回字段: {', '.join(columns)}
- 字段数: {num_cols}

## 示例数据（前 {sample_size} 行）
{sample_text}

请用自然语言总结查询结果，关注数据中的关键发现、趋势、异常值等。
语言简洁、专业、与原始问题对应。
不要解释 SQL，直接说数据反映了什么。"""

    explanation = await llm.generate(
        [{"role": "user", "content": prompt}]
    )
    return explanation.strip()


def _suggest_chart_type(
    results: list[dict[str, Any]],
) -> str:
    """根据数据形状自动推荐图表类型

    规则：
        - 0 行数据 → table
        - 1 字段 → table
        - 2 字段（一个数值一个非数值）→ bar（或 pie 如果非数值维度取值 <= 6）
        - 3+ 字段且有时间字段 → line
        - 3+ 字段无时间字段 → table
        - 结果行数 <= 10 且有可枚举维度 → table

    Args:
        results: 查询结果数据集

    Returns:
        图表示例: "table" | "bar" | "line" | "pie"
    """
    if not results:
        return "table"

    columns = list(results[0].keys())
    num_cols = len(columns)
    num_rows = len(results)

    # 单字段 → 纯表格
    if num_cols <= 1:
        return "table"

    # 识别数值字段和非数值字段
    numeric_cols: list[str] = []
    non_numeric_cols: list[str] = []
    time_cols: list[str] = []

    for col in columns:
        sample_vals = [
            row[col] for row in results[:5] if row.get(col) is not None
        ]
        if _is_time_column(col, sample_vals):
            time_cols.append(col)
        elif _is_numeric_column(sample_vals):
            numeric_cols.append(col)
        else:
            non_numeric_cols.append(col)

    # 有时间字段且有数值 → 折线图
    if time_cols and numeric_cols:
        return "line"

    # 两个字段：一个非数值维度 + 一个数值 → bar 或 pie
    if len(non_numeric_cols) == 1 and len(numeric_cols) >= 1:
        if num_rows <= 6 and num_rows > 1:
            return "pie"
        return "bar"

    # 两个数值字段 → bar
    if len(numeric_cols) >= 2 and not non_numeric_cols:
        return "bar"

    # 默认：表格
    return "table"


def _is_numeric_column(sample_values: list[Any]) -> bool:
    """判断字段是否为数值类型"""
    for v in sample_values:
        if v is None:
            continue
        if isinstance(v, (int, float)):
            return True
        if isinstance(v, str):
            v = v.strip()
            if v.replace(".", "").replace("-", "").replace(",", "").isdigit():
                return True
        return False
    return False


def _is_time_column(name: str, sample_values: list[Any]) -> bool:
    """根据字段名和样例值判断是否为时间字段"""
    time_keywords = (
        "time", "date", "year", "month", "day", "hour", "minute",
        "second", "week", "quarter", "时间", "日期", "年", "月", "日",
    )
    name_lower = name.lower().replace("_", "").replace("-", "")
    for kw in time_keywords:
        if kw in name_lower:
            return True

    # 检查样例值是否像时间格式
    import re

    date_patterns = [
        r"^\d{4}-\d{2}-\d{2}",  # 2024-01-01
        r"^\d{4}/\d{2}/\d{2}",  # 2024/01/01
        r"^\d{4}年\d{1,2}月",  # 2024年1月
    ]
    for v in sample_values[:3]:
        if v is None:
            continue
        if isinstance(v, str):
            for pat in date_patterns:
                if re.match(pat, v.strip()):
                    return True
    return False