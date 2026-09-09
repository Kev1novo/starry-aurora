"""
FastAPI 应用工厂
提供 create_app 工厂函数，完成中间件、异常处理器、路由、生命周期事件的注册。
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.elasticsearch import close_es_client, create_es_client
from app.core.exceptions import register_exception_handlers
from app.core.qdrant import create_qdrant_client
from app.core.redis import close_redis_pool, create_redis_pool
from app.middleware.cors import configure_cors
from app.middleware.logging import configure_request_logging
from app.utils.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    应用生命周期管理
    - 启动时初始化基础设施连接（Redis、ES、Qdrant）
    - 关闭时优雅释放连接池
    """
    # ---- 启动 ----
    setup_logging()
    await create_redis_pool()
    await create_es_client()
    create_qdrant_client()

    yield

    # ---- 关闭 ----
    await close_redis_pool()
    await close_es_client()
    await engine.dispose()


def create_app() -> FastAPI:
    """
    创建并配置 FastAPI 应用实例
    Returns:
        配置完成的 FastAPI 应用
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # ---------- 中间件注册（顺序重要） ----------
    configure_request_logging(app)   # 在最外层记录所有请求
    configure_cors(app)

    # ---------- 全局异常处理器 ----------
    register_exception_handlers(app)

    # ---------- 路由注册 ----------
    app.include_router(api_router)

    return app