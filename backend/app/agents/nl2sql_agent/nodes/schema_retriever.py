"""
Schema 检索节点
执行混合检索 -> 重排序 -> 因子剪枝，获取与用户问题最相关的 Schema 字段。
"""

from __future__ import annotations

from typing import Any

from app.agents.nl2sql_agent.state import AgentState
from app.agents.shared.embedding import EmbeddingService
from app.agents.shared.llm_factory import LLMFactory
from app.agents.shared.reranker import rerank
from app.agents.shared.retriever import hybrid_search

# 最大剪枝后保留的字段数
_MAX_PRUNED_FIELDS = 30


async def schema_retriever_node(state: AgentState) -> dict[str, Any]:
    """Schema 检索节点

    三步流程：
        1. 混合检索（三路召回 + RRF）
        2. Cross-encoder 重排序
        3. LLM 因子剪枝（去除不相关字段）

    Args:
        state: 当前 AgentState

    Returns:
        更新到 state 的字段字典（retrieved_schemas, pruned_schemas）
    """
    question: str = state.get("question", "")
    datasource_id: int | None = state.get("datasource_id")

    if not datasource_id:
        return {
            "retrieved_schemas": [],
            "pruned_schemas": [],
            "error": "缺少 datasource_id",
        }

    # 1. 生成查询向量
    emb = EmbeddingService()
    query_vector = await emb.embed_one(question)
    if not query_vector:
        return {
            "retrieved_schemas": [],
            "pruned_schemas": [],
            "error": "查询向量生成失败",
        }

    # 2. 混合检索（三路召回 + RRF）
    retrieved = await hybrid_search(
        query=question,
        query_vector=query_vector,
        datasource_id=datasource_id,
        top_k=20,
        rrf_k=60,
    )

    if not retrieved:
        return {
            "retrieved_schemas": [],
            "pruned_schemas": [],
            "error": "未检索到相关 Schema",
        }

    # 3. Cross-encoder 重排序
    reranked = await rerank(query=question, candidates=retrieved, top_k=15)

    # 4. LLM 因子剪枝
    pruned = await _factor_prune(question, reranked)

    return {
        "retrieved_schemas": retrieved,
        "pruned_schemas": pruned,
    }


async def _factor_prune(
    question: str,
    candidates: list[dict[str, Any]],
    max_fields: int = _MAX_PRUNED_FIELDS,
) -> list[dict[str, Any]]:
    """LLM 因子剪枝：从重排序结果中剔除与问题无关的字段

    使用 LLM 判断每个候选字段是否与用户查询相关，
    只保留「相关」字段以减少 SQL 生成的上下文噪音。

    Args:
        question: 用户原始问题
        candidates: 重排序后的候选字段列表
        max_fields: 最大保留字段数

    Returns:
        剪枝后的相关字段列表
    """
    if not candidates:
        return []

    # 如果候选字段很少，直接返回不做剪枝
    if len(candidates) <= 10:
        return candidates

    fields_text = "\n".join(
        f"[{i}] {c.get('table_name', '?')}.{c.get('column_name', '?')} "
        f"({c.get('data_type', '?')}) - {c.get('description', c.get('column_comment', ''))}"
        for i, c in enumerate(candidates)
    )

    llm = LLMFactory(temperature=0.0)
    prompt = f"""用户查询: {question}

以下是候选 Schema 字段列表，请判断每个字段是否与查询相关。
只保留与查询意图直接相关的字段（表名或字段名或描述与查询中的业务概念匹配）。

字段列表:
{fields_text}

请输出逗号分隔的相关字段序号（例如: 0,3,5,10），只输出序号:"""

    resp = await llm.generate([{"role": "user", "content": prompt}])

    # 解析序号
    import re

    indices: list[int] = []
    for token in re.split(r"[,，\s]+", resp.strip()):
        token = token.strip()
        if token.isdigit():
            idx = int(token)
            if 0 <= idx < len(candidates):
                indices.append(idx)

    # 去重并保持顺序
    seen: set[int] = set()
    unique_indices: list[int] = []
    for idx in indices:
        if idx not in seen:
            seen.add(idx)
            unique_indices.append(idx)

    pruned = [candidates[i] for i in unique_indices]
    return pruned[:max_fields]