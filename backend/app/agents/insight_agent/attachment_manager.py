"""
附件管理模块（MVP 阶段只留接口，核心方法预留）
管理报表/文件导出附件的上传、存储与生命周期。
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.exceptions import NotFoundException
from app.models.base import BaseModel

# ---------- 枚举 ----------


class AttachmentType(str, Enum):
    """附件类型枚举"""

    REPORT = "report"
    EXPORT = "export"
    CHART = "chart"
    OTHER = "other"


class AttachmentStatus(str, Enum):
    """附件状态枚举"""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    EXPIRED = "expired"


# ---------- ORM 模型 ----------


class Attachment(BaseModel):
    """附件 ORM 模型"""

    __tablename__ = "attachments"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True, comment="所属用户 ID"
    )
    workspace_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("workspaces.id"), nullable=True, comment="关联工作区 ID"
    )
    query_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="关联查询 ID"
    )
    file_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="文件名"
    )
    file_size: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="文件大小（字节）"
    )
    file_type: Mapped[str] = mapped_column(
        String(64), default="", nullable=False, comment="文件 MIME 类型"
    )
    storage_path: Mapped[str] = mapped_column(
        String(512), default="", nullable=False, comment="存储路径"
    )
    attachment_type: Mapped[AttachmentType] = mapped_column(
        SAEnum(AttachmentType, name="attachment_type_enum", create_constraint=True),
        default=AttachmentType.OTHER,
        nullable=False,
        comment="附件类型",
    )
    status: Mapped[AttachmentStatus] = mapped_column(
        SAEnum(AttachmentStatus, name="attachment_status_enum", create_constraint=True),
        default=AttachmentStatus.PENDING,
        nullable=False,
        comment="附件状态",
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="过期时间（到期自动清理）"
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(
        Text, default=None, comment="扩展元数据（JSON 字符串）"
    )

    def __repr__(self) -> str:
        return f"<Attachment(id={self.id}, file_name={self.file_name!r}, status={self.status.value})>"


# ---------- Pydantic 模型 ----------


class AttachmentCreate(BaseModel):
    """创建附件的输入模型"""

    file_name: str = Field(..., max_length=255)
    file_size: int = Field(default=0, ge=0)
    file_type: str = Field(default="", max_length=64)
    attachment_type: AttachmentType = AttachmentType.OTHER
    workspace_id: Optional[int] = None
    query_id: Optional[str] = None
    expires_in_hours: Optional[int] = None


class AttachmentResponse(BaseModel):
    """附件响应模型"""

    id: int
    file_name: str
    file_size: int
    file_type: str
    attachment_type: AttachmentType
    status: AttachmentStatus
    storage_path: str
    created_at: datetime
    expires_at: Optional[datetime]


# ---------- 管理器 ----------


class AttachmentManager:
    """
    附件管理器

    职责：
        1. 附件的创建、查询、删除
        2. 附件状态跟踪（处理中 / 就绪 / 失败 / 过期）
        3. 生命周期管理与过期清理（预留）

    MVP 阶段：核心上传/下载方法预留，仅提供基础的元数据 CRUD。
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------- CRUD ----------

    async def create(self, user_id: int, data: AttachmentCreate) -> Attachment:
        """
        创建附件记录。

        Args:
            user_id: 用户 ID
            data: 附件创建参数

        Returns:
            已创建的 Attachment 实例
        """
        expires_at: Optional[datetime] = None
        if data.expires_in_hours is not None:
            expires_at = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            expires_at = expires_at.replace(hour=expires_at.hour + data.expires_in_hours)

        attachment = Attachment(
            user_id=user_id,
            workspace_id=data.workspace_id,
            query_id=data.query_id,
            file_name=data.file_name,
            file_size=data.file_size,
            file_type=data.file_type,
            attachment_type=data.attachment_type,
            status=AttachmentStatus.PENDING,
            expires_at=expires_at,
            storage_path="",
        )
        self.db.add(attachment)
        await self.db.commit()
        await self.db.refresh(attachment)
        return attachment

    async def get(self, attachment_id: int, user_id: int) -> Attachment:
        """
        获取附件详情。

        Raises:
            NotFoundException: 附件不存在
        """
        stmt = select(Attachment).where(
            Attachment.id == attachment_id, Attachment.user_id == user_id
        )
        result = await self.db.execute(stmt)
        attachment = result.scalar_one_or_none()
        if attachment is None:
            raise NotFoundException(detail=f"附件 {attachment_id} 不存在")
        return attachment

    async def list_by_user(
        self, user_id: int, attachment_type: Optional[AttachmentType] = None
    ) -> list[Attachment]:
        """获取用户的附件列表"""
        stmt = select(Attachment).where(Attachment.user_id == user_id)
        if attachment_type is not None:
            stmt = stmt.where(Attachment.attachment_type == attachment_type)
        stmt = stmt.order_by(Attachment.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_workspace(self, workspace_id: int) -> list[Attachment]:
        """获取工作区的附件列表"""
        stmt = (
            select(Attachment)
            .where(Attachment.workspace_id == workspace_id)
            .order_by(Attachment.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self, attachment_id: int, user_id: int, status: AttachmentStatus
    ) -> Attachment:
        """更新附件状态"""
        attachment = await self.get(attachment_id, user_id)
        attachment.status = status
        await self.db.commit()
        await self.db.refresh(attachment)
        return attachment

    async def delete(self, attachment_id: int, user_id: int) -> None:
        """删除附件记录（不删除物理文件）"""
        attachment = await self.get(attachment_id, user_id)
        await self.db.delete(attachment)
        await self.db.commit()

    # ---------- 预留方法（MVP 暂不实现） ----------

    async def upload_file(self, attachment_id: int, content: bytes) -> str:
        """
        上传附件文件到存储后端。

        MVP 阶段：预留接口，直接返回空路径。
        TODO: 实现文件上传逻辑（本地磁盘 / S3 / OSS）
        """
        # pylint: disable=unused-argument
        raise NotImplementedError("upload_file 在 MVP 阶段未实现")

    async def download_file(self, attachment_id: int) -> bytes:
        """
        从存储后端下载附件文件。

        MVP 阶段：预留接口，直接抛出异常。
        TODO: 实现文件下载逻辑
        """
        # pylint: disable=unused-argument
        raise NotImplementedError("download_file 在 MVP 阶段未实现")

    async def cleanup_expired(self) -> int:
        """
        清理过期附件（标记为 expired 或物理删除）。

        MVP 阶段：预留接口，返回 0。
        TODO: 实现过期清理逻辑
        """
        return 0

    # ---------- 工具方法 ----------

    @staticmethod
    async def to_response(attachment: Attachment) -> AttachmentResponse:
        """将 ORM 模型转换为响应模型"""
        return AttachmentResponse(
            id=attachment.id,
            file_name=attachment.file_name,
            file_size=attachment.file_size,
            file_type=attachment.file_type,
            attachment_type=attachment.attachment_type,
            status=attachment.status,
            storage_path=attachment.storage_path,
            created_at=attachment.created_at,
            expires_at=attachment.expires_at,
        )