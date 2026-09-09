"""
用户模型
定义系统用户的基础属性，用于认证与权限管理。
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class User(BaseModel):
    """
    系统用户模型

    字段说明：
        id: 主键，自增整数
        username: 用户名，唯一且带索引，最长 50 字符
        email: 电子邮箱，唯一且带索引，最长 100 字符
        hashed_password: bcrypt 哈希后的密码，最长 255 字符
        role: 用户角色，可选值为 admin / analyst / viewer，默认为 analyst
        is_active: 用户是否激活，默认为 True
        created_at: 创建时间（继承自 TimestampMixin）
        updated_at: 更新时间（继承自 TimestampMixin）
    """

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="用户名",
    )
    email: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="电子邮箱",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="bcrypt 哈希密码",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default="analyst",
        nullable=False,
        comment="用户角色：admin / analyst / viewer",
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="是否激活",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username!r}, role={self.role!r})>"