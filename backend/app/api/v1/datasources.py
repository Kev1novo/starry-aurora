"""数据源 API 路由"""
from fastapi import APIRouter, Depends, Query

from app.api.v1.auth import get_current_user
from app.core.dependencies import get_db
from app.models.user import User
from app.repositories.datasource_repo import DataSourceRepository
from app.repositories.schema_repo import SchemaMetaRepository
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.datasource import (
    DataSourceCreate,
    DataSourceResponse,
    DataSourceUpdate,
    TestConnectionRequest,
    TestConnectionResponse,
)
from app.schemas.schema_meta import SchemaMetaResponse
from app.services.datasource_service import DataSourceService
from app.services.schema_service import SchemaService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/datasources", tags=["数据源"])


@router.get("", response_model=ApiResponse[PaginatedResponse[DataSourceResponse]])
async def list_datasources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取数据源列表"""
    service = DataSourceService(db)
    result = await service.list_datasources(current_user.id, page, page_size)
    return ApiResponse(data=result)


@router.post("", response_model=ApiResponse[DataSourceResponse])
async def create_datasource(
    data: DataSourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建新数据源"""
    service = DataSourceService(db)
    ds = await service.create(current_user.id, data)
    return ApiResponse(data=DataSourceResponse.model_validate(ds))


@router.get("/{ds_id}", response_model=ApiResponse[DataSourceResponse])
async def get_datasource(
    ds_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取数据源详情"""
    service = DataSourceService(db)
    ds = await service.get_datasource(current_user.id, ds_id)
    return ApiResponse(data=DataSourceResponse.model_validate(ds))


@router.put("/{ds_id}", response_model=ApiResponse[DataSourceResponse])
async def update_datasource(
    ds_id: int,
    data: DataSourceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新数据源配置"""
    service = DataSourceService(db)
    ds = await service.update(current_user.id, ds_id, data)
    return ApiResponse(data=DataSourceResponse.model_validate(ds))


@router.delete("/{ds_id}", response_model=ApiResponse)
async def delete_datasource(
    ds_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除数据源"""
    service = DataSourceService(db)
    await service.delete(current_user.id, ds_id)
    return ApiResponse(message="数据源已删除")


@router.post("/{ds_id}/test", response_model=ApiResponse[TestConnectionResponse])
async def test_datasource_connection(
    ds_id: int,
    data: TestConnectionRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """测试数据源连接"""
    service = DataSourceService(db)
    if data:
        result = await service.test_connection(data)
    else:
        ds = await service.get_datasource(current_user.id, ds_id)
        test_data = TestConnectionRequest(
            host=ds.host,
            port=ds.port,
            database_name=ds.database_name,
            username=ds.username,
            password=ds.password,
        )
        result = await service.test_connection(test_data)
    return ApiResponse(data=result)


@router.post("/{ds_id}/sync", response_model=ApiResponse)
async def sync_datasource_schemas(
    ds_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动触发 Schema 同步"""
    service = SchemaService(db, None, None)  # qdrant/es 占位
    result = await service.sync_datasource_schemas(ds_id)
    return ApiResponse(message=f"同步完成: {result.tables_count} 表, {result.fields_count} 字段")


@router.get("/{ds_id}/schemas", response_model=ApiResponse[list[SchemaMetaResponse]])
async def get_datasource_schemas(
    ds_id: int,
    table: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取数据源的 Schema 字段列表"""
    repo = SchemaMetaRepository(db)
    if table:
        items = await repo.get_table_columns(ds_id, table)
    else:
        items = await repo.list(limit=1000)
    return ApiResponse(data=[SchemaMetaResponse.model_validate(item) for item in items])


@router.get("/{ds_id}/schemas/tables", response_model=ApiResponse[list[str]])
async def list_datasource_tables(
    ds_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取数据源的表名列表"""
    repo = SchemaMetaRepository(db)
    tables = await repo.list_tables(ds_id)
    return ApiResponse(data=tables)