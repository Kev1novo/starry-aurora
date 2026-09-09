"""NL2SQL 查询 API——SSE 流式端点"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.dependencies import get_db
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.query import QueryAskRequest, QueryResponse

router = APIRouter(prefix="/queries", tags=["NL2SQL 查询"])


@router.post("/ask")
async def ask_question(
    data: QueryAskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    NL2SQL 查询入口
    普通请求模式（SSE 模式使用 Accept: text/event-stream 触发流式响应）
    """
    from app.agents.insight_agent.agent import InsightAgent

    agent = InsightAgent(db)
    result = await agent.handle_query(
        question=data.question,
        user_id=current_user.id,
        datasource_id=data.datasource_id,
        conversation_id=data.conversation_id,
    )
    return ApiResponse(data=result)


@router.post("/ask/stream")
async def ask_question_stream(
    data: QueryAskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    NL2SQL 查询 SSE 流式响应
    请使用 EventSource 或 fetch + ReadableStream 消费
    """
    from app.agents.insight_agent.agent import InsightAgent
    from app.middleware.sse import EventSourceResponse

    agent = InsightAgent(db)

    async def event_generator():
        async for event in agent.handle_query_stream(
            question=data.question,
            user_id=current_user.id,
            datasource_id=data.datasource_id,
            conversation_id=data.conversation_id,
        ):
            yield {"event": event["type"], "data": json.dumps(event["data"], ensure_ascii=False)}

    return EventSourceResponse(event_generator())


@router.get("/history", response_model=ApiResponse[list[QueryResponse]])
async def get_query_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取查询历史"""
    # 从对话记录中获取用户的消息历史
    from app.repositories.conversation_repo import ConversationRepository

    repo = ConversationRepository(db)
    conversations, total = await repo.list_by_user(current_user.id, page, page_size)
    return ApiResponse(data=[], message=f"共 {total} 条对话记录")


@router.get("/{query_id}")
async def get_query_detail(
    query_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询详情"""
    from app.repositories.conversation_repo import ConversationRepository

    repo = ConversationRepository(db)
    conv = await repo.get(query_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="查询记录不存在")
    messages = await repo.get_messages(query_id)
    return ApiResponse(data={
        "conversation": {"id": conv.id, "title": conv.title, "created_at": conv.created_at.isoformat()},
        "messages": [{"id": m.id, "role": m.role, "content": m.content[:500], "type": m.message_type} for m in messages],
    })