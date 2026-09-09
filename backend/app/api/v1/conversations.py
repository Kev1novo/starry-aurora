"""会话工作区 API 路由"""
from fastapi import APIRouter, Depends, Query

from app.api.v1.auth import get_current_user
from app.core.dependencies import get_db
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationResponse,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
)
from app.services.conversation_service import ConversationService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/conversations", tags=["会话工作区"])


@router.post("", response_model=ApiResponse[ConversationResponse])
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建会话"""
    service = ConversationService(db)
    conv = await service.create_conversation(current_user.id, data.title, data.workspace_type)
    msg_count = 0
    return ApiResponse(data=ConversationResponse(
        id=conv.id, user_id=conv.user_id, title=conv.title,
        workspace_type=conv.workspace_type, status=conv.status,
        created_at=conv.created_at, updated_at=conv.updated_at,
        message_count=msg_count,
    ))


@router.get("", response_model=ApiResponse[PaginatedResponse[ConversationResponse]])
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取会话列表"""
    service = ConversationService(db)
    items, total = await service.list_conversations(current_user.id, page, page_size)
    results = []
    for conv in items:
        cnt = await service.repo.get_message_count(conv.id)
        results.append(ConversationResponse(
            id=conv.id, user_id=conv.user_id, title=conv.title,
            workspace_type=conv.workspace_type, status=conv.status,
            created_at=conv.created_at, updated_at=conv.updated_at,
            message_count=cnt,
        ))
    return ApiResponse(data=PaginatedResponse(items=results, total=total, page=page, page_size=page_size))


@router.get("/{conv_id}", response_model=ApiResponse[ConversationDetailResponse])
async def get_conversation(
    conv_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取会话详情（含消息列表）"""
    service = ConversationService(db)
    result = await service.get_conversation_detail(conv_id, current_user.id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="会话不存在")
    conv, messages = result
    return ApiResponse(data=ConversationDetailResponse(
        id=conv.id, user_id=conv.user_id, title=conv.title,
        workspace_type=conv.workspace_type, status=conv.status,
        created_at=conv.created_at, updated_at=conv.updated_at,
        messages=[MessageResponse.model_validate(m) for m in messages],
    ))


@router.put("/{conv_id}", response_model=ApiResponse[ConversationResponse])
async def update_conversation(
    conv_id: int,
    data: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新会话"""
    service = ConversationService(db)
    conv = await service.update_conversation(conv_id, current_user.id, title=data.title, status=data.status)
    if not conv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="会话不存在")
    msg_count = await service.repo.get_message_count(conv.id)
    return ApiResponse(data=ConversationResponse(
        id=conv.id, user_id=conv.user_id, title=conv.title,
        workspace_type=conv.workspace_type, status=conv.status,
        created_at=conv.created_at, updated_at=conv.updated_at,
        message_count=msg_count,
    ))


@router.delete("/{conv_id}", response_model=ApiResponse)
async def delete_conversation(
    conv_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除会话"""
    service = ConversationService(db)
    ok = await service.delete_conversation(conv_id, current_user.id)
    if not ok:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="会话不存在")
    return ApiResponse(message="会话已删除")


@router.post("/{conv_id}/messages", response_model=ApiResponse[MessageResponse])
async def add_message(
    conv_id: int,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """添加消息"""
    service = ConversationService(db)
    msg = await service.add_message(conv_id, current_user.id, data.role, data.content, data.message_type)
    if not msg:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="会话不存在")
    return ApiResponse(data=MessageResponse.model_validate(msg))