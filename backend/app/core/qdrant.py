"""
Qdrant 客户端管理
提供 QdrantClient 初始化、依赖注入以及集合创建工具。
"""

from collections.abc import AsyncGenerator
from typing import Optional

from grpc import RpcError
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import settings

_qdrant_client: Optional[QdrantClient] = None


def create_qdrant_client() -> QdrantClient:
    """
    创建 Qdrant 客户端
    根据配置使用 gRPC 或 HTTP 模式连接。
    """
    global _qdrant_client
    _qdrant_client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        api_key=settings.QDRANT_API_KEY or None,
        prefer_grpc=True,
    )
    return _qdrant_client


def get_qdrant() -> QdrantClient:
    """
    FastAPI 依赖注人：获取 Qdrant 客户端（同步单例）
    """
    if _qdrant_client is None:
        create_qdrant_client()
    return _qdrant_client  # type: ignore


def ensure_collection(collection_name: str, vector_size: int) -> bool:
    """
    确保 Qdrant 集合存在，不存在时自动创建
    Args:
        collection_name: 集合名称
        vector_size: 向量维度
    Returns:
        集合是否已就绪
    """
    client = get_qdrant()
    try:
        collections = client.get_collections().collections
        existing = {c.name for c in collections}
        if collection_name not in existing:
            client.recreate_collection(
                collection_name=collection_name,
                vectors_config={"size": vector_size, "distance": "Cosine"},
            )
        return True
    except (UnexpectedResponse, RpcError) as e:
        raise RuntimeError(f"Qdrant 集合操作失败: {e}") from e