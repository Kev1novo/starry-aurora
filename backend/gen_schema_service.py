#!/usr/bin/env python
"""Generate schema_service.py with correct encoding."""

import os

GEN = r'''"""
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
'''

path = "D:/Vibe_Coding/starry-aurora/backend/app/services/schema_service.py"
with open(path, "w", encoding="utf-8") as f:
    f.write(GEN[1:])
print(f"Written {len(GEN)-1} bytes")