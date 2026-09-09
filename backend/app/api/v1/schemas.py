"""Schema 元数据 API 路由——用于查看和管理已同步的数据表结构"""
from fastapi import APIRouter, Depends, Query

from app.api.v1.auth import get_current_user
from app.core.dependencies import get_db
from app.models.user import User
from app.repositories.schema_repo import SchemaMetaRepository
from app.schemas.common import ApiResponse
from app.schemas.schema_meta import SchemaMetaResponse, SchemaTableResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/schemas", tags=["Schema"])


@router.get("/tables", response_model=ApiResponse[list[SchemaTableResponse]])
async def list_all_tables(
    datasource_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有数据表列表（可筛选数据源）"""
    repo = SchemaMetaRepository(db)
    if datasource_id:
        tables = await repo.list_tables(datasource_id)
    else:
        tables = []
    return ApiResponse(data=tables)


@router.get("/search", response_model=ApiResponse[list[SchemaMetaResponse]])
async def search_schema(
    keyword: str = Query(..., min_length=1),
    datasource_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """搜索 Schema 字段（按表名或字段名）"""
    repo = SchemaMetaRepository(db)
    limit = 50
    items = await repo.list(limit=limit)
    results = [
        SchemaMetaResponse.model_validate(item)
        for item in items
        if keyword.lower() in item.table_name.lower()
        or keyword.lower() in item.column_name.lower()
        or (item.description and keyword.lower() in item.description.lower())
    ]
    return ApiResponse(data=results)