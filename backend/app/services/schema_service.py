"""
Schema 元数据服务层
封装从数据源同步表结构、AI 增强字段描述、以及 Schema 查询等业务逻辑。
"""

import json
import urllib.parse
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.security import decrypt_password
from app.models.datasource import DataSource
from app.models.schema_meta import SchemaMeta
from app.repositories.datasource_repo import DataSourceRepository
from app.repositories.schema_repo import SchemaMetaRepository


class SyncResult:
    """Schema 同步结果"""

    def __init__(self, tables_count: int, fields_count: int) -> None:
        self.tables_count = tables_count
        self.fields_count = fields_count


class SchemaService:
    """
    Schema 元数据服务

    处理数据库表结构的自动同步、字段语义描述的 AI 生成、以及 Schema 信息查询。
    依赖 Qdrant 存储向量嵌入、ES 提供全文检索（预留）。
    """

    def __init__(
        self,
        db: AsyncSession,
        qdrant_client: Any = None,
        es_client: Any = None,
    ) -> None:
        self.db = db
        self.schema_repo = SchemaMetaRepository(db)
        self.ds_repo = DataSourceRepository(db)
        self.qdrant_client = qdrant_client
        self.es_client = es_client

    async def sync_datasource_schemas(self, ds_id: int) -> SyncResult:
        """
        同步指定数据源的表结构

        通过连接目标数据库查询 INFORMATION_SCHEMA，
        获取所有表及字段信息，替换本地存储的旧 Schema 记录。

        Args:
            ds_id: 数据源 ID

        Returns:
            同步结果，包含同步的表数量和字段总数

        Raises:
            NotFoundException: 数据源不存在
        """
        datasource = await self.ds_repo.get(ds_id)
        if datasource is None:
            raise NotFoundException(detail=f"数据源 {ds_id} 不存在")

        conn_info = self._get_connection_info(datasource)
        tables = await self._fetch_schema_from_db(conn_info)

        # 删除旧的 Schema 记录
        await self.schema_repo.delete_by_datasource(ds_id)

        # 批量创建新的 Schema 记录
        fields_count = 0
        for table_name, columns in tables.items():
            fields: List[SchemaMeta] = []
            for col in columns:
                fields.append(
                    SchemaMeta(
                        datasource_id=ds_id,
                        table_name=table_name,
                        column_name=col["column_name"],
                        ordinal_position=col["ordinal_position"],
                        data_type=col["data_type"],
                        is_nullable=col.get("is_nullable", True),
                        column_default=col.get("column_default"),
                        column_comment=col.get("column_comment"),
                        is_primary_key=col.get("is_primary_key", False),
                        is_foreign_key=col.get("is_foreign_key", False),
                        indexed=col.get("indexed", False),
                    )
                )
                fields_count += 1

            if fields:
                await self.schema_repo.batch_create(fields)

        return SyncResult(tables_count=len(tables), fields_count=fields_count)

    async def generate_field_description(
        self, ds_id: int, table: str, column: str
    ) -> str:
        """
        根据字段名和类型生成语义描述（占位实现，先用规则生成）

        后续可集成 LLM 调用，根据字段名、数据类型及表名生成更准确的业务语义。

        Args:
            ds_id: 数据源 ID
            table: 表名
            column: 字段名

        Returns:
            字段的语义描述文本

        Raises:
            NotFoundException: 字段不存在
        """
        fields = await self.schema_repo.get_by_table(ds_id, table)
        target = next((f for f in fields if f.column_name == column), None)
        if target is None:
            raise NotFoundException(
                detail=f"表 {table} 中未找到字段 {column}"
            )

        # 规则生成描述：若已有数据库注释则优先使用，否则根据命名规则推断
        if target.column_comment:
            return target.column_comment

        description = self._infer_description_from_name(
            column, target.data_type, table
        )
        return description

    # ---- 内部辅助方法 ----

    def _get_connection_info(self, datasource: DataSource) -> Dict[str, Any]:
        """
        从数据源模型提取连接参数字典

        Args:
            datasource: 数据源模型实例

        Returns:
            包含连接参数的字典（密码已解密）
        """
        db_info: Dict[str, Any] = {
            "host": datasource.host,
            "port": datasource.port,
            "database": datasource.database_name,
            "user": datasource.username,
            "password": decrypt_password(datasource.password),
            "type": datasource.type,
        }
        if datasource.extra_params:
            try:
                extra = json.loads(datasource.extra_params)
                db_info.update(extra)
            except (json.JSONDecodeError, TypeError):
                pass
        return db_info

    async def _fetch_schema_from_db(
        self, conn_info: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        从目标数据库查询 INFORMATION_SCHEMA 获取表结构

        Args:
            conn_info: 连接参数字典

        Returns:
            嵌套字典：{表名: [{字段信息}]}
        """
        db_type = conn_info["type"]

        if db_type == "postgresql":
            return await self._fetch_pg_schema(conn_info)
        elif db_type == "clickhouse":
            return await self._fetch_ck_schema(conn_info)
        else:
            # 默认按 MySQL 处理
            return await self._fetch_mysql_schema(conn_info)

    async def _fetch_mysql_schema(
        self, conn_info: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """从 MySQL INFORMATION_SCHEMA 获取表结构"""
        import aiomysql

        pool = await aiomysql.create_pool(
            host=conn_info["host"],
            port=conn_info["port"],
            user=conn_info["user"],
            password=conn_info["password"],
            db=conn_info["database"],
            minsize=1,
            maxsize=1,
        )
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(
                        """
                        SELECT
                            TABLE_NAME,
                            COLUMN_NAME,
                            ORDINAL_POSITION,
                            DATA_TYPE,
                            IS_NULLABLE,
                            COLUMN_DEFAULT,
                            COLUMN_COMMENT,
                            COLUMN_KEY
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = %s
                        ORDER BY TABLE_NAME, ORDINAL_POSITION
                        """,
                        (conn_info["database"],),
                    )
                    rows = await cur.fetchall()
        finally:
            pool.close()
            await pool.wait_closed()

        tables: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            table_name = row["TABLE_NAME"]
            if table_name not in tables:
                tables[table_name] = []
            col_key = row.get("COLUMN_KEY", "")
            tables[table_name].append(
                {
                    "column_name": row["COLUMN_NAME"],
                    "ordinal_position": row["ORDINAL_POSITION"],
                    "data_type": row["DATA_TYPE"],
                    "is_nullable": row["IS_NULLABLE"].upper() == "YES",
                    "column_default": row["COLUMN_DEFAULT"],
                    "column_comment": row["COLUMN_COMMENT"] or None,
                    "is_primary_key": col_key == "PRI",
                    "is_foreign_key": False,
                    "indexed": col_key in ("PRI", "MUL", "UNI"),
                }
            )
        return tables

    async def _fetch_pg_schema(
        self, conn_info: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """从 PostgreSQL INFORMATION_SCHEMA 获取表结构"""
        import asyncpg

        conn = await asyncpg.connect(
            host=conn_info["host"],
            port=conn_info["port"],
            user=conn_info["user"],
            password=conn_info["password"],
            database=conn_info["database"],
        )
        try:
            rows = await conn.fetch(
                """
                SELECT
                    t.table_name,
                    c.column_name,
                    c.ordinal_position,
                    c.data_type,
                    c.is_nullable,
                    c.column_default,
                    pgd.description AS column_comment
                FROM information_schema.tables t
                JOIN information_schema.columns c
                    ON t.table_name = c.table_name
                    AND t.table_schema = c.table_schema
                LEFT JOIN pg_catalog.pg_statio_all_tables st
                    ON t.table_name = st.relname
                LEFT JOIN pg_catalog.pg_description pgd
                    ON pgd.objoid = st.relid
                    AND pgd.objsubid = c.ordinal_position
                WHERE t.table_schema = 'public'
                  AND t.table_type = 'BASE TABLE'
                ORDER BY t.table_name, c.ordinal_position
                """
            )
        finally:
            await conn.close()

        tables: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            table_name = row["table_name"]
            if table_name not in tables:
                tables[table_name] = []
            tables[table_name].append(
                {
                    "column_name": row["column_name"],
                    "ordinal_position": row["ordinal_position"],
                    "data_type": row["data_type"],
                    "is_nullable": row["is_nullable"].upper() == "YES",
                    "column_default": row["column_default"],
                    "column_comment": row["column_comment"],
                    "is_primary_key": False,
                    "is_foreign_key": False,
                    "indexed": False,
                }
            )
        return tables

    async def _fetch_ck_schema(
        self, conn_info: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """从 ClickHouse system.columns 获取表结构"""
        import aiohttp

        query = (
            "SELECT database, table, name, position, type, default_expression "
            "FROM system.columns "
            f"WHERE database = '{conn_info['database']}' "
            "ORDER BY table, position"
        )

        encoded_query = urllib.parse.quote(query)
        url = (
            f"http://{conn_info['host']}:{conn_info['port']}/"
            f"?query={encoded_query}"
            f"&user={conn_info['user']}&password={conn_info['password']}"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(
                        f"ClickHouse Schema 查询失败: {text[:200]}"
                    )
                text = await resp.text()

        tables: Dict[str, List[Dict[str, Any]]] = {}
        for line in text.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            _db_name, table_name, col_name, pos, col_type = parts[:5]
            default_expr = parts[5] if len(parts) > 5 else None
            if table_name not in tables:
                tables[table_name] = []
            tables[table_name].append(
                {
                    "column_name": col_name,
                    "ordinal_position": int(pos),
                    "data_type": col_type,
                    "is_nullable": True,
                    "column_default": default_expr,
                    "column_comment": None,
                    "is_primary_key": False,
                    "is_foreign_key": False,
                    "indexed": False,
                }
            )
        return tables

    def _infer_description_from_name(
        self, column_name: str, data_type: str, table_name: str
    ) -> str:
        """
        根据字段名和类型推测语义描述

        基于常见命名规则生成描述，供 LLM 增强前的初始版本使用。

        Args:
            column_name: 字段名
            data_type: 数据类型
            table_name: 表名

        Returns:
            推测的语义描述
        """
        # 常见字段名映射
        name_mapping = {
            "id": "唯一标识符",
            "name": "名称",
            "created_at": "创建时间",
            "updated_at": "更新时间",
            "is_active": "是否启用",
            "is_deleted": "是否删除",
            "status": "状态",
            "type": "类型",
            "email": "电子邮箱",
            "phone": "电话号码",
            "mobile": "手机号码",
            "address": "地址",
            "description": "描述",
            "remark": "备注",
            "sort": "排序值",
            "order": "排序",
            "price": "价格",
            "amount": "金额",
            "count": "计数",
            "quantity": "数量",
            "user_id": "用户 ID",
            "dept_id": "部门 ID",
        }

        lower_name = column_name.lower()
        if lower_name in name_mapping:
            return name_mapping[lower_name]

        # 根据命名规则推断
        if lower_name.endswith("_id"):
            return f"{column_name[:-3].replace('_', ' ').title()} ID"
        if lower_name.endswith("_at") or lower_name.endswith("_time"):
            return f"{column_name[:-3].replace('_', ' ').title()} 时间" if lower_name.endswith("_at") else f"{column_name[:-5].replace('_', ' ').title()} 时间"
        if lower_name.endswith("_count"):
            return f"{column_name[:-6].replace('_', ' ').title()} 数量"
        if lower_name.startswith("is_"):
            return f"是否{column_name[3:].replace('_', ' ').title()}"

        # 兜底：根据类型返回
        type_hints = {
            "varchar": "字符串",
            "int": "整数",
            "bigint": "长整数",
            "decimal": "小数",
            "float": "浮点数",
            "double": "双精度浮点数",
            "date": "日期",
            "datetime": "日期时间",
            "timestamp": "时间戳",
            "text": "长文本",
            "boolean": "布尔值",
            "json": "JSON 数据",
        }
        base_type = data_type.split("(")[0].lower()
        type_desc = type_hints.get(base_type, data_type)
        return f"{column_name.replace('_', ' ').title()} ({type_desc})"
