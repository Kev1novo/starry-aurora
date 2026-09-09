"""
Schema 元数据模型
记录从数据源同步的数据库表结构信息，支持字段级语义描述与向量嵌入。
"""

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class SchemaMeta(BaseModel):
    """
    Schema 元数据模型

    记录每个数据源中各表的字段结构信息，包括字段名、类型、约束等。
    通过 AI 增强后可填充业务语义描述（description）和向量嵌入（embedding），
    用于 NL2SQL 的 Schema 上下文召回。

    字段说明：
        id: 主键，自增整数
        datasource_id: 所属数据源 ID，关联 datasources 表
        table_name: 表名
        column_name: 字段名
        ordinal_position: 字段顺序（从 1 开始）
        data_type: 数据类型（varchar / int / decimal 等）
        is_nullable: 是否允许为空，默认为 True
        column_default: 字段默认值
        column_comment: 数据库中的字段注释
        description: 业务语义描述，AI 增强后填充
        embedding: 向量嵌入（JSON 数组文本），或仅存 Qdrant 引用 ID 后留空
        is_primary_key: 是否为主键，默认为 False
        is_foreign_key: 是否为外键，默认为 False
        indexed: 是否有索引，默认为 False
        created_at: 创建时间（继承自 TimestampMixin）
        updated_at: 更新时间（继承自 TimestampMixin）
    """

    __tablename__ = "schema_metas"

    datasource_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("datasources.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="所属数据源 ID",
    )
    table_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="表名",
    )
    column_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="字段名",
    )
    ordinal_position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="字段顺序",
    )
    data_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="数据类型：varchar / int / decimal 等",
    )
    is_nullable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否允许为空",
    )
    column_default: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="字段默认值",
    )
    column_comment: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="数据库字段注释",
    )
    description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="业务语义描述（AI 增强后填充）",
    )
    embedding: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="向量嵌入（JSON 数组文本）或 Qdrant 引用",
    )
    is_primary_key: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否为主键",
    )
    is_foreign_key: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否为外键",
    )
    indexed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否有索引",
    )

    def __repr__(self) -> str:
        return (
            f"<SchemaMeta(id={self.id}, table={self.table_name!r}, "
            f"column={self.column_name!r}, type={self.data_type!r})>"
        )