"""
CORS 中间件配置
基于配置中心的 CORS_ORIGINS 白名单配置跨域策略。
"""

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware

from app.core.config import settings


def configure_cors(app: FastAPI) -> None:
    """
    注册 CORS 中间件
    从配置读取允许的源列表，允许携带凭证的跨域请求。
    """
    app.add_middleware(
        StarletteCORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_origin_regex=None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition", "X-Request-Id"],
        max_age=600,
    )