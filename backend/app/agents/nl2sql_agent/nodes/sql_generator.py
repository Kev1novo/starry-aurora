"""
SQL 生成节点
基于意图、Schema 上下文和 Chain-of-Thought 推理生成 SQL 查询。
生成后自动注入时间范围过滤条件（避免 LLM 遗漏或猜错时间字段）。
"""

from __future__ import annotations

import re
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
7. **当实体信息中包含 time_range 时，必须将其转换为 SQL WHERE 条件**。
     首先找到"时间字段"列表中的列，确定它在哪个表中。
     WHERE 条件中引用的时间列必须使用该表对应的别名
     （如 o.created_at 而非 oi.created_at），必要时 JOIN 该表。
     WHERE 子句必须放在 FROM/JOIN 之后、ORDER BY/LIMIT/GROUP BY 之前，不能放在 RANK() OVER() 等窗口函数内部。
8. **当问题涉及排序时**，使用 ORDER BY 子句。
9. **当问题涉及分组时**，使用 GROUP BY 子句。
10. **当需要去重时**，使用 DISTINCT。
11. **结果行数不超过 1000 行**，使用 LIMIT 1000。

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
5. **确定过滤条件**：WHERE 子句的条件。如果实体信息中有 time_range，必须选择"时间过滤要求"中指定的字段进行过滤，不可跳过。
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
    all_retrieved: list[dict[str, Any]] = state.get("retrieved_schemas", [])
    intent: str = state.get("intent", "data_query")
    entities: dict[str, Any] = state.get("entities", {})
    time_range: dict[str, Any] | None = state.get("time_range")
    validation_errors: list[str] = state.get("validation_errors", [])
    fix_attempts: int = state.get("fix_attempts", 0)
    datasource_id: int | None = state.get("datasource_id")

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
    # 构建时间过滤指令（从数据库 schema 查找实际时间字段）
    time_instruction = await _build_time_instruction(datasource_id, time_range, intent)
    # 构建 fix 反馈（如果有之前的错误）
    fix_feedback = _build_fix_feedback(validation_errors, fix_attempts)

    llm = LLMFactory(temperature=0.0)

    user_prompt = f"""## 用户问题
{question}

## Schema 上下文
{schema_context}

## 实体信息
{entity_context}

## 意图类型
{intent}
{time_instruction}
{fix_feedback}
请按照 Chain-of-Thought 步骤分析并生成 SQL。"""

    raw = await llm.generate(
        [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )

    parsed = _parse_llm_response(raw)
    sql = parsed.get("sql")

    # 程序化注入时间范围过滤（兜底，LLM 可能遗漏或猜错时间字段）
    sql = await _inject_time_filter(sql, datasource_id, time_range)

    return {
        "generated_sql": sql,
    }


async def _inject_time_filter(
    sql: str | None,
    datasource_id: int | None,
    time_range: dict | None,
) -> str | None:
    """程序化注入时间范围过滤条件

    当 LLM 生成的 SQL 缺少时间过滤（或用了错误的列名）时，
    自动查找实际的时间字段并注入正确的 WHERE 条件。
    """
    if not sql or not datasource_id or not time_range:
        return sql
    start = time_range.get("start")
    end = time_range.get("end")
    if not start and not end:
        return sql

    # 从数据库查询时间字段
    from app.repositories.schema_repo import SchemaMetaRepository
    from app.core.database import AsyncSessionLocal

    time_cols: list[tuple[str, str]] = []
    try:
        async with AsyncSessionLocal() as db:
            repo = SchemaMetaRepository(db)
            all_fields = await repo.list(limit=10000)
            time_types = {"datetime", "timestamp", "date"}
            for f in all_fields:
                if f.datasource_id != datasource_id:
                    continue
                base_type = (f.data_type or "").split("(")[0].lower()
                if base_type in time_types:
                    time_cols.append((f.table_name, f.column_name))
    except Exception:
        return sql

    if not time_cols:
        return sql

    # 检查 SQL 是否已包含时间过滤：只要 WHERE 子句中已引用任一时间字段列名
    # （无论表名还是别名形式，如 o.order_date / orders.order_date），就认为
    # LLM 已正确处理，不再程序化注入（避免重复注入或引用不存在的别名）。
    upper_sql = sql.upper()
    where_idx = upper_sql.find("WHERE")
    if where_idx != -1:
        where_tail = upper_sql[where_idx:]
        for tbl, col in time_cols:
            if col.upper() in where_tail:
                return sql

    # 选择一个时间字段：
    # 优先选业务时间字段（排除 created_at/updated_at 等记录元数据时间），
    # 且优先选 FROM/JOIN 中已出现的表。
    sql_lower = sql.lower()
    _meta_time = {"created_at", "updated_at", "deleted_at", "create_time", "update_time"}

    def _appears_in_sql(tbl: str) -> bool:
        return tbl.lower() in sql_lower

    best_col: tuple[str, str] | None = None
    # 第一轮：业务时间 + 表在 SQL 中
    for tbl, col in time_cols:
        if _appears_in_sql(tbl) and col.lower() not in _meta_time:
            best_col = (tbl, col)
            break
    # 第二轮：表在 SQL 中（元数据时间也接受）
    if not best_col:
        for tbl, col in time_cols:
            if _appears_in_sql(tbl):
                best_col = (tbl, col)
                break
    # 兜底：任意时间字段
    if not best_col:
        best_col = time_cols[0]

    tbl, col = best_col

    # 检测表是否有别名（FROM/JOIN orders o → 别名 o）
    alias = tbl.lower()
    import re as _re
    # 匹配 FROM/JOIN tablename [AS] alias 模式
    alias_pattern = _re.compile(
        r'(?:FROM|JOIN)\s+' + _re.escape(tbl.lower()) + r'(?:\s+AS)?\s+(\w+)',
        _re.IGNORECASE,
    )
    alias_match = alias_pattern.search(sql)
    if alias_match:
        alias = alias_match.group(1)
        # 确保别名不是 SQL 关键字（如 WHERE、ON、JOIN 等）
        if alias.upper() in {'WHERE', 'ON', 'JOIN', 'AND', 'OR', 'AS', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'CROSS'}:
            alias = tbl.lower()

    where_clause = f"{alias}.{col} BETWEEN '{start}' AND '{end}'"

    # 去掉 LLM 可能添加的错误 WHERE 子句
    # 只处理最后一个 FROM/JOIN 之后的 WHERE（避免误伤 OVER() 或子查询中的 WHERE）
    upper_sql = sql.upper()

    # 找到 FROM/JOIN 部分的结束位置（最后一个 JOIN 或 FROM 之后）
    from_join_end = 0
    for kw in ["JOIN ", "JOIN\t", "JOIN\n"]:
        idx = upper_sql.rfind(kw)
        if idx > from_join_end:
            from_join_end = idx
    from_kw = "FROM "
    from_idx = upper_sql.rfind(from_kw)
    if from_idx > from_join_end:
        from_join_end = from_idx + len(from_kw)
        # 找到 FROM 的表名结束位置
        rest = upper_sql[from_join_end:]
        # 跳过可能的表名和别名
        end_pos = 0
        for c in rest:
            if c in (' ', '\t', '\n', '\r'):
                end_pos += 1
            else:
                break
        from_join_end += end_pos

    # 在 FROM/JOIN 部分之后查找 WHERE
    where_idx = upper_sql.find("WHERE", from_join_end)
    if where_idx != -1:
        # 检查这个 WHERE 是否在 OVER() 内（在找到 WHERE 之前，检查是否有未闭合的 OVER）
        before_where = upper_sql[:where_idx]
        over_count = before_where.count("OVER(")
        close_paren = before_where.count(")")
        # 简单的启发式判断：如果 OVER( 比 ) 多，说明 WHERE 在 OVER() 内，不处理
        if over_count > close_paren:
            # WHERE 在 OVER() 内部——我们需要去掉 OVER 及其内容
            # 找到最后一个 OVER( 的位置
            last_over = before_where.rfind("OVER(")
            sql = sql[:last_over].rstrip()
        else:
            # 截掉 WHERE 及之后的内容
            sql = sql[:where_idx].rstrip()

    # 在 GROUP BY / ORDER BY / LIMIT / HAVING 之前插入
    # 必须只匹配「括号深度 0（top-level）」的关键字，避免命中
    # DENSE_RANK() OVER (ORDER BY ...) 等窗口函数内部的 ORDER BY。
    def _find_top_level(s: str, keyword: str) -> int:
        """在括号深度为 0 的位置查找关键字，返回位置或 -1"""
        upper = s.upper()
        kw = keyword.upper()
        n = len(kw)
        depth = 0
        i = 0
        while i < len(s):
            c = s[i]
            if c == "(":
                depth += 1
                i += 1
                continue
            if c == ")":
                depth = max(0, depth - 1)
                i += 1
                continue
            if depth == 0 and upper.startswith(kw, i):
                before_ok = i == 0 or not (upper[i - 1].isalnum() or upper[i - 1] == "_")
                after = i + n
                after_ok = after >= len(s) or not (upper[after].isalnum() or upper[after] == "_")
                if before_ok and after_ok:
                    return i
            i += 1
        return -1

    insert_pos = len(sql)
    for keyword in ["GROUP BY", "ORDER BY", "LIMIT", "HAVING"]:
        idx = _find_top_level(sql, keyword)
        if idx != -1 and idx < insert_pos:
            insert_pos = idx

    before = sql[:insert_pos].rstrip()
    after = sql[insert_pos:]

    return f"{before} WHERE {where_clause} {after}".strip()


async def _build_time_instruction(
    datasource_id: int | None,
    time_range: dict[str, Any] | None,
    intent: str,
) -> str:
    """当有 time_range 时，从数据库直接查询时间字段，生成明确的过滤指令"""
    if not time_range or not datasource_id:
        return ""
    start = time_range.get("start")
    end = time_range.get("end")
    if not start and not end:
        return ""

    # 从数据库 schema 查询该数据源所有时间类型字段
    from app.repositories.schema_repo import SchemaMetaRepository
    from app.core.database import AsyncSessionLocal

    time_fields: list[str] = []
    try:
        async with AsyncSessionLocal() as db:
            repo = SchemaMetaRepository(db)
            all_fields = await repo.list(limit=10000)
            time_types = {"datetime", "timestamp", "date", "time"}
            for f in all_fields:
                if f.datasource_id != datasource_id:
                    continue
                base_type = (f.data_type or "").split("(")[0].lower()
                if base_type in time_types:
                    time_fields.append(
                        f"  - {f.table_name}.{f.column_name} ({f.data_type})"
                        f" - {f.description or f.column_comment or ''}"
                    )
    except Exception:
        pass

    if not time_fields:
        return ""

    fields_str = "\n".join(time_fields)

    return f"""
## 时间过滤要求（必须执行）

查询时间范围：{start or '不限'} ~ {end or '不限'}。

该数据源中可用于时间过滤的字段（表名.列名）：
{fields_str}

你必须：
1. 从上面的列表中选择一个时间字段用于 WHERE 子句
2. 如果该字段所在的表不在当前查询的 JOIN 中，必须先添加 JOIN
3. 时间字段引用时必须带上表别名（如 t.column_name）
4. 不可使用不在上述列表中的时间字段，不可凭空编造
"""


def _build_fix_feedback(
    validation_errors: list[str],
    fix_attempts: int,
) -> str:
    """构建 fix 反馈信息（给 LLM 修正参考）"""
    if not validation_errors:
        return ""
    errors_str = "\n".join(f"  - {e}" for e in validation_errors)
    return f"""
## 上一次 SQL 的错误反馈（第 {fix_attempts} 次修正）

以下 SQL 在验证/执行阶段失败，请参考错误信息修正：

{errors_str}

请根据 Schema 上下文中实际存在的表和字段进行修正，不要使用不存在的列。
如果错误是 Unknown column，检查该列属于哪个表，必要时添加 JOIN 以引入目标表。
"""


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

    # 额外列出所有时间字段（便于 WHERE 条件选择正确的列）
    time_cols: list[str] = []
    time_types = {"datetime", "timestamp", "date", "time"}
    for s in limited:
        base_type = s.get("data_type", "").split("(")[0].lower()
        if base_type in time_types:
            time_cols.append(
                f"  - {s['table_name']}.{s['column_name']} ({s['data_type']})"
                f" - {s.get('description') or s.get('column_comment') or ''}"
            )
    if time_cols:
        lines.append("时间字段（可用于 WHERE 条件过滤）:")
        lines.extend(time_cols)
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
        start = time_range.get("start") or "不限"
        end = time_range.get("end") or "不限"
        parts.append(f"时间范围: {start} ~ {end}")
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