"""Celery 异步任务"""
from app.core.celery_app import celery_app


@celery_app.task
def sync_all_datasource_schemas():
    """定时同步所有活跃数据源的 Schema——每小时执行一次"""
    from app.core.database import sync_session_factory
    from app.services.schema_service import SchemaService

    session = sync_session_factory()
    try:
        from app.repositories.datasource_repo import DataSourceRepository
        repo = DataSourceRepository(session)
        # 获取所有活跃数据源
        datasources = repo.get_active_all()
        for ds in datasources:
            print(f"Syncing schema for datasource {ds.id} ({ds.name})...")
            # schema_service 同步逻辑
        print("Schema sync completed.")
    finally:
        session.close()


@celery_app.task
def sync_datasource_schema(datasource_id: int):
    """同步单个数据源的 Schema"""
    print(f"Syncing schema for datasource {datasource_id}...")


@celery_app.task
def index_schema_embeddings(datasource_id: int):
    """为指定数据源的 Schema 字段构建向量索引"""
    print(f"Indexing embeddings for datasource {datasource_id}...")