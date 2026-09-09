"""因子剪枝——基于相关度过滤不相关的数据库字段"""

import re
from typing import Any

from app.nlp.tokenizer import JiebaTokenizer


class FactorPruner:
    """
    因子剪枝器。
    根据自然语言查询，从候选字段列表中剔除与查询无关的字段，
    降低下游 NL2SQL 的搜索空间和 LLM 输入长度。
    """

    def __init__(self, tokenizer: JiebaTokenizer | None = None):
        self.tokenizer = tokenizer or JiebaTokenizer()
        # 停用词——过滤无信息量的词
        self.stop_words: set[str] = {
            "的",
            "了",
            "是",
            "在",
            "与",
            "和",
            "或",
            "对",
            "有",
            "以",
            "之",
            "为",
            "这",
            "那",
            "哪",
            "什么",
            "如何",
            "怎么",
            "多少",
            "一个",
            "一些",
            "其中",
            "分别",
            "每",
            "各",
            "所有",
            "全部",
            "请",
            "帮",
            "查",
            "找",
            "看",
            "展示",
            "显示",
            "列出",
            "统计",
        }

    async def prune(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        relevance_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        根据查询相关度过滤候选字段。

        Args:
            query: 自然语言查询
            candidates: 候选字段列表，每项含
                {id, table_name, column_name, description, column_type, ...}
            relevance_threshold: 相关度分数阈值（0~1），低于此值的字段被剔除。
                0 表示仅移除完全无关字段。

        Returns:
            过滤后的候选字段列表（附加 relevance_score 字段）
        """
        if not candidates:
            return []

        # 1. 提取查询关键词
        query_keywords = self._extract_keywords(query)

        # 2. 为每个候选字段计算相关度
        scored = []
        for cand in candidates:
            score = self._compute_field_relevance(query, query_keywords, cand)
            if score >= relevance_threshold:
                scored.append({**cand, "relevance_score": round(score, 4)})

        # 3. 按相关度降序排列
        scored.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored

    def _extract_keywords(self, text: str) -> set[str]:
        """从文本中提取有效关键词"""
        tokens = self.tokenizer.tokenize(text)
        raw_words = {t["word"].strip().lower() for t in tokens if t["word"].strip()}

        # 过滤停用词
        keywords = set()
        for w in raw_words:
            if w in self.stop_words:
                continue
            if re.match(r'^[^\w]+$', w):  # 纯标点
                continue
            keywords.add(w)

        return keywords

    def _compute_field_relevance(
        self,
        query: str,
        query_keywords: set[str],
        candidate: dict[str, Any],
    ) -> float:
        """
        计算单个字段与查询的相关度。

        综合以下几个维度：
        - 关键词命中率（column_name、table_name、description）
        - 词义精确匹配 vs 部分匹配
        - 字段值域匹配（枚举值匹配）

        Returns:
            0~1 之间的相关度分数
        """
        # 构建字段的文本表示
        field_texts = [
            candidate.get("column_name", "").lower(),
            candidate.get("table_name", "").lower(),
            candidate.get("description", "").lower(),
        ]

        query_lower = query.lower()
        scores = []

        for text in field_texts:
            if not text:
                continue
            field_keywords = self._extract_keywords(text)

            if not field_keywords:
                continue

            # 精确关键词匹配率
            intersection = query_keywords & field_keywords
            if intersection:
                exact_match_ratio = len(intersection) / len(field_keywords)
                scores.append(exact_match_ratio)

            # 子串匹配：查询词是否出现在字段名中，或反之
            for kw in query_keywords:
                if len(kw) < 2:
                    continue
                if kw in text:
                    scores.append(0.5)
                elif text in kw:
                    scores.append(0.3)

        # 字段值域匹配：如果候选字段有枚举值定义，检查查询是否提及
        enum_values = candidate.get("enum_values", [])
        if enum_values:
            for ev in enum_values:
                if str(ev).lower() in query_lower:
                    scores.append(0.6)
                    break

        # 综合得分（上限 1.0）
        if not scores:
            return 0.0
        return min(sum(scores) / max(len(set(field_texts) - {""}), 1), 1.0)


# 全局默认实例
factor_pruner = FactorPruner()