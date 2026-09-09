"""
Elasticsearch 异步客户端管理
提供 AsyncElasticsearch 初始化及 FastAPI 依赖注入。
"""

from collections.abc import AsyncGenerator
from typing import Optional

from elasticsearch import AsyncElasticsearch

from app.core.config import settings

_es_client: Optional[AsyncElasticsearch] = None


async def create_es_client() -> AsyncElasticsearch:
    """
    创建 ES 异步客户端
    """
    global _es_client
    _es_client = AsyncElasticsearch(
        hosts=[settings.ELASTICSEARCH_URL],
    )
    return _es_client


async def close_es_client() -> None:
    """关闭 ES 客户端"""
    global _es_client
    if _es_client is not None:
        await _es_client.close()
        _es_client = None


async def get_es() -> AsyncGenerator[AsyncElasticsearch, None]:
    """
    FastAPI 依赖注入：获取 ES 客户端
    """
    if _es_client is None:
        await create_es_client()
    try:
        yield _es_client  # type: ignore
    finally:
        pass