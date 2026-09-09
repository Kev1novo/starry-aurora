"""
Redis 异步客户端管理
提供 Redis 连接池初始化、FastAPI 依赖注入、应用生命周期事件处理。
"""

from collections.abc import AsyncGenerator
from typing import Optional

from redis.asyncio import Redis

from app.core.config import settings

_redis_pool: Optional[Redis] = None


async def create_redis_pool() -> Redis:
    """
    创建 Redis 异步连接池
    使用 from_url 统一管理连接生命周期。
    """
    global _redis_pool
    _redis_pool = Redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    return _redis_pool


async def close_redis_pool() -> None:
    """关闭 Redis 连接池"""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None


async def get_redis() -> AsyncGenerator[Redis, None]:
    """
    FastAPI 依赖注入：获取 Redis 客户端
    返回应用级单例 Redis 连接。
    """
    if _redis_pool is None:
        await create_redis_pool()
    try:
        yield _redis_pool  # type: ignore
    finally:
        pass  # 连接池由应用生命周期管理，不在请求级别关闭