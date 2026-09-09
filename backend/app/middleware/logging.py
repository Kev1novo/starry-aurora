"""
请求日志中间件
记录每个 HTTP 请求的方法、路径、耗时、状态码。
"""

import logging
import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

logger = logging.getLogger("starry_aurora.http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件
    记录请求方法、路径、耗时、状态码，用于监控和排障。
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start_time

        logger.info(
            "HTTP 请求",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query),
                "status_code": response.status_code,
                "elapsed_ms": round(elapsed * 1000, 2),
                "client_host": request.client.host if request.client else None,
            },
        )
        return response


def configure_request_logging(app: FastAPI) -> None:
    """注册请求日志中间件"""
    app.add_middleware(RequestLoggingMiddleware)