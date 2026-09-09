"""initial migration

Revision ID: 0001
Revises:
Create Date: 2026-09-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### users ###
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键 ID"),
        sa.Column("username", sa.String(50), nullable=False, comment="用户名"),
        sa.Column("email", sa.String(100), nullable=False, comment="电子邮箱"),
        sa.Column("hashed_password", sa.String(255), nullable=False, comment="bcrypt 哈希密码"),
        sa.Column("role", sa.String(20), nullable=False, server_default="analyst", comment="用户角色：admin / analyst / viewer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1"), comment="是否激活"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # ### datasources ###
    op.create_table(
        "datasources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键 ID"),
        sa.Column("name", sa.String(100), nullable=False, comment="数据源别名"),
        sa.Column("type", sa.String(20), nullable=False, comment="数据库类型：mysql / postgresql / clickhouse"),
        sa.Column("host", sa.String(255), nullable=False, comment="数据库主机地址"),
        sa.Column("port", sa.Integer(), nullable=False, comment="数据库端口"),
        sa.Column("database_name", sa.String(100), nullable=False, comment="数据库名称"),
        sa.Column("username", sa.String(100), nullable=False, comment="数据库用户名"),
        sa.Column("password", sa.String(255), nullable=False, comment="加密存储的数据库密码"),
        sa.Column("extra_params", sa.Text(500), nullable=True, comment="连接额外参数，JSON 格式"),
        sa.Column("status", sa.String(20), nullable=False, server_default="disconnected", comment="连接状态：connected / disconnected / error"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1"), comment="是否启用"),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户 ID"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # ### schema_metas ###
    op.create_table(
        "schema_metas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键 ID"),
        sa.Column("datasource_id", sa.Integer(), sa.ForeignKey("datasources.id", ondelete="CASCADE"), nullable=False, comment="所属数据源 ID"),
        sa.Column("table_name", sa.String(100), nullable=False, comment="表名"),
        sa.Column("column_name", sa.String(100), nullable=False, comment="字段名"),
        sa.Column("ordinal_position", sa.Integer(), nullable=False, comment="字段顺序"),
        sa.Column("data_type", sa.String(50), nullable=False, comment="数据类型：varchar / int / decimal 等"),
        sa.Column("is_nullable", sa.Boolean(), nullable=False, server_default=sa.text("1"), comment="是否允许为空"),
        sa.Column("column_default", sa.String(200), nullable=True, comment="字段默认值"),
        sa.Column("column_comment", sa.String(500), nullable=True, comment="数据库字段注释"),
        sa.Column("description", sa.String(1000), nullable=True, comment="业务语义描述（AI 增强后填充）"),
        sa.Column("embedding", sa.Text(), nullable=True, comment="向量嵌入（JSON 数组文本）或 Qdrant 引用"),
        sa.Column("is_primary_key", sa.Boolean(), nullable=False, server_default=sa.text("0"), comment="是否为主键"),
        sa.Column("is_foreign_key", sa.Boolean(), nullable=False, server_default=sa.text("0"), comment="是否为外键"),
        sa.Column("indexed", sa.Boolean(), nullable=False, server_default=sa.text("0"), comment="是否有索引"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_schema_metas_datasource_id"), "schema_metas", ["datasource_id"])

    # ### conversations ###
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键 ID"),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户 ID"),
        sa.Column("title", sa.String(200), nullable=False, server_default="新对话", comment="会话标题"),
        sa.Column("workspace_type", sa.String(50), nullable=False, server_default="query", comment="工作区类型：query / attribution"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active", comment="状态：active / archived"),
        sa.Column("metadata_json", sa.Text(), nullable=True, comment="元数据 JSON"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversations_user_id"), "conversations", ["user_id"])

    # ### conversation_messages ###
    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键 ID"),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, comment="所属会话 ID"),
        sa.Column("role", sa.String(20), nullable=False, comment="角色：user / assistant / system"),
        sa.Column("content", mysql.LONGTEXT(), nullable=False, comment="消息内容"),
        sa.Column("message_type", sa.String(50), nullable=False, server_default="text", comment="消息类型：text / sql / result / chart"),
        sa.Column("metadata_json", sa.Text(), nullable=True, comment="元数据 JSON"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversation_messages_conversation_id"), "conversation_messages", ["conversation_id"])


def downgrade() -> None:
    op.drop_table("conversation_messages")
    op.drop_table("conversations")
    op.drop_table("schema_metas")
    op.drop_table("datasources")
    op.drop_table("users")