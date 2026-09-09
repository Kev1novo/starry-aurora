"""
用户数据访问层
提供针对 User 模型的数据库查询操作。
"""

from typing import Optional

from sqlalchemy import select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    用户 Repository

    继承 BaseRepository 的泛型 CRUD，并扩展用户名 / 邮箱维度的查询方法。
    """

    def _get_model(self) -> type[User]:
        return User

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        根据用户名查询用户

        Args:
            username: 用户名

        Returns:
            匹配的用户实例，未找到返回 None
        """
        stmt = select(User).where(User.username == username)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        根据邮箱查询用户

        Args:
            email: 电子邮箱

        Returns:
            匹配的用户实例，未找到返回 None
        """
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()