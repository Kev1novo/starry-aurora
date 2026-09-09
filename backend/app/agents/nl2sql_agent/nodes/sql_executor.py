"""
SQL 执行节点
在目标数据源上以只读事务方式执行 SQL，带超时和行数限制。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from app.agents.nl2sql_agent.state import AgentState
from app.core.exceptions import SQLExecutionError

# 默认查询超时（秒）
_DEFAULT_TIMEOUT = 30
# 最大返回行数
_MAX_ROWS = 1000


@dataclass
class DatasourceConnection:
    """数据源连接的轻量封装"""

    type: str  # mysql / postgresql / clickhouse
    host: str
    port: int
    database: str
    username: str
    password: str


async def sql_executor_node(state: AgentState) -> dict[str, Any]:
    """SQL 执行节点

    以只读事务方式执行生成的 SQL：
        1. 查找数据源连接信息
        2. 建立数据库连接（带超时）
        3. 执行 SQL（只读事务，行数限制）
        4. 返回结果或错误信息

    Args:
        state: 当前 AgentState

    Returns:
        更新到 state 的字段字典（execution_result, execution_error）
    """
    sql: str | None = state.get("generated_sql")
    datasource_id: int | None = state.get("datasource_id")

    if not sql:
        return {
            "execution_result": None,
            "execution_error": "SQL 为空",
        }

    if not datasource_id:
        return {
            "execution_result": None,
            "execution_error": "缺少 datasource_id",
        }

    try:
        conn = await _get_datasource_connection(datasource_id)
        result = await _execute_with_timeout(conn, sql)
        return {
            "execution_result": result,
            "execution_error": None,
            "error": None,
        }
    except SQLExecutionError as e:
        return {
            "execution_result": None,
            "execution_error": str(e),
            "error": str(e),
        }
    except Exception as e:
        error_msg = f"SQL 执行异常: {str(e)[:300]}"
        return {
            "execution_result": None,
            "execution_error": error_msg,
            "error": error_msg,
        }


# ---------- 连接管理 ----------


async def _get_datasource_connection(
    datasource_id: int,
    timeout: int = _DEFAULT_TIMEOUT,
) -> DatasourceConnection:
    """获取数据源连接信息

    从数据库元数据中查找指定数据源的连接配置，解密密码。

    Args:
        datasource_id: 数据源 ID
        timeout: 连接超时（秒）

    Returns:
        数据源连接信息

    Raises:
        SQLExecutionError: 数据源未找到或连接信息不完整
    """
    try:
        from app.core.database import AsyncSessionLocal
        from app.core.security import decrypt_password
        from app.models.datasource import DataSource
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            stmt = select(DataSource).where(DataSource.id == datasource_id)
            result = await session.execute(stmt)
            ds = result.scalar_one_or_none()

        if ds is None:
            raise SQLExecutionError(detail=f"数据源 {datasource_id} 不存在")

        decrypted = decrypt_password(ds.password)

        return DatasourceConnection(
            type=ds.type,
            host=ds.host,
            port=ds.port,
            database=ds.database_name,
            username=ds.username,
            password=decrypted,
        )
    except SQLExecutionError:
        raise
    except Exception as e:
        raise SQLExecutionError(detail=f"获取数据源连接信息失败: {str(e)[:200]}") from e


# ---------- 执行器 ----------


async def _execute_with_timeout(
    conn_info: DatasourceConnection,
    sql: str,
    timeout: int = _DEFAULT_TIMEOUT,
    max_rows: int = _MAX_ROWS,
) -> list[dict[str, Any]]:
    """带超时和行数限制的 SQL 执行

    根据数据源类型使用不同的数据库驱动执行 SQL。
    所有操作在只读事务内进行。

    Args:
        conn_info: 数据源连接信息
        sql: 要执行的 SQL
        timeout: 查询超时（秒）
        max_rows: 最大返回行数

    Returns:
        查询结果，列表[字典]，每个字典代表一行

    Raises:
        SQLExecutionError: 执行失败
    """
    try:
        async with asyncio.timeout(timeout):
            return await _execute(conn_info, sql, max_rows)
    except asyncio.TimeoutError:
        raise SQLExecutionError(detail=f"查询执行超时（{timeout}秒）")
    except SQLExecutionError:
        raise
    except Exception as e:
        raise SQLExecutionError(detail=str(e)[:300])


async def _execute(
    conn_info: DatasourceConnection,
    sql: str,
    max_rows: int,
) -> list[dict[str, Any]]:
    """根据数据源类型路由到对应的执行器"""
    db_type = conn_info.type.lower()
    if "postgresql" in db_type or conn_info.port == 5432:
        return await _execute_pg(conn_info, sql, max_rows)
    elif "clickhouse" in db_type or conn_info.port in (9000, 8123):
        return await _execute_ch(conn_info, sql, max_rows)
    else:
        return await _execute_mysql(conn_info, sql, max_rows)


async def _execute_mysql(
    conn_info: DatasourceConnection,
    sql: str,
    max_rows: int,
) -> list[dict[str, Any]]:
    """通过 aiomysql 执行 SQL"""
    import aiomysql

    pool = await aiomysql.create_pool(
        host=conn_info.host,
        port=conn_info.port,
        user=conn_info.username,
        password=conn_info.password,
        db=conn_info.database,
        minsize=1,
        maxsize=2,
        connect_timeout=10,
        cursorclass=aiomysql.cursors.DictCursor,
    )
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SET SESSION TRANSACTION READ ONLY")
                await cur.execute(sql)
                rows = await cur.fetchmany(size=max_rows)
                columns = [d[0] for d in cur.description] if cur.description else []
                return [dict(zip(columns, row)) for row in rows]
    finally:
        pool.close()
        await pool.wait_closed()


async def _execute_pg(
    conn_info: DatasourceConnection,
    sql: str,
    max_rows: int,
) -> list[dict[str, Any]]:
    """通过 asyncpg 执行 SQL"""
    import asyncpg

    conn = await asyncpg.connect(
        host=conn_info.host,
        port=conn_info.port,
        user=conn_info.username,
        password=conn_info.password,
        database=conn_info.database,
        timeout=10,
    )
    try:
        async with conn.transaction(readonly=True):
            rows = await conn.fetch(sql)
            if rows:
                columns = list(rows[0].keys())
                return [dict(zip(columns, row.values())) for row in rows]
            return []
    finally:
        await conn.close()


async def _execute_ch(
    conn_info: DatasourceConnection,
    sql: str,
    max_rows: int,
) -> list[dict[str, Any]]:
    """通过 HTTP 接口执行 ClickHouse SQL"""
    import json

    import aiohttp

    url = (
        f"http://{conn_info.host}:{conn_info.port}"
        f"/?query={sql}&user={conn_info.username}"
        f"&password={conn_info.password}"
        f"&database={conn_info.database}"
        f"&default_format=JSONCompact"
        f"&max_result_rows={max_rows}"
    )

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise SQLExecutionError(detail=f"ClickHouse 查询失败: {text[:200]}")
            text = await resp.text()
            data = json.loads(text)
            meta = data.get("meta", [])
            columns = [m["name"] for m in meta] if meta else []
            data_rows = data.get("data", [])
            result = []
            for row in data_rows:
                if columns:
                    result.append(dict(zip(columns, row)))
                else:
                    result.append({f"col_{i}": v for i, v in enumerate(row)})
            return result