"""索引构建与同步任务"""
from app.core.config import settings
from app.core.elasticsearch import create_es_client, get_es
from app.core.qdrant import get_qdrant


async def sync_schema_to_qdrant(datasource_id: int, fields: list[dict]) -> int:
    """将 Schema 字段同步到 Qdrant（批量嵌入）"""
    from app.agents.shared.embedding import EmbeddingService
    from app.search.vector_store import delete_schema_vectors, upsert_schema_vector

    client = get_qdrant()
    embed = EmbeddingService()

    await delete_schema_vectors(client, datasource_id)

    if not fields:
        return 0

    # 批量生成所有文本的向量
    texts = [
        f"{f.get('table_name', '')}.{f.get('column_name', '')} - {f.get('description', '')} - {f.get('column_comment', '')}"
        for f in fields
    ]
    vectors = await embed.embed(texts)

    # 逐一写入 Qdrant
    count = 0
    for field, vector in zip(fields, vectors):
        await upsert_schema_vector(client, field["id"], vector, field)
        count += 1

    return count


async def sync_schema_to_es(datasource_id: int, fields: list[dict]) -> int:
    """将 Schema 字段同步到 ES"""
    from app.search.keyword_search import delete_schema_docs, index_schema_doc

    es = await get_es().__anext__()
    await delete_schema_docs(es, datasource_id)

    count = 0
    for field in fields:
        await index_schema_doc(es, field["id"], {
            "datasource_id": datasource_id,
            "table_name": field.get("table_name", ""),
            "column_name": field.get("column_name", ""),
            "data_type": field.get("data_type", ""),
            "description": field.get("description", ""),
            "column_comment": field.get("column_comment", ""),
            "is_primary_key": field.get("is_primary_key", False),
        })
        count += 1

    return count