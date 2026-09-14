"""Qdrant 向量检索封装"""
from typing import Any

from qdrant_client import QdrantClient

SCHEMA_COLLECTION = "schema_fields"


def ensure_schema_collection(client: QdrantClient, vector_size: int = 768) -> None:
    """确保 Schema 集合存在"""
    from app.core.qdrant import ensure_collection
    ensure_collection(SCHEMA_COLLECTION, vector_size)


async def search_qdrant(
    client: QdrantClient,
    query_vector: list[float],
    datasource_id: int,
    top_k: int = 20,
) -> list[dict[str, Any]]:
    """Qdrant 向量检索"""
    import asyncio
    from qdrant_client.http import models

    def _search():
        results = client.query_points(
            collection_name=SCHEMA_COLLECTION,
            query=query_vector,
            query_filter=models.Filter(
                must=[models.FieldCondition(key="datasource_id", match=models.MatchValue(value=datasource_id))]
            ) if datasource_id else None,
            limit=top_k,
            with_payload=True,
        )
        return results.points

    results = await asyncio.to_thread(_search)

    return [
        {
            "id": str(hit.id),
            "score": hit.score,
            **hit.payload,
        }
        for hit in results
    ]


async def upsert_schema_vector(
    client: QdrantClient,
    field_id: int,
    vector: list[float],
    payload: dict,
) -> None:
    """写入 Schema 向量"""
    import asyncio
    from qdrant_client.http import models

    def _upsert():
        client.upsert(
            collection_name=SCHEMA_COLLECTION,
            points=[models.PointStruct(
                id=field_id,
                vector=vector,
                payload=payload,
            )],
        )

    await asyncio.to_thread(_upsert)


async def delete_schema_vectors(client: QdrantClient, datasource_id: int) -> None:
    """删除数据源所有 Schema 向量"""
    import asyncio
    from qdrant_client.http import models

    def _delete():
        client.delete(
            collection_name=SCHEMA_COLLECTION,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key="datasource_id", match=models.MatchValue(value=datasource_id))]
                )
            ),
        )

    await asyncio.to_thread(_delete)