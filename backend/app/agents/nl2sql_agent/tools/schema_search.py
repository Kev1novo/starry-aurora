"""Schema 搜索工具"""
from typing import Any

from app.agents.shared.embedding import EmbeddingService
from app.agents.shared.retriever import hybrid_search
from app.agents.shared.reranker import rerank
from app.nlp.factor_pruner import prune_factors


async def search_schema(
    question: str,
    datasource_id: int,
    top_k: int = 20,
) -> list[dict[str, Any]]:
    """混合检索 Schema"""
    embed = EmbeddingService()
    query_vector = await embed.embed_one(question)

    candidates = await hybrid_search(question, query_vector, datasource_id, top_k)
    ranked = await rerank(question, candidates, top_k=10)
    pruned = await prune_factors(question, ranked)

    return pruned


async def search_tables(question: str, datasource_id: int) -> list[str]:
    """搜索相关表名"""
    schemas = await search_schema(question, datasource_id, top_k=30)
    tables = set(s["table_name"] for s in schemas if "table_name" in s)
    return list(tables)[:5]


async def search_columns(question: str, datasource_id: int, table_name: str) -> list[dict]:
    """搜索特定表的字段"""
    from app.agents.shared.embedding import EmbeddingService

    embed = EmbeddingService()
    query_vector = await embed.embed_one(question)

    from app.search.vector_store import search_qdrant
    from app.core.qdrant import get_qdrant

    qdrant = get_qdrant()
    results = await search_qdrant(qdrant, query_vector, datasource_id, top_k=50)
    return [r for r in results if r.get("table_name") == table_name]