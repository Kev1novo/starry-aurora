"""向量嵌入服务——支持 Qdrant 和通用嵌入"""
from app.core.config import settings


class EmbeddingService:
    """向量嵌入生成"""

    def __init__(self, model: str = "", dimension: int = 0):
        self.model = model or settings.EMBEDDING_MODEL
        self.dimension = dimension or settings.EMBEDDING_DIM

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """生成文本向量"""
        # 通过 LiteLLM 的 /embeddings 端点或直接调 Embedding API
        from litellm import aembedding

        resp = await aembedding(model=self.model, input=texts)
        return [item["embedding"] for item in resp.data]

    async def embed_one(self, text: str) -> list[float]:
        res = await self.embed([text])
        return res[0] if res else []