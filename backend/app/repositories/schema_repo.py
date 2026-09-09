"""
Schema 元数据数据访问层
提供针对 SchemaMeta 模型的数据库查询操作，支持表级和字段级的批量管理。
"""

from typing import List, Optional

from sqlalchemy import delete, select

from app.models.schema_meta import SchemaMeta
from app.repositories.base import BaseRepository


class SchemaMetaRepository(BaseRepository[SchemaMeta]):
    """
    Schema 元数据 Repository

    继承 BaseRepository 的基础 CRUD，扩展按表查询、列表、批量创建和按数据源删除方法。
    """

    def _get_model(self) -> type[SchemaMeta]:
        return SchemaMeta

    async def get_by_table(
        self, datasource_id: int, table_name: str
    ) -> List[SchemaMeta]:
        """
        获取指定数据源中某个表的所有字段元数据

        Args:
            datasource_id: 数据源 ID
            table_name: 表名

        Returns:
            字段元数据列表，按 ordinal_position 排序
        """
        stmt = (
            select(SchemaMeta)
            .where(
                SchemaMeta.datasource_id == datasource_id,
                SchemaMeta.table_name == table_name,
            )
            .order_by(SchemaMeta.ordinal_position)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_tables(self, datasource_id: int) -> List[str]:
        """
        获取指定数据源中所有不同的表名列表

        Args:
            datasource_id: 数据源 ID

        Returns:
            表名列表
        """
        from sqlalchemy import distinct

        stmt = (
            select(distinct(SchemaMeta.table_name))
            .where(SchemaMeta.datasource_id == datasource_id)
            .order_by(SchemaMeta.table_name)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_table_columns(
        self, datasource_id: int, table_name: str
    ) -> List[SchemaMeta]:
        """
        获取指定数据源中某个表的所有字段（同 get_by_table，提供语义更清晰的别名）

        Args:
            datasource_id: 数据源 ID
            table_name: 表名

        Returns:
            字段元数据列表
        """
        return await self.get_by_table(datasource_id, table_name)

    async def delete_by_datasource(self, datasource_id: int) -> None:
        """
        删除指定数据源的所有 Schema 记录

        Args:
            datasource_id: 数据源 ID
        """
        stmt = delete(SchemaMeta).where(SchemaMeta.datasource_id == datasource_id)
        await self.db.execute(stmt)
        await self.db.commit()

    async def batch_create(self, fields: List[SchemaMeta]) -> None:
        """
        批量创建 Schema 元数据记录

        Args:
            fields: SchemaMeta 实例列表
        """
        for field in fields:
            self.db.add(field)
        await self.db.commit()