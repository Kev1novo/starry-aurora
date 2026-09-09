"""语义对齐器——基于 HyDE 的查询扩展与语义匹配"""

from typing import Any

from app.agents.shared.embedding import EmbeddingService
from app.agents.shared.llm_factory import LLMFactory


class SemanticAligner:
    """
    HyDE (Hypothetical Document Embedding) 查询扩展 + 语义对齐。
    将自然语言查询扩展为假设文档，再通过向量嵌入与候选字段进行语义匹配。
    """

    def __init__(
        self,
        llm_factory: LLMFactory | None = None,
        embedding_service: EmbeddingService | None = None,
    ):
        self.llm = llm_factory or LLMFactory()
        self.embedder = embedding_service or EmbeddingService()

    async def expand_query(self, query: str, domain: str = "database") -> list[str]:
        """
        通过 HyDE 生成多条假设文档，扩展原始查询。

        Args:
            query: 自然语言查询
            domain: 领域提示，如 "database"、"marketing"、"finance"

        Returns:
            [hypothetical_doc_1, hypothetical_doc_2, ...]
        """
        domain_prompts = {
            "database": (
                "你是一个数据库分析专家。请根据以下用户查询，生成一段假设的 SQL 查询描述文档。"
                "文档应详细描述可能涉及的表、字段、过滤条件和聚合逻辑。"
            ),
            "marketing": (
                "你是一个营销分析师。请根据以下用户查询，生成一段假设的市场分析场景描述。"
                "描述应包含涉及的渠道、用户群体、时间范围和指标定义。"
            ),
            "finance": (
                "你是一个财务分析师。请根据以下用户查询，生成一段假设的财务分析文档。"
                "描述应包含涉及的科目、期间、维度对比等细节。"
            ),
        }

        prompt_template = domain_prompts.get(domain, domain_prompts["database"])

        # 生成单条 HyDE 文档
        single_prompt = f"{prompt_template}\n\n用户查询: {query}\n\n假设文档:"
        single_doc = await self.llm.generate([{"role": "user", "content": single_prompt}])

        expansions = [query]
        if single_doc and single_doc.strip():
            expansions.append(single_doc.strip())

        return expansions

    async def align(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int = 10,
        domain: str = "database",
    ) -> list[dict[str, Any]]:
        """
        对查询进行语义扩展，然后与候选字段做向量相似度匹配。

        Args:
            query: 原始用户查询
            candidates: 候选字段列表，每项含 {id, name, description, table_name, ...}
            top_k: 返回最相关的 K 个字段
            domain: 领域提示

        Returns:
            按相关度排序的候选字段（附加 semantic_score 字段）
        """
        if not candidates:
            return []

        # 1. HyDE 扩展
        expansions = await self.expand_query(query, domain=domain)

        # 2. 生成扩展文档的向量
        expansion_vectors = await self.embedder.embed(expansions)

        # 3. 生成候选字段的向量
        candidate_texts = [
            f"{c.get('table_name', '')}.{c.get('column_name', '')} {c.get('description', '')}"
            for c in candidates
        ]
        candidate_vectors = await self.embedder.embed(candidate_texts)

        # 4. 计算余弦相似度，取扩展文档平均
        import math

        def cosine_sim(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(y * y for y in b))
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)

        scored = []
        for i, cand in enumerate(candidates):
            # 对每个候选字段，计算与所有扩展向量的平均余弦相似度
            sims = [
                cosine_sim(candidate_vectors[i], ev)
                for ev in expansion_vectors
            ]
            avg_sim = sum(sims) / len(sims) if sims else 0.0
            scored.append({**cand, "semantic_score": round(avg_sim, 4)})

        # 按语义得分排序
        scored.sort(key=lambda x: x["semantic_score"], reverse=True)
        return scored[:top_k]

    async def compute_similarity(
        self,
        text_a: str,
        text_b: str,
    ) -> float:
        """计算两段文本的语义相似度"""
        import math

        vectors = await self.embedder.embed([text_a, text_b])
        a, b = vectors[0], vectors[1]
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return round(dot / (norm_a * norm_b), 4)


# 全局默认实例
semantic_aligner = SemanticAligner()