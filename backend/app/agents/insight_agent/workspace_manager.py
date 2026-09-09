"""
工作区管理模块
提供用户工作区的 CRUD 操作及活跃工作区状态管理。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.exceptions import NotFoundException, PermissionException
from app.models.base import BaseModel

# ---------- ORM 模型 ----------


class Workspace(BaseModel):
    """用户工作区 ORM 模型"""

    __tablename__ = "workspaces"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True, comment="所属用户 ID"
    )
    name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="工作区名称"
    )
    description: Mapped[str] = mapped_column(
        Text, default="", nullable=False, comment="工作区描述"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否为当前活跃工作区"
    )
    data_source_ids: Mapped[Optional[str]] = mapped_column(
        Text, default=None, comment="关联数据源 ID 列表（JSON 数组字符串）"
    )
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True, comment="最后访问时间"
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(
        Text, default=None, comment="扩展元数据（JSON 字符串）"
    )

    # ---------- relationships ----------
    # user = relationship("User", back_populates="workspaces")

    def __repr__(self) -> str:
        return f"<Workspace(id={self.id}, name={self.name!r}, user_id={self.user_id})>"


# ---------- Pydantic 模型 ----------


class WorkspaceCreate(PydanticBaseModel):
    """创建工作区的输入模型"""

    name: str
    description: str = ""
    data_source_ids: Optional[list[int]] = None


class WorkspaceUpdate(PydanticBaseModel):
    """更新工作区的输入模型"""

    name: Optional[str] = None
    description: Optional[str] = None
    data_source_ids: Optional[list[int]] = None


class WorkspaceResponse(PydanticBaseModel):
    """工作区响应模型"""

    id: int
    name: str
    description: str
    is_active: bool
    data_source_ids: Optional[list[int]]
    created_at: datetime
    updated_at: datetime
    last_accessed_at: Optional[datetime]


# ---------- 管理器 ----------


class WorkspaceManager:
    """
    工作区管理器

    职责：
        1. 用户工作区的 CRUD 操作
        2. 活跃工作区的切换与状态维护
        3. 工作区关联数据源的管理
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------- CRUD ----------

    async def create(self, user_id: int, data: WorkspaceCreate) -> Workspace:
        """
        为用户创建新工作区。
        若用户尚无活跃工作区，则自动将其设为活跃。
        """
        # 检查同名工作区
        existing = await self._find_by_name(user_id, data.name)
        if existing is not None:
            raise ValueError(f"工作区名称 '{data.name}' 已存在")

        has_active = await self._has_active(user_id)
        workspace = Workspace(
            user_id=user_id,
            name=data.name,
            description=data.description or "",
            is_active=not has_active,
            data_source_ids=self._serialize_ids(data.data_source_ids),
            last_accessed_at=datetime.now(timezone.utc),
        )
        self.db.add(workspace)
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace

    async def get(self, workspace_id: int, user_id: int) -> Workspace:
        """
        按 ID 获取工作区。
        校验所属用户，防止越权访问。

        Raises:
            NotFoundException: 工作区不存在
            PermissionException: 不属于当前用户
        """
        workspace = await self.db.get(Workspace, workspace_id)
        if workspace is None:
            raise NotFoundException(detail=f"工作区 {workspace_id} 不存在")
        if workspace.user_id != user_id:
            raise PermissionException(detail="无权访问其他用户的工作区")
        return workspace

    async def list_by_user(self, user_id: int) -> list[Workspace]:
        """获取用户的所有工作区（按更新时间倒序）"""
        stmt = (
            select(Workspace)
            .where(Workspace.user_id == user_id)
            .order_by(Workspace.updated_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, workspace_id: int, user_id: int, data: WorkspaceUpdate) -> Workspace:
        """
        更新工作区信息。

        Raises:
            NotFoundException: 工作区不存在
            ValueError: 名称冲突
        """
        workspace = await self.get(workspace_id, user_id)

        if data.name is not None and data.name != workspace.name:
            existing = await self._find_by_name(user_id, data.name)
            if existing is not None and existing.id != workspace_id:
                raise ValueError(f"工作区名称 '{data.name}' 已存在")
            workspace.name = data.name

        if data.description is not None:
            workspace.description = data.description

        if data.data_source_ids is not None:
            workspace.data_source_ids = self._serialize_ids(data.data_source_ids)

        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace

    async def delete(self, workspace_id: int, user_id: int) -> None:
        """
        删除工作区。
        若删除的是活跃工作区，则自动指定另一个工作区为活跃。

        Raises:
            NotFoundException: 工作区不存在
        """
        workspace = await self.get(workspace_id, user_id)
        was_active = workspace.is_active

        await self.db.delete(workspace)
        await self.db.commit()

        # 若删除了活跃工作区，将最新的另一个设为活跃
        if was_active:
            remaining = await self.list_by_user(user_id)
            if remaining:
                await self._set_active(remaining[0].id, user_id)

    # ---------- 活跃工作区管理 ----------

    async def get_active(self, user_id: int) -> Optional[Workspace]:
        """获取用户的活跃工作区"""
        stmt = select(Workspace).where(
            Workspace.user_id == user_id, Workspace.is_active.is_(True)
        )
        result = await self.db.execute(stmt)
        workspace = result.scalar_one_or_none()
        if workspace is not None:
            workspace.last_accessed_at = datetime.now(timezone.utc)
            workspace.is_active = True
            await self.db.commit()
        return workspace

    async def set_active(self, workspace_id: int, user_id: int) -> Workspace:
        """
        切换用户的活跃工作区。

        Raises:
            NotFoundException: 工作区不存在
        """
        workspace = await self.get(workspace_id, user_id)
        await self._set_active(workspace_id, user_id)
        workspace.last_accessed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace

    # ---------- 关联数据源 ----------

    async def get_data_source_ids(self, workspace_id: int, user_id: int) -> list[int]:
        """获取工作区关联的数据源 ID 列表"""
        workspace = await self.get(workspace_id, user_id)
        return self._deserialize_ids(workspace.data_source_ids) or []

    async def add_data_source(self, workspace_id: int, user_id: int, datasource_id: int) -> Workspace:
        """向工作区添加数据源"""
        workspace = await self.get(workspace_id, user_id)
        ids = self._deserialize_ids(workspace.data_source_ids) or []
        if datasource_id not in ids:
            ids.append(datasource_id)
            workspace.data_source_ids = self._serialize_ids(ids)
            await self.db.commit()
            await self.db.refresh(workspace)
        return workspace

    async def remove_data_source(
        self, workspace_id: int, user_id: int, datasource_id: int
    ) -> Workspace:
        """从工作区移除数据源"""
        workspace = await self.get(workspace_id, user_id)
        ids = self._deserialize_ids(workspace.data_source_ids) or []
        if datasource_id in ids:
            ids.remove(datasource_id)
            workspace.data_source_ids = self._serialize_ids(ids)
            await self.db.commit()
            await self.db.refresh(workspace)
        return workspace

    # ---------- 工具方法 ----------

    async def to_response(self, workspace: Workspace) -> WorkspaceResponse:
        """将 ORM 模型转换为响应模型"""
        return WorkspaceResponse(
            id=workspace.id,
            name=workspace.name,
            description=workspace.description,
            is_active=workspace.is_active,
            data_source_ids=self._deserialize_ids(workspace.data_source_ids),
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            last_accessed_at=workspace.last_accessed_at,
        )

    # ---------- 私有方法 ----------

    async def _set_active(self, workspace_id: int, user_id: int) -> None:
        """将指定工作区设为活跃，同时取消同用户其他工作区的活跃状态"""
        stmt = (
            select(Workspace)
            .where(Workspace.user_id == user_id, Workspace.is_active.is_(True))
        )
        result = await self.db.execute(stmt)
        for w in result.scalars().all():
            w.is_active = False
        # 这里 workspace_id 的赋值在调用处完成
        _stmt = select(Workspace).where(Workspace.id == workspace_id)
        result = await self.db.execute(_stmt)
        target = result.scalar_one_or_none()
        if target is not None:
            target.is_active = True

    async def _find_by_name(self, user_id: int, name: str) -> Optional[Workspace]:
        stmt = select(Workspace).where(
            Workspace.user_id == user_id, Workspace.name == name
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _has_active(self, user_id: int) -> bool:
        stmt = select(func.count()).select_from(Workspace).where(
            Workspace.user_id == user_id, Workspace.is_active.is_(True)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one() > 0

    @staticmethod
    def _serialize_ids(ids: Optional[list[int]]) -> Optional[str]:
        if ids is None:
            return None
        import json
        return json.dumps(ids)

    @staticmethod
    def _deserialize_ids(raw: Optional[str]) -> Optional[list[int]]:
        if raw is None:
            return None
        import json
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None