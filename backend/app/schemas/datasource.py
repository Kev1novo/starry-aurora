"""
数据源相关 Pydantic Schema
包含数据源的创建、更新、查询响应及连接测试的请求/响应模型。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DataSourceCreate(BaseModel):
    """创建数据源请求体"""

    name: str = Field(
        ..., min_length=1, max_length=100, description="数据源别名，需唯一"
    )
    type: str = Field(
        ..., pattern=r"^(mysql|postgresql|clickhouse)$", description="数据库类型"
    )
    host: str = Field(..., max_length=255, description="数据库主机地址")
    port: int = Field(..., ge=1, le=65535, description="数据库端口")
    database_name: str = Field(..., max_length=100, description="数据库名称")
    username: str = Field(..., max_length=100, description="数据库用户名")
    password: str = Field(..., max_length=255, description="数据库密码")
    extra_params: Optional[str] = Field(
        None, max_length=500, description="连接额外参数，JSON 格式"
    )


class DataSourceUpdate(BaseModel):
    """更新数据源请求体（所有字段可选）"""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="数据源别名"
    )
    type: Optional[str] = Field(
        None, pattern=r"^(mysql|postgresql|clickhouse)$", description="数据库类型"
    )
    host: Optional[str] = Field(None, max_length=255, description="数据库主机地址")
    port: Optional[int] = Field(None, ge=1, le=65535, description="数据库端口")
    database_name: Optional[str] = Field(
        None, max_length=100, description="数据库名称"
    )
    username: Optional[str] = Field(None, max_length=100, description="数据库用户名")
    password: Optional[str] = Field(None, max_length=255, description="数据库密码")
    extra_params: Optional[str] = Field(
        None, max_length=500, description="连接额外参数，JSON 格式"
    )
    is_active: Optional[bool] = Field(None, description="是否启用")


class DataSourceResponse(BaseModel):
    """数据源响应体"""

    id: int = Field(..., description="数据源 ID")
    name: str = Field(..., description="数据源别名")
    type: str = Field(..., description="数据库类型")
    host: str = Field(..., description="数据库主机地址")
    port: int = Field(..., description="数据库端口")
    database_name: str = Field(..., description="数据库名称")
    status: str = Field(..., description="连接状态")
    created_at: datetime = Field(..., description="创建时间")

    model_config = ConfigDict(from_attributes=True)


class DataSourceList(BaseModel):
    """数据源列表响应体"""

    items: List[DataSourceResponse] = Field(..., description="数据源列表")
    total: int = Field(..., ge=0, description="总记录数")


class TestConnectionRequest(BaseModel):
    """测试连接请求体"""

    host: str = Field(..., max_length=255, description="数据库主机地址")
    port: int = Field(..., ge=1, le=65535, description="数据库端口")
    database_name: str = Field(..., max_length=100, description="数据库名称")
    username: str = Field(..., max_length=100, description="数据库用户名")
    password: str = Field(..., max_length=255, description="数据库密码")


class TestConnectionResponse(BaseModel):
    """测试连接响应体"""

    success: bool = Field(..., description="是否连接成功")
    message: str = Field(..., description="结果消息")
    latency_ms: Optional[float] = Field(None, description="连接延迟（毫秒）")