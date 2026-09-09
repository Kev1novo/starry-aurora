"""RRF 融合排序"""
from typing import Any

from app.search.keyword_search import search_es
from app.search.vector_store import search_qdrant


async def hybrid_search(
    query: str,
    query_vector: list[float],
    datasource_id: int,
    top_k: int = 20,
    rrf_k: int = 60,
) -> list[dict[str, Any]]:
    """
    混合检索——Qdrant 向量 + ES BM25 + RRF 融合

    调用 app.agents.shared.retriever.hybrid_search 进行三路召回和 RRF 融合
    """
    from app.agents.shared.retriever import hybrid_search as _hs

    return await _hs(query, query_vector, datasource_id, top_k, rrf_k)