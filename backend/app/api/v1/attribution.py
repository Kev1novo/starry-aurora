"""归因分析 API 路由"""
from fastapi import APIRouter, Depends, Query

from app.api.v1.auth import get_current_user
from app.core.dependencies import get_db
from app.models.user import User
from app.schemas.attribution import AttributionAnalysisRequest, AttributionModelInfo
from app.schemas.common import ApiResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/attribution", tags=["归因分析"])


@router.get("/models", response_model=ApiResponse[list[AttributionModelInfo]])
async def list_attribution_models():
    """获取可用归因模型列表"""
    from app.agents.attribution_models.registry import registry

    models = registry.list_models()
    return ApiResponse(data=[AttributionModelInfo(**m) for m in models])


@router.post("/analyze")
async def analyze_attribution(
    data: AttributionAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """执行归因分析"""
    from app.agents.insight_agent.agent import InsightAgent

    agent = InsightAgent(db)
    result = await agent.handle_attribution(
        model_name=data.model,
        datasource_id=data.datasource_id,
        touchpoint_table=data.touchpoint_table,
        conversion_table=data.conversion_table,
        time_range=data.time_range,
        user_id=current_user.id,
        params=data.params,
    )
    return ApiResponse(data=result)


@router.post("/analyze/stream")
async def analyze_attribution_stream(
    data: AttributionAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """归因分析 SSE 流式响应"""
    from app.agents.insight_agent.agent import InsightAgent
    from app.middleware.sse import EventSourceResponse

    import json

    agent = InsightAgent(db)

    async def event_generator():
        async for event in agent.handle_attribution_stream(
            model_name=data.model,
            datasource_id=data.datasource_id,
            touchpoint_table=data.touchpoint_table,
            conversion_table=data.conversion_table,
            time_range=data.time_range,
            user_id=current_user.id,
            params=data.params,
        ):
            yield {"event": event["type"], "data": json.dumps(event["data"], ensure_ascii=False)}

    return EventSourceResponse(event_generator())