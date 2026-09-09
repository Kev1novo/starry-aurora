"""SQL 执行工具"""
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def execute_sql(
    db: AsyncSession,
    sql: str,
    timeout: int = 30,
    row_limit: int = 1000,
) -> dict[str, Any]:
    """安全执行 SQL 查询"""
    if not sql.strip().upper().startswith("SELECT"):
        return {"error": "只允许 SELECT 查询", "rows": []}

    try:
        result = await db.execute(text(sql))
        rows = result.fetchmany(row_limit)
        columns = result.keys()

        return {
            "columns": list(columns),
            "rows": [dict(zip(columns, row)) for row in rows],
            "row_count": len(rows),
        }
    except Exception as e:
        return {"error": str(e), "rows": []}


def validate_sql_safety(sql: str) -> tuple[bool, list[str]]:
    """SQL 安全校验"""
    errors = []
    upper = sql.strip().upper()

    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "EXEC", "CALL"]
    for word in forbidden:
        if word in upper.split():
            errors.append(f"禁止使用 {word} 语句")

    dangerous_keywords = ["INFORMATION_SCHEMA", "PG_SLEEP", "SLEEP", "BENCHMARK"]
    for kw in dangerous_keywords:
        if kw in upper:
            errors.append(f"包含敏感关键字: {kw}")

    return len(errors) == 0, errors