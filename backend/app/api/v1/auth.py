"""
认证路由
提供注册、登录、令牌刷新、登出等认证相关端点。
"""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.common import ApiResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["认证"])


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """依赖注入：获取 AuthService 实例"""
    return AuthService(db)


async def get_current_user(
    authorization: str = Header(..., description="Bearer {token}"),
    db: AsyncSession = Depends(get_db),
) -> "UserResponse":
    """
    依赖注入：解析当前用户信息

    从 Authorization header 提取 JWT token，解码后返回用户信息。

    Args:
        authorization: Authorization 请求头，格式为 "Bearer <token>"
        db: 数据库会话

    Returns:
        当前用户的信息响应

    Raises:
        HTTPException 401: 令牌缺失或无效
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization 头格式错误，应为 Bearer <token>",
        )
    token = authorization.removeprefix("Bearer ")
    service = AuthService(db)
    try:
        user = await service.get_current_user(token)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return UserResponse.model_validate(user)


@router.post("/register", response_model=ApiResponse[UserResponse])
async def register(
    req: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[UserResponse]:
    """
    用户注册

    创建新用户账号，返回用户基本信息。

    - **username**: 用户名，2-50 字符
    - **email**: 电子邮箱
    - **password**: 密码，6-128 字符
    """
    try:
        user = await service.register(req)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return ApiResponse(
        code=201,
        message="注册成功",
        data=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=ApiResponse[LoginResponse])
async def login(
    req: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[LoginResponse]:
    """
    用户登录

    验证用户名和密码，返回 access_token, refresh_token 和用户信息。
    """
    try:
        tokens, user = await service.authenticate(req)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return ApiResponse(
        code=200, message="登录成功",
        data=LoginResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            user=UserResponse.model_validate(user),
        ),
    )


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh_token(
    req: RefreshTokenRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[TokenResponse]:
    """
    刷新访问令牌

    使用 refresh_token 换取新的 access_token 和 refresh_token。
    """
    try:
        tokens = await service.refresh_token(req.refresh_token)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return ApiResponse(code=200, message="令牌刷新成功", data=tokens)


@router.post("/logout", response_model=ApiResponse[None])
async def logout(
    authorization: str = Header(..., description="Bearer {token}"),
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[None]:
    """
    用户登出

    使当前用户的 refresh_token 失效。需要登录状态。
    """
    token = authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else ""
    await service.logout(token)
    return ApiResponse(code=200, message="登出成功")