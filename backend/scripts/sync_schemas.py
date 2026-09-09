"""
Schema 元数据同步脚本
从 MySQL INFORMATION_SCHEMA 抽取表结构，写入 SchemaMeta 表、Qdrant 向量索引、ES 全文索引

用法: python scripts/sync_schemas.py --datasource-id 1
"""
import asyncio
import argparse

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.qdrant import get_qdrant
from app.core.elasticsearch import get_es
from app.services.schema_service import SchemaService


async def sync_schemas(datasource_id: int) -> None:
    print(f"Syncing schemas for datasource_id={datasource_id}...")
    db_gen = async_session_factory()
    db = await db_gen.__anext__()
    qdrant = get_qdrant()
    es = get_es()

    service = SchemaService(db, qdrant, es)
    result = await service.sync_datasource_schemas(datasource_id)

    print(f"Synced {result.tables_count} tables, {result.fields_count} fields")
    await db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync database schemas")
    parser.add_argument("--datasource-id", type=int, required=True, help="DataSource ID")
    args = parser.parse_args()

    asyncio.run(sync_schemas(args.datasource_id))