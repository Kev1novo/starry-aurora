"""LLM 工厂——基于 LiteLLM 的统一封装"""
from typing import Any, AsyncGenerator, Optional

from litellm import acompletion

from app.core.config import settings


class LLMFactory:
    """大模型调用统一封装"""

    def __init__(
        self,
        model: str = "",
        temperature: Optional[float] = None,
        max_tokens: int = 0,
    ):
        raw_model = model or settings.LLM_MODEL
        # LiteLLM 要求模型名带 provider 前缀（如 openai/qwen-plus）
        if "/" not in raw_model and settings.LLM_PROVIDER:
            self.model = f"{settings.LLM_PROVIDER}/{raw_model}"
        else:
            self.model = raw_model
        self.temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE
        self.max_tokens = max_tokens or settings.LLM_MAX_TOKENS

    async def generate(self, messages: list[dict], **kwargs) -> str:
        """同步请求"""
        resp = await acompletion(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            api_key=settings.LLM_API_KEY or None,
            api_base=settings.LLM_API_BASE or None,
            **kwargs,
        )
        return resp.choices[0].message.content or ""

    async def stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        """流式请求"""
        resp = await acompletion(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
            api_key=settings.LLM_API_KEY or None,
            api_base=settings.LLM_API_BASE or None,
            **kwargs,
        )
        async for chunk in resp:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta