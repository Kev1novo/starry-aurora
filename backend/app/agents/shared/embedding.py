"""向量嵌入服务——支持本地 sentence-transformers 与 API 双模式"""
import asyncio
import os
from functools import lru_cache

from app.core.config import settings

# 中国大陆用户使用 HF 镜像加速下载
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")


@lru_cache(maxsize=1)
def _load_local_model(model_name: str):
    """懒加载本地 embedding 模型（全局单例）"""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)


class EmbeddingService:
    """向量嵌入生成"""

    def __init__(self, model: str = "", dimension: int = 0):
        self.model = model or settings.EMBEDDING_MODEL
        self.dimension = dimension or settings.EMBEDDING_DIM
        self._use_local = settings.EMBEDDING_USE_LOCAL

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """生成文本向量"""
        if self._use_local:
            return await self._embed_local(texts)
        return await self._embed_api(texts)

    async def embed_one(self, text: str) -> list[float]:
        res = await self.embed([text])
        return res[0] if res else []

    async def _embed_local(self, texts: list[str]) -> list[list[float]]:
        """使用本地 sentence-transformers 生成向量"""
        model = await asyncio.to_thread(_load_local_model, self.model)

        def _encode():
            embeddings = model.encode(texts, normalize_embeddings=True)
            return [emb.tolist() for emb in embeddings]

        return await asyncio.to_thread(_encode)

    async def _embed_api(self, texts: list[str]) -> list[list[float]]:
        """使用远程 API 生成向量"""
        from litellm import aembedding

        resp = await aembedding(
            model=self.model,
            input=texts,
            api_key=settings.LLM_API_KEY or None,
            api_base=settings.LLM_API_BASE or None,
        )
        return [item["embedding"] for item in resp.data]