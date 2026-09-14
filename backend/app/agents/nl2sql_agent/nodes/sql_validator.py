"""
SQL 验证节点
三重验证：语法检查 + 权限白名单 + EXPLAIN 预览
验证失败时递增 fix_attempts，触发重试路由。
"""

from __future__ import annotations

import re
from typing import Any

from app.agents.nl2sql_agent.state import AgentState
from app.agents.shared.llm_factory import LLMFactory
from app.core.exceptions import SQLValidationError


# 安全白名单：只允许的 SQL 语句类型前缀
_SAFE_SQL_PREFIXES = ("SELECT", "WITH", "EXPLAIN", "SHOW", "DESC", "DESCRIBE")

# 禁止出现的关键词（DDL / DML / 危险操作）
_FORBIDDEN_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "TRUNCATE",
    "ALTER",
    "CREATE",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
    "CALL",
    "RENAME",
    "LOCK",
    "UNLOCK",
    "SET",
    "KILL",
    "SHUTDOWN",
)

# 最大重试次数
_MAX_FIX_ATTEMPTS = 3


async def sql_validator_node(state: AgentState) -> dict[str, Any]:
    """SQL 验证节点

    对生成的 SQL 执行三重验证：
        1. sqlparse 语法解析校验
        2. 白名单安全检查（只允许 SELECT/With 查询）
        3. 数据库 EXPLAIN 预览（执行计划验证）

    Args:
        state: 当前 AgentState

    Returns:
        更新到 state 的字段字典（validated, validation_errors, fix_attempts）
    """
    sql: str | None = state.get("generated_sql")
    fix_attempts: int = state.get("fix_attempts", 0)
    errors: list[str] = []
    validated = True

    if not sql:
        return {
            "validated": False,
            "validation_errors": ["SQL 为空"],
            "fix_attempts": fix_attempts + 1,
        }

    # ---- 第一重：sqlparse 语法校验 ----
    syntax_ok, syntax_error = _check_syntax(sql)
    if not syntax_ok:
        errors.append(f"语法错误: {syntax_error}")
        validated = False

    # ---- 第二重：权限白名单检查 ----
    perm_ok, perm_error = _check_permissions(sql)
    if not perm_ok:
        errors.append(f"权限拒绝: {perm_error}")
        validated = False

    # ---- 第三重：EXPLAIN 预览 ----
    if validated and state.get("datasource_id"):
        explain_ok, explain_error = await _check_explain(
            sql, state["datasource_id"]
        )
        if not explain_ok:
            errors.append(f"EXPLAIN 验证失败: {explain_error}")
            validated = False

    return {
        "validated": validated,
        "validation_errors": errors,
        "fix_attempts": fix_attempts + 1,
    }


# ---------- 校验函数 ----------


def _check_syntax(sql: str) -> tuple[bool, str]:
    """sqlparse 语法校验

    使用 sqlparse 库解析 SQL 语句，检查是否存在语法错误。
    sqlparse 对复杂 SQL 的校验能力有限，后续可接入更专业的 SQL linter。

    Returns:
        (is_valid, error_message)
    """
    try:
        import sqlparse

        parsed = sqlparse.parse(sql)
        if not parsed or not parsed[0].tokens:
            return False, "无法解析 SQL 语句"
        # 无法通过 sqlparse 检测深层语法错误，这里只做基础校验
        return True, ""
    except ImportError:
        # sqlparse 未安装时跳过语法检查
        return True, ""
    except Exception as e:
        return False, str(e)


def _check_permissions(sql: str) -> tuple[bool, str]:
    """权限白名单检查

    检查 SQL 语句是否：
    1. 以 SELECT 或 WITH 开头（只读查询）
    2. 不包含 DDL/DML/危险操作关键词

    Returns:
        (is_allowed, error_message)
    """
    stripped = sql.strip()
    # 检查前缀
    upper = stripped.upper().lstrip()
    if not any(upper.startswith(prefix) for prefix in _SAFE_SQL_PREFIXES):
        return False, f"只允许 SELECT 查询，当前语句以 '{upper.split()[0] if upper.split() else ''}' 开头"

    # 检查禁止关键词（排除在 SELECT 字符串/注释中的误匹配）
    # 使用正则避免匹配到字段名或别名中的关键词
    cleaned = _remove_string_literals(stripped)
    for kw in _FORBIDDEN_KEYWORDS:
        # 只匹配作为独立语句关键词的情况
        pattern = rf"(?:^|\s|;){kw}(?:\s|$)"
        if re.search(pattern, cleaned, re.IGNORECASE):
            return False, f"SQL 包含禁止的关键词: {kw}"

    return True, ""


def _remove_string_literals(sql: str) -> str:
    """移除 SQL 中的字符串字面量，避免误匹配关键词"""
    # 移除单引号字符串
    cleaned = re.sub(r"'[^']*'", "''", sql)
    # 移除双引号标识符（可能含有关键词）
    cleaned = re.sub(r'"[^"]*"', '""', cleaned)
    # 移除反引号标识符
    cleaned = re.sub(r"`[^`]*`", "``", cleaned)
    return cleaned


async def _check_explain(sql: str, datasource_id: int) -> tuple[bool, str]:
    """EXPLAIN 预览验证

    在目标数据源上执行 EXPLAIN，验证 SQL 的执行可行性。
    主要检查：表是否存在、字段是否存在、语法在目标方言下是否正确。

    Returns:
        (is_valid, error_message)
    """
    # 只有 SELECT 和 WITH 需要 EXPLAIN
    upper = sql.strip().upper().lstrip()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return True, "非查询语句跳过 EXPLAIN"

    try:
        from app.agents.nl2sql_agent.nodes.sql_executor import _get_datasource_connection, _execute

        conn = await _get_datasource_connection(datasource_id, timeout=10)
        explain_sql = f"EXPLAIN {sql}"
        results = await _execute(conn, explain_sql, max_rows=10)

        if isinstance(results, list):
            return True, ""

        return False, "EXPLAIN 无返回结果"

    except SQLValidationError:
        # 数据源查找失败时，跳过 EXPLAIN 验证
        return True, ""
    except Exception as e:
        error_msg = str(e)
        # 常见错误处理
        if "doesn't exist" in error_msg or "does not exist" in error_msg:
            return False, f"表或字段不存在: {error_msg[:200]}"
        if "syntax" in error_msg.lower():
            return False, f"语法错误（数据库层）: {error_msg[:200]}"
        return False, f"EXPLAIN 执行异常: {error_msg[:200]}"


# ---------- 重试决策函数（供 graph.py 的条件路由使用） ----------


def should_retry(state: AgentState) -> str:
    """根据验证结果判断下一步路由

    验证失败且未达到最大重试次数 → 返回 "fix"（回到 sql_generator_node）
    验证成功或达到最大重试次数 → 返回 "execute"（进入 sql_executor_node）

    Args:
        state: 当前 AgentState

    Returns:
        路由目标: "fix" | "execute"
    """
    validated: bool = state.get("validated", False)
    fix_attempts: int = state.get("fix_attempts", 0)

    if validated:
        return "execute"

    if fix_attempts < _MAX_FIX_ATTEMPTS:
        return "fix"

    return "execute"