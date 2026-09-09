"""归因分析请求 Schema"""
from typing import Any, Optional

from pydantic import BaseModel


class AttributionModelInfo(BaseModel):
    name: str
    description: str


class AttributionAnalysisRequest(BaseModel):
    model: str = "first_touch"
    datasource_id: int
    touchpoint_table: str
    conversion_table: str
    time_range: Optional[dict] = None
    params: dict[str, Any] = {}


class TouchpointResponse(BaseModel):
    channel: str
    touch_count: int
    contribution: float
    contribution_pct: float


class AttributionResultResponse(BaseModel):
    model: str
    total_conversions: int
    total_revenue: float
    touchpoints: list[TouchpointResponse]
    chart_data: dict
    insights: list[str]