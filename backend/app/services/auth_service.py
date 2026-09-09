"""
认证服务层
封装用户注册、登录、令牌刷新、登出、当前用户获取等业务逻辑。
"""

from datetime import timedelta
from typing import Any, Dict, Tuple

from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthException, ValidationException
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.config import settings
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)


class AuthService:
    """
    认证服务

    处理用户注册、登录、令牌刷新、登出及身份校验等核心认证流程。
    令牌存储依赖 Redis，用户数据访问依赖 UserRepository。
    """

    def __init__(self, db: AsyncSession) -> None:
        self.repo = UserRepository(db)

    async def _get_redis(self) -> Redis:
        """获取 Redis 客户端实例"""
        return await get_redis().__anext__()

    async def register(self, req: RegisterRequest) -> User:
        """
        用户注册

        校验用户名和邮箱是否已存在，若不存在则创建新用户并返回。

        Args:
            req: 注册请求体（含 username, email, password）

        Returns:
            新创建的用户实例

        Raises:
            ValidationException: 用户名或邮箱已被占用
        """
        existing_user = await self.repo.get_by_username(req.username)
        if existing_user is not None:
            raise ValidationException(detail="用户名已被占用", code="USERNAME_EXISTS")

        existing_email = await self.repo.get_by_email(req.email)
        if existing_email is not None:
            raise ValidationException(detail="邮箱已被注册", code="EMAIL_EXISTS")

        user = await self.repo.create(
            {
                "username": req.username,
                "email": req.email,
                "hashed_password": hash_password(req.password),
            }
        )
        return user

    async def authenticate(self, req: LoginRequest) -> Tuple[TokenResponse, User]:
        """
        用户登录认证

        验证用户名和密码，成功后签发 access_token 和 refresh_token。

        Args:
            req: 登录请求体（含 username, password）

        Returns:
            (TokenResponse, User) — 令牌响应和用户对象

        Raises:
            AuthException: 用户名不存在或密码错误
        """
        user = await self.repo.get_by_username(req.username)
        if user is None:
            raise AuthException(detail="用户名或密码错误", code="INVALID_CREDENTIALS")

        if not verify_password(req.password, user.hashed_password):
            raise AuthException(detail="用户名或密码错误", code="INVALID_CREDENTIALS")

        if not user.is_active:
            raise AuthException(detail="账号已被禁用", code="ACCOUNT_DISABLED")

        payload: Dict[str, Any] = {"sub": str(user.id), "username": user.username, "role": user.role}
        access_token = create_access_token(data=payload)
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        # 将 refresh token 存入 Redis，过期时间与 JWT 一致
        redis = await self._get_redis()
        redis_key = f"refresh_{refresh_token}"
        await redis.setex(
            redis_key,
            timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            str(user.id),
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        ), user

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """
        刷新 access token

        校验 refresh token 的有效性及 Redis 中的存储状态，通过后签发新令牌。

        Args:
            refresh_token: 刷新令牌字符串

        Returns:
            新的令牌响应

        Raises:
            AuthException: 令牌无效、已过期或已被撤销
        """
        # 校验 JWT 本身
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise AuthException(detail="刷新令牌无效或已过期", code="INVALID_REFRESH_TOKEN")

        user_id = payload.get("sub")
        if user_id is None:
            raise AuthException(detail="刷新令牌载荷无效", code="INVALID_REFRESH_TOKEN")

        # 校验 Redis 中是否存在
        redis = await self._get_redis()
        redis_key = f"refresh_{refresh_token}"
        stored_user_id = await redis.get(redis_key)
        if stored_user_id is None:
            raise AuthException(detail="刷新令牌已失效", code="REFRESH_TOKEN_REVOKED")

        # 查询用户
        user = await self.repo.get(int(user_id))
        if user is None:
            raise AuthException(detail="用户不存在", code="USER_NOT_FOUND")

        if not user.is_active:
            raise AuthException(detail="账号已被禁用", code="ACCOUNT_DISABLED")

        # 签发新令牌
        payload: Dict[str, Any] = {"sub": str(user.id), "username": user.username, "role": user.role}
        new_access_token = create_access_token(data=payload)
        new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

        # 删除旧 refresh token，存入新 token
        await redis.delete(redis_key)
        new_redis_key = f"refresh_{new_refresh_token}"
        await redis.setex(
            new_redis_key,
            timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            str(user.id),
        )

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
        )

    async def logout(self, access_token: str) -> None:
        """
        用户登出

        从 Redis 中删除与当前用户关联的 refresh token。
        注意：实际生产环境还应维护 access_token 黑名单以支持立即失效。

        Args:
            access_token: 当前的 access token（用于识别用户）
        """
        try:
            payload = decode_token(access_token)
            user_id = payload.get("sub")
            if user_id is not None:
                redis = await self._get_redis()
                # 清除该用户的所有 refresh token
                # 注意：这里简化处理，实际可按用户 ID 维护 token 集合
                pattern = "refresh_*"
                cursor = 0
                while True:
                    cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
                    for key in keys:
                        stored_id = await redis.get(key)
                        if stored_id == user_id:
                            await redis.delete(key)
                    if cursor == 0:
                        break
        except JWTError:
            # token 可能已过期，忽略
            pass

    async def get_current_user(self, token: str) -> User:
        """
        根据 JWT token 获取当前用户

        Args:
            token: JWT access token 字符串

        Returns:
            当前用户实例

        Raises:
            AuthException: 令牌无效或用户不存在
        """
        try:
            payload = decode_token(token)
        except JWTError as e:
            raise AuthException(detail=f"令牌无效: {e}", code="INVALID_TOKEN")

        user_id = payload.get("sub")
        if user_id is None:
            raise AuthException(detail="令牌载荷无效", code="INVALID_TOKEN_PAYLOAD")

        user = await self.repo.get(int(user_id))
        if user is None:
            raise AuthException(detail="用户不存在", code="USER_NOT_FOUND")
        if not user.is_active:
            raise AuthException(detail="账号已被禁用", code="ACCOUNT_DISABLED")

        return user