"""
全局异常层次定义
为 NL2SQL + 归因分析平台提供统一的异常层次结构和 FastAPI 异常处理器。
"""

from typing import Any, Dict, Type

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi import status


class AppException(Exception):
    """
    应用基础异常
    Attributes:
        status_code: HTTP 状态码
        detail: 错误详情描述
        code: 业务错误码（可选）
    """

    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "服务器内部错误",
        code: str = "INTERNAL_ERROR",
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code
        super().__init__(self.detail)


# ---------- 认证与权限 ----------

class AuthException(AppException):
    """认证异常（401）"""

    def __init__(self, detail: str = "认证失败", code: str = "AUTH_FAILED") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            code=code,
        )


class PermissionException(AppException):
    """权限异常（403）"""

    def __init__(self, detail: str = "无权限访问", code: str = "PERMISSION_DENIED") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            code=code,
        )


# --------- 查询 ----------

class QueryException(AppException):
    """查询相关基础异常（400）"""

    def __init__(self, detail: str = "查询异常", code: str = "QUERY_ERROR") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail, code=code)


class SQLValidationError(QueryException):
    """SQL 验证失败"""

    def __init__(self, detail: str = "SQL 验证未通过", code: str = "SQL_VALIDATION_ERROR") -> None:
        super().__init__(detail=detail, code=code)


class SQLExecutionError(AppException):
    """SQL 执行异常（500）"""

    def __init__(self, detail: str = "SQL 执行时发生错误", code: str = "SQL_EXECUTION_ERROR") -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            code=code,
        )


# ---------- 归因分析 ---------

class AttributionException(AppException):
    """归因分析异常（500）"""

    def __init__(self, detail: str = "归因分析失败", code: str = "ATTRIBUTION_ERROR") -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            code=code,
        )


# ---------- 通用 ----------

class NotFoundException(AppException):
    """资源未找到（404）"""

    def __init__(self, detail: str = "请求的资源不存在", code: str = "NOT_FOUND") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail, code=code)


class ValidationException(AppException):
    """请求参数校验失败（422）"""

    def __init__(self, detail: str = "请求参数校验失败", code: str = "VALIDATION_ERROR") -> None:
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail, code=code)


# ---------- 异常处理器 ----------

async def _app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """通用应用异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


async def _general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底异常处理器（未捕获的异常）"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "服务器内部错误", "code": "INTERNAL_ERROR"},
    )


exception_handlers: Dict[Type[Exception], Any] = {
    AppException: _app_exception_handler,
    Exception: _general_exception_handler,
}


def register_exception_handlers(app: FastAPI) -> None:
    """
    向 FastAPI 应用注册全局异常处理器
    """
    for exc_type, handler in exception_handlers.items():
        app.add_exception_handler(exc_type, handler)