"""数据源 API 路由"""
from fastapi import APIRouter, Depends, Query

from app.api.v1.auth import get_current_user
from app.core.config import settings
from app.core.dependencies import get_db
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.repositories.datasource_repo import DataSourceRepository
from app.repositories.schema_repo import SchemaMetaRepository
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.datasource import (
    DataSourceCreate,
    DataSourceDetailResponse,
    DataSourceResponse,
    DataSourceUpdate,
    TestConnectionRequest,
    TestConnectionResponse,
)
from app.schemas.schema_meta import SchemaMetaResponse, SchemaTableResponse, SyncResultResponse
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


@router.get("/{ds_id}", response_model=ApiResponse[DataSourceDetailResponse])
async def get_datasource(
    ds_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取数据源详情（含用户名、数据库名等完整信息）"""
    service = DataSourceService(db)
    ds = await service.get_datasource(current_user.id, ds_id)
    return ApiResponse(data=DataSourceDetailResponse.model_validate(ds))


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


@router.post("/test", response_model=ApiResponse[TestConnectionResponse])
async def test_datasource_connection_raw(
    data: TestConnectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """测试数据库连接（未保存的数据源）"""
    service = DataSourceService(db)
    result = await service.test_connection(data)
    return ApiResponse(data=result)


@router.post("/{ds_id}/test", response_model=ApiResponse[TestConnectionResponse])
async def test_datasource_connection(
    ds_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """测试已保存数据源的连接（使用已保存的配置，无需 request body）"""
    from app.core.security import decrypt_password

    service = DataSourceService(db)
    ds = await service.get_datasource(current_user.id, ds_id)
    test_data = TestConnectionRequest(
        host=ds.host,
        port=ds.port,
        database_name=ds.database_name,
        username=ds.username,
        password=decrypt_password(ds.password),
    )
    result = await service.test_connection(test_data)
    return ApiResponse(data=result)


@router.post("/{ds_id}/sync", response_model=ApiResponse[SyncResultResponse])
async def sync_datasource_schemas(
    ds_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动触发 Schema 同步（MySQL + Qdrant 向量 + ES 全文）"""
    from app.repositories.schema_repo import SchemaMetaRepository
    from app.search.indexing import sync_schema_to_es, sync_schema_to_qdrant
    from app.core.qdrant import ensure_collection
    from app.search.vector_store import ensure_schema_collection
    from app.search.keyword_search import ensure_schema_index, SCHEMA_INDEX
    from app.core.elasticsearch import get_es

    # 1. MySQL 元数据同步
    service = SchemaService(db, None, None)
    result = await service.sync_datasource_schemas(ds_id)

    # 2. 读取刚同步的字段
    repo = SchemaMetaRepository(db)
    all_fields = await repo.list(limit=10000)
    ds_fields = [f for f in all_fields if f.datasource_id == ds_id]
    field_dicts = [
        {
            "id": f.id,
            "datasource_id": f.datasource_id,
            "table_name": f.table_name,
            "column_name": f.column_name,
            "data_type": f.data_type,
            "description": f.description or "",
            "column_comment": f.column_comment or "",
            "is_primary_key": f.is_primary_key,
            "ordinal_position": f.ordinal_position,
        }
        for f in ds_fields
    ]

    # 3. 索引到 Qdrant
    ensure_schema_collection(None, settings.EMBEDDING_DIM)
    qdrant_count = await sync_schema_to_qdrant(ds_id, field_dicts)

    # 4. 索引到 ES
    es = await anext(get_es())
    await ensure_schema_index(es)
    es_count = await sync_schema_to_es(ds_id, field_dicts)

    return ApiResponse(data=SyncResultResponse(
        tables_count=result.tables_count,
        fields_count=result.fields_count,
        status="success",
        message=f"MySQL {result.fields_count} 字段 → Qdrant {qdrant_count} 向量 → ES {es_count} 文档",
    ))


@router.get("/{ds_id}/schemas", response_model=ApiResponse[list[SchemaTableResponse]])
async def get_datasource_schemas(
    ds_id: int,
    table: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取数据源的 Schema（按表分组返回）"""
    repo = SchemaMetaRepository(db)

    # 确定查询范围
    if table:
        items = await repo.get_table_columns(ds_id, table)
    else:
        items = await repo.list(limit=10000)

    # 按表名分组
    table_map: dict[str, list[SchemaMetaResponse]] = {}
    for item in items:
        resp = SchemaMetaResponse.model_validate(item)
        table_map.setdefault(item.table_name, []).append(resp)

    tables = [
        SchemaTableResponse(
            table_name=tname,
            columns=cols,
            column_count=len(cols),
        )
        for tname, cols in sorted(table_map.items())
    ]
    return ApiResponse(data=tables)


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


@router.put("/{ds_id}/schemas/tables/{table_name}/columns/{column_name}", response_model=ApiResponse[SchemaMetaResponse])
async def update_field_description(
    ds_id: int,
    table_name: str,
    column_name: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新字段的业务描述"""
    repo = SchemaMetaRepository(db)
    fields = await repo.get_table_columns(ds_id, table_name)
    target = next((f for f in fields if f.column_name == column_name), None)
    if target is None:
        raise NotFoundException(detail=f"字段 {table_name}.{column_name} 不存在")
    description = body.get("business_description", "")
    updated = await repo.update(target.id, {"description": description})
    return ApiResponse(data=SchemaMetaResponse.model_validate(updated))


@router.post("/{ds_id}/schemas/enrich", response_model=ApiResponse)
async def enrich_field_descriptions(
    ds_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """LLM 批量增强字段业务描述（按表分组生成 → 更新 MySQL → 重建 Qdrant/ES 索引）"""
    from app.agents.shared.llm_factory import LLMFactory
    from app.core.config import settings
    from app.core.elasticsearch import get_es
    from app.core.qdrant import get_qdrant
    from app.search.indexing import sync_schema_to_es, sync_schema_to_qdrant
    from app.search.keyword_search import ensure_schema_index
    from app.search.vector_store import ensure_schema_collection

    repo = SchemaMetaRepository(db)
    tables = await repo.list_tables(ds_id)

    llm = LLMFactory(temperature=0.0)
    total_enriched = 0
    table_results = []

    for table_name in tables:
        fields = await repo.get_table_columns(ds_id, table_name)
        if not fields:
            continue

        # 只看没有业务描述的字段
        need_enrich = [
            f for f in fields
            if not f.description or f.description == f.column_comment
        ]
        if not need_enrich:
            continue

        field_lines = [
            f"  - {f.column_name} ({f.data_type})"
            f"{' [PK]' if f.is_primary_key else ''}{' [FK]' if f.is_foreign_key else ''}"
            f"{' 注释: ' + f.column_comment if f.column_comment else ''}"
            for f in need_enrich
        ]

        prompt = (
            f"你是一个数据库语义专家。请为数据表「{table_name}」的每个字段生成简短的中文业务描述。\n\n"
            "要求：\n"
            "- 每个描述控制在 20 字以内\n"
            "- 按业务含义命名，而非直接翻译字段名\n"
            "- 区分相似字段（id vs category_id vs product_id）\n"
            "- 返回 JSON，key=字段名, value=描述\n\n"
            f"表名: {table_name}\n"
            f"字段:\n{chr(10).join(field_lines)}\n\n"
            "返回 JSON:\n"
            '{"字段名": "业务描述", ...}'
        )

        try:
            raw = await llm.generate([{"role": "user", "content": prompt}])
            import json
            import re

            json_match = re.search(r"\{[\s\S]*\}", raw)
            if json_match:
                descriptions = json.loads(json_match.group())
                table_count = 0
                for f in need_enrich:
                    desc = descriptions.get(f.column_name)
                    if desc and isinstance(desc, str) and len(desc) > 2:
                        await repo.update(f.id, {"description": desc.strip()})
                        total_enriched += 1
                        table_count += 1
                table_results.append({"table": table_name, "enriched": table_count})
        except Exception as e:
            table_results.append({"table": table_name, "enriched": 0, "error": str(e)[:100]})

    # 重新构建 Qdrant + ES 索引
    all_fields = await repo.list(limit=10000)
    ds_fields = [f for f in all_fields if f.datasource_id == ds_id]
    field_dicts = [
        {
            "id": f.id,
            "datasource_id": f.datasource_id,
            "table_name": f.table_name,
            "column_name": f.column_name,
            "data_type": f.data_type,
            "description": f.description or "",
            "column_comment": f.column_comment or "",
            "is_primary_key": f.is_primary_key,
            "ordinal_position": f.ordinal_position,
        }
        for f in ds_fields
    ]

    ensure_schema_collection(get_qdrant(), settings.EMBEDDING_DIM)
    qdrant_count = await sync_schema_to_qdrant(ds_id, field_dicts)

    es = await anext(get_es())
    await ensure_schema_index(es)
    es_count = await sync_schema_to_es(ds_id, field_dicts)

    return ApiResponse(data={
        "total_enriched": total_enriched,
        "tables": table_results,
        "qdrant_count": qdrant_count,
        "es_count": es_count,
        "message": f"已增强 {total_enriched} 个字段的业务描述，Qdrant {qdrant_count} 向量 + ES {es_count} 文档已重建",
    })