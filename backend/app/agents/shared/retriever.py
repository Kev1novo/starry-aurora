"""混合检索引擎——Qdrant 向量 + ES 关键词 + RRF 融合排序"""
from typing import Any, Optional

from app.core.config import settings
from app.core.elasticsearch import get_es
from app.core.qdrant import get_qdrant


async def hybrid_search(
    query: str,
    query_vector: list[float],
    datasource_id: int,
    top_k: int = 20,
    rrf_k: int = 60,
) -> list[dict[str, Any]]:
    """
    三路召回 + RRF 融合排序

    - 一路：Qdrant 向量检索（语义相似度）
    - 二路：ES BM25 关键词检索
    - 三路：LLM 生成假设文档的 HyDE 检索

    返回 RRF 融合后的 Schema 字段候选列表
    """
    from app.agents.shared.embedding import EmbeddingService
    from app.search.vector_store import search_qdrant
    from app.search.keyword_search import search_es

    qdrant = get_qdrant()
    es = await anext(get_es())

    # 一路：Qdrant 向量检索
    vector_results = await search_qdrant(qdrant, query_vector, datasource_id, top_k)

    # 二路：ES BM25 关键词检索
    keyword_results = await search_es(es, query, datasource_id, top_k)

    # 三路：HyDE——LLM 生成假设文档后再做向量检索
    hyde_results = await _hyde_search(query, datasource_id, top_k)

    # RRF 融合
    rank = _rrf_fusion(vector_results, keyword_results, hyde_results, k=rrf_k)
    return rank[:top_k]


async def _hyde_search(query: str, datasource_id: int, top_k: int) -> list[dict]:
    """HyDE：生成假设文档提升召回"""
    from app.agents.shared.embedding import EmbeddingService
    from app.agents.shared.llm_factory import LLMFactory

    llm = LLMFactory()
    prompt = f"""根据以下自然语言查询，生成一段假设的 SQL 查询描述文档。文档应包含可能涉及的表名、字段名和业务概念。

查询: {query}

假设文档:"""
    hyde_doc = await llm.generate([{"role": "user", "content": prompt}])
    if not hyde_doc:
        return []

    emb = EmbeddingService()
    hyde_vector = await emb.embed_one(hyde_doc)

    qdrant = get_qdrant()
    from app.search.vector_store import search_qdrant

    return await search_qdrant(qdrant, hyde_vector, datasource_id, top_k)


def _rrf_fusion(
    *rankings: list[dict],
    k: int = 60,
) -> list[dict]:
    """RRF (Reciprocal Rank Fusion) 融合多路召回结果"""
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}

    for docs in rankings:
        for rank, doc in enumerate(docs):
            doc_id = doc.get("id", str(hash(str(doc))))
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
            items[doc_id] = doc

    sorted_ids = sorted(scores, key=scores.get, reverse=True)
    return [items[i] for i in sorted_ids]