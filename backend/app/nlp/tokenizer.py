"""Jieba 分词封装——提供 tokenize() 和 extract_keywords()"""

from typing import Any

import jieba
import jieba.analyse


class JiebaTokenizer:
    """中文分词与关键词提取封装"""

    def __init__(self, user_dict_path: str | None = None):
        """
        Args:
            user_dict_path: 自定义词典路径，用于领域专有词（表名、字段名等）
        """
        if user_dict_path:
            jieba.load_userdict(user_dict_path)

    def tokenize(
        self,
        text: str,
        cut_all: bool = False,
        use_paddle: bool = False,
        keep_whitespace: bool = False,
    ) -> list[dict[str, Any]]:
        """
        对文本进行分词，返回带词性和位置的 token 列表。

        Args:
            text: 输入文本
            cut_all: 是否使用全模式（默认精确模式）
            use_paddle: 是否使用 Paddle 模型分词（需安装 paddlepaddle-tiny）
            keep_whitespace: 是否保留空白符

        Returns:
            [{"word": str, "flag": str, "start": int, "end": int}, ...]
        """
        if not text or not text.strip():
            return []

        tokens = jieba.tokenize(text, mode="search" if cut_all else "default")
        results = []
        for start, end, word in tokens:
            if not keep_whitespace and word.strip() == "":
                continue
            results.append(
                {
                    "word": word,
                    "flag": jieba.posseg.POSTokenizer(jieba.dt).guess(word) if use_paddle else "",
                    "start": start,
                    "end": end,
                }
            )
        return results

    def extract_keywords(
        self,
        text: str,
        top_k: int = 10,
        method: str = "tfidf",
        with_weight: bool = True,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """
        提取文本关键词。

        Args:
            text: 输入文本
            top_k: 返回前 K 个关键词
            method: "tfidf" 或 "textrank"
            with_weight: 是否返回权重值

        Returns:
            [{"word": str, "weight": float}, ...]
        """
        if not text or not text.strip():
            return []

        if method == "textrank":
            words_with_weight = jieba.analyse.textrank(text, topK=top_k, withWeight=with_weight)
        else:
            words_with_weight = jieba.analyse.extract_tags(
                text, topK=top_k, withWeight=with_weight, **kwargs
            )

        if with_weight:
            return [{"word": w, "weight": round(weight, 4)} for w, weight in words_with_weight]
        return [{"word": w, "weight": 1.0} for w in words_with_weight]

    def add_word(self, word: str, freq: int = 0, tag: str = "") -> None:
        """向词典动态添加词"""
        jieba.add_word(word, freq=freq, tag=tag)

    def suggest_freq(self, segment: tuple[str, ...]) -> int:
        """查询或建议词的频率"""
        return jieba.suggest_freq(segment)


# 全局默认实例
tokenizer = JiebaTokenizer()