"""
SQLAlchemy 声明式基类与通用 Mixin
提供所有模型的基础表结构和通用字段（id, created_at, updated_at）。
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

# re-export Base 方便所有业务模型统一从 app.models.base 导入
from app.core.database import Base as CoreBase

Base = CoreBase


class TimestampMixin:
    """
    时间戳 Mixin
    为模型添加 created_at 和 updated_at 自动管理字段。
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )


class BaseModel(Base, TimestampMixin):
    """
    全局声明式基类模型
    所有业务模型应继承此类，自动获得 id、created_at、updated_at。
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="主键 ID",
    )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"