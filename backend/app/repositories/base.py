"""
数据访问层基类
提供泛型 CRUD 抽象，各业务 Repository 继承此类实现具体数据操作。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class BaseRepository(ABC, Generic[ModelT]):
    """
    泛型 CRUD 基类

    所有业务 Repository 应继承此类，并传入对应的 SQLAlchemy 模型类型。
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @abstractmethod
    def _get_model(self) -> type[ModelT]:
        """子类需返回对应的 SQLAlchemy 模型类"""
        ...

    async def get(self, id: int) -> Optional[ModelT]:
        """
        根据主键 ID 获取单条记录

        Args:
            id: 主键 ID

        Returns:
            模型实例，未找到返回 None
        """
        model = self._get_model()
        stmt = select(model).where(model.id == id)  # type: ignore
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, skip: int = 0, limit: int = 20) -> List[ModelT]:
        """
        获取记录列表（分页）

        Args:
            skip: 跳过记录数
            limit: 返回最大条数

        Returns:
            模型实例列表
        """
        model = self._get_model()
        stmt = select(model).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, data: Dict[str, Any] | BaseModel) -> ModelT:
        """
        创建新记录

        Args:
            data: 创建数据，支持字典或 Pydantic BaseModel

        Returns:
            已创建的模型实例
        """
        if isinstance(data, BaseModel):
            data = data.model_dump()
        model = self._get_model()(**data)
        self.db.add(model)
        await self.db.commit()
        await self.db.refresh(model)
        return model

    async def update(self, id: int, data: Dict[str, Any] | BaseModel) -> Optional[ModelT]:
        """
        更新记录

        Args:
            id: 主键 ID
            data: 更新字段，支持字典或 Pydantic BaseModel

        Returns:
            更新后的模型实例，不存在返回 None
        """
        if isinstance(data, BaseModel):
            data = data.model_dump(exclude_unset=True)
        instance = await self.get(id)
        if instance is None:
            return None
        for key, value in data.items():
            setattr(instance, key, value)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def delete(self, id: int) -> bool:
        """
        删除记录

        Args:
            id: 主键 ID

        Returns:
            True 表示删除成功，False 表示记录不存在
        """
        instance = await self.get(id)
        if instance is None:
            return False
        await self.db.delete(instance)
        await self.db.commit()
        return True

    async def count(self) -> int:
        """
        统计总记录数

        Returns:
            记录总数
        """
        model = self._get_model()
        stmt = select(func.count()).select_from(model)
        result = await self.db.execute(stmt)
        return result.scalar_one()