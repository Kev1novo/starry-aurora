"""
意图解析节点
使用 LLM 对用户问题进行意图分类与实体提取，输出到 AgentState。
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.nl2sql_agent.parser import extract_json
from app.agents.nl2sql_agent.state import AgentState
from app.agents.shared.llm_factory import LLMFactory

_INTENT_SYSTEM_PROMPT = """你是一个 NL2SQL 意图解析器。你的职责是：

1. 识别用户自然语言查询的意图类型
2. 提取查询中涉及的时间范围、维度字段、度量指标等实体
3. 解析自然语言时间表达式为标准化时间范围

## 意图类型

| 类型 | 说明 | 示例 |
|------|------|------|
| data_query | 数据查询——用户要查数据（最常见） | "上个月的销售额是多少" |
| attribution | 归因分析——用户要做渠道归因 | "各渠道的转化贡献如何" |
| schema_explore | Schema 探索——用户想了解表结构 | "这个数据源有哪些表" |
| system | 系统类问题——与数据无关 | "你能做什么" |

## 输出格式

以 JSON 对象返回，字段说明：

```json
{
  "intent": "data_query",
  "reasoning": "简要说明判断依据",
  "entities": {
    "metrics": ["销售额"],
    "dimensions": ["渠道", "地区"],
    "filters": []
  },
  "time_range": {
    "start": null,
    "end": null,
    "granularity": null
  }
}
```

- metrics: 用户想查询的度量指标
- dimensions: 用户想按什么维度分组/筛选
- filters: 其他过滤条件
- time_range: 时间范围，{start: "YYYY-MM-DD", end: "YYYY-MM-DD", granularity: "day"|"week"|"month"|"quarter"|"year"|null}
  重要：将自然语言的时间表达转换为具体日期。
  例如 "上个月" → {"start": "2026-08-01", "end": "2026-08-31", "granularity": "month"}
       "昨天"   → {"start": "2026-09-14", "end": "2026-09-14", "granularity": "day"}
       "今年"   → {"start": "2026-01-01", "end": "2026-09-14", "granularity": "year"}
       "近7天"  → {"start": "2026-09-08", "end": "2026-09-14", "granularity": "day"}
  计算相对时间时以今天的日期 2026-09-15 为基准。
  如果问题中没有明确时间范围，start、end 和 granularity 全部设为 null。

只输出 JSON，不输出其他内容。"""


async def intent_parser_node(state: AgentState) -> dict[str, Any]:
    """意图解析节点

    从用户问题中解析意图、实体和时间范围，写入 AgentState。

    Args:
        state: 当前 AgentState

    Returns:
        更新到 state 的字段字典
    """
    question: str = state.get("question", "")
    if not question:
        return {
            "intent": "system",
            "entities": {},
            "time_range": None,
            "error": "问题为空",
        }

    llm = LLMFactory(temperature=0.0)

    prompt = f"用户问题：{question}\n\n请进行意图解析："
    raw = await llm.generate(
        [
            {"role": "system", "content": _INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
    )

    parsed = _parse_llm_response(raw)
    return {
        "intent": parsed.get("intent", "data_query"),
        "entities": parsed.get("entities", {}),
        "time_range": parsed.get("time_range"),
    }


def _parse_llm_response(raw: str) -> dict[str, Any]:
    """从 LLM 响应中提取并解析 JSON"""
    result = extract_json(raw)
    if result is not None:
        return result

    return {
        "intent": "data_query",
        "entities": {},
        "time_range": None,
    }