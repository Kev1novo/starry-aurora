"""
用户管理路由
提供当前用户信息查询、用户列表与详情管理等端点。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.repositories.user_repo import UserRepository
from app.schemas.auth import UserResponse
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationParams

router = APIRouter(prefix="/users", tags=["用户管理"])


async def require_admin(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """
    依赖注入：要求当前用户为 admin 角色

    Args:
        current_user: 当前登录用户信息

    Returns:
        当前用户信息

    Raises:
        HTTPException 403: 非管理员访问
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅管理员可执行此操作",
        )
    return current_user


@router.get("/me", response_model=ApiResponse[UserResponse])
async def get_me(
    current_user: UserResponse = Depends(get_current_user),
) -> ApiResponse[UserResponse]:
    """
    获取当前登录用户信息

    返回当前认证用户的详细资料。
    """
    return ApiResponse(code=200, message="success", data=current_user)


@router.get("/", response_model=ApiResponse[PaginatedResponse[UserResponse]])
async def list_users(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    _: UserResponse = Depends(require_admin),
) -> ApiResponse[PaginatedResponse[UserResponse]]:
    """
    获取用户列表（仅管理员）

    分页返回所有用户信息列表。

    - **page**: 页码，从 1 开始
    - **page_size**: 每页条数，默认 20，最大 100
    """
    repo = UserRepository(db)
    skip = (pagination.page - 1) * pagination.page_size
    users = await repo.list(skip=skip, limit=pagination.page_size)
    total = await repo.count()
    items = [UserResponse.model_validate(u) for u in users]
    return ApiResponse(
        code=200,
        message="success",
        data=PaginatedResponse(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        ),
    )


@router.get("/{user_id}", response_model=ApiResponse[UserResponse])
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: UserResponse = Depends(require_admin),
) -> ApiResponse[UserResponse]:
    """
    获取指定用户详情（仅管理员）

    Args:
        user_id: 用户 ID
    """
    repo = UserRepository(db)
    user = await repo.get(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 {user_id} 不存在",
        )
    return ApiResponse(
        code=200,
        message="success",
        data=UserResponse.model_validate(user),
    )