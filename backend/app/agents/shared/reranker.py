"""Cross-encoder 重排序——二次过滤"""
from typing import Any


async def rerank(query: str, candidates: list[dict], top_k: int = 10) -> list[dict]:
    """
    对混合检索结果进行二次精排
    MVP 阶段使用 LLM 评分排序，后续可接入 cross-encoder 专用模型
    """
    if not candidates:
        return []

    from app.agents.shared.llm_factory import LLMFactory

    llm = LLMFactory(temperature=0.0)

    fields_text = "\n".join(
        f"[{i}] {c.get('table_name', '')}.{c.get('column_name', '')} - {c.get('description', '')}"
        for i, c in enumerate(candidates)
    )

    prompt = f"""查询: {query}

候选字段:
{fields_text}

请选择与查询最相关的 {top_k} 个字段，按相关度从高到低输出序号，逗号分隔。
只输出序号:"""

    resp = await llm.generate([{"role": "user", "content": prompt}])

    try:
        indices = [int(i.strip()) for i in resp.split(",") if i.strip().isdigit()]
        return [candidates[i] for i in indices if i < len(candidates)]
    except ValueError:
        return candidates[:top_k]