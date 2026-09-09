"""
数据源数据访问层
提供针对 DataSource 模型的数据库查询操作，继承 BaseRepository 泛型 CRUD。
"""

from typing import List, Optional

from sqlalchemy import select

from app.models.datasource import DataSource
from app.repositories.base import BaseRepository


class DataSourceRepository(BaseRepository[DataSource]):
    """
    数据源 Repository

    继承 BaseRepository 的基础 CRUD，扩展按名称查询和按用户分页查询方法。
    """

    def _get_model(self) -> type[DataSource]:
        return DataSource

    async def get_by_name(self, name: str) -> Optional[DataSource]:
        """
        根据名称查询数据源

        Args:
            name: 数据源别名

        Returns:
            匹配的数据源实例，未找到返回 None
        """
        stmt = select(DataSource).where(DataSource.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> List[DataSource]:
        """
        获取指定用户的数据源列表（分页）

        Args:
            user_id: 用户 ID
            skip: 跳过记录数
            limit: 返回最大条数

        Returns:
            数据源实例列表
        """
        stmt = (
            select(DataSource)
            .where(DataSource.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_user(self, user_id: int) -> int:
        """
        统计指定用户的数据源总数

        Args:
            user_id: 用户 ID

        Returns:
            数据源总数
        """
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(DataSource)
            .where(DataSource.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()