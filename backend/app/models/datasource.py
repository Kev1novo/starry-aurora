"""
数据源模型
定义连接外部数据库（MySQL / PostgreSQL / ClickHouse）的配置信息。
"""

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class DataSource(BaseModel):
    """
    数据源模型

    记录用户配置的外部数据库连接信息，支持 MySQL、PostgreSQL、ClickHouse。
    密码字段以加密形式存储，业务层在连接时解密使用。

    字段说明：
        id: 主键，自增整数
        name: 数据源别名，唯一
        type: 数据库类型，可选 mysql / postgresql / clickhouse
        host: 数据库主机地址
        port: 数据库端口
        database_name: 数据库名称
        username: 数据库用户名
        password: 加密存储的数据库密码
        extra_params: 连接字符串额外参数，JSON 格式
        status: 连接状态，可选 connected / disconnected / error
        is_active: 是否启用，默认为 True
        user_id: 所属用户 ID，关联 users 表
        created_at: 创建时间（继承自 TimestampMixin）
        updated_at: 更新时间（继承自 TimestampMixin）
    """

    __tablename__ = "datasources"

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="数据源别名",
    )
    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="数据库类型：mysql / postgresql / clickhouse",
    )
    host: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="数据库主机地址",
    )
    port: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="数据库端口",
    )
    database_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="数据库名称",
    )
    username: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="数据库用户名",
    )
    password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="加密存储的数据库密码",
    )
    extra_params: Mapped[str | None] = mapped_column(
        Text(500),
        nullable=True,
        comment="连接额外参数，JSON 格式",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="disconnected",
        nullable=False,
        comment="连接状态：connected / disconnected / error",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否启用",
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属用户 ID",
    )

    # ---------- 关系 ----------
    user = relationship("User", backref="datasources")

    def __repr__(self) -> str:
        return (
            f"<DataSource(id={self.id}, name={self.name!r}, "
            f"type={self.type!r}, host={self.host!r}, status={self.status!r})>"
        )