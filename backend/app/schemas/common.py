"""
通用响应 Pydantic Schema
提供分页参数、分页响应及统一 API 响应的数据模型。
"""

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """分页查询参数"""

    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应体"""

    items: List[T] = Field(..., description="当前页数据列表")
    total: int = Field(..., ge=0, description="总记录数")
    page: int = Field(..., ge=1, description="当前页码")
    page_size: int = Field(..., ge=1, description="每页条数")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应体"""

    code: int = Field(default=200, description="业务状态码")
    message: str = Field(default="success", description="业务消息")
    data: Optional[T] = Field(default=None, description="响应数据")