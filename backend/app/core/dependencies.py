"""
FastAPI 依赖注入汇总
整合数据库、Redis、认证等公共依赖。
"""

from collections.abc import AsyncGenerator
from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db as _get_db
from app.core.redis import get_redis as _get_redis
from app.core.security import decode_token

# ---------- 数据库 ----------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """数据库会话依赖"""
    async for session in _get_db():
        yield session


# ---------- Redis ----------

async def get_redis() -> AsyncGenerator[Redis, None]:
    """Redis 客户端依赖"""
    async for redis in _get_redis():
        yield redis


# ---------- JWT 认证 ----------

_security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_security_scheme),
) -> Dict[str, Any]:
    """
    从 JWT 解析当前用户
    提取 Authorization Bearer token，验证并返回用户信息。
    """
    token = credentials.credentials
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token 中缺少用户标识",
            )
        return {"user_id": user_id, **payload}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
        )