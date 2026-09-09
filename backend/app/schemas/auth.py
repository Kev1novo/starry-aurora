"""
认证相关 Pydantic Schema
包含用户注册、登录、令牌刷新及用户信息响应的数据模型。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    """用户注册请求体"""

    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    email: str = Field(..., max_length=100, description="电子邮箱")
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class LoginRequest(BaseModel):
    """用户登录请求体"""

    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """令牌响应体"""

    access_token: str = Field(..., description="JWT 访问令牌")
    refresh_token: str = Field(..., description="JWT 刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")


class LoginResponse(TokenResponse):
    """登录响应体（含令牌和用户信息）"""

    user: "UserResponse" = Field(..., description="用户信息")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求体"""

    refresh_token: str = Field(..., description="刷新令牌")


class UserResponse(BaseModel):
    """用户信息响应体"""

    id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="电子邮箱")
    role: str = Field(..., description="用户角色")
    is_active: bool = Field(..., description="是否激活")
    created_at: datetime = Field(..., description="创建时间")

    model_config = ConfigDict(from_attributes=True)