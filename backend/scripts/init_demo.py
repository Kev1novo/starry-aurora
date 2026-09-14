"""
Demo 零售数据库一键初始化脚本

一键完成：
  1. 创建 demo_retail 数据库并灌入 7 张业务表 + 演示数据
  2. 在 starry_aurora 中注册 demo_retail 数据源
  3. 自动同步 Schema 元数据到 SchemaMeta 表
  4. 构建 Qdrant 向量索引 + ES 全文索引
  5. LLM 批量增强字段业务描述
  6. 输出完整的初始化报告

用法:
  python scripts/init_demo.py
  python scripts/init_demo.py --skip-llm    # 跳过 LLM 描述增强（更快）
  python scripts/init_demo.py --datasource-id 1  # 只触发同步，不重建数据库
"""
import asyncio
import os
import sys

# 确保从项目根目录导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def init_demo(skip_llm: bool = False, datasource_id: int | None = None):
    """一键初始化 demo 环境"""
    from pathlib import Path

    from app.core.config import settings

    print("=" * 60)
    print("  StarryAurora — Demo 零售数据库初始化")
    print("=" * 60)
    print()

    if datasource_id:
        # 只做同步
        print(f">> 触发完整同步 pipeline (datasource_id={datasource_id})...")
        result = await _full_sync(datasource_id)
        print(f">> 同步完成: {result['tables_count']} 张表, {result['fields_count']} 个字段")
        print(f"   Qdrant: {result.get('qdrant_count', 0)} 向量")
        print(f"   ES:     {result.get('es_count', 0)} 文档")
        if not skip_llm:
            enriched = await _llm_enrich(datasource_id)
            print(f">> LLM 描述增强: {enriched} 个字段已更新")
        print()
        _print_demo_summary(datasource_id)
        return datasource_id

    # ==== Step 1: 创建 demo_retail 数据库 ====
    sql_path = Path(__file__).parent / "seed_demo_retail.sql"
    if not sql_path.exists():
        print(f"[ERROR] 找不到 SQL 文件: {sql_path}")
        sys.exit(1)

    print("[1/5] 创建 demo_retail 数据库并灌入演示数据...")
    await _execute_sql_file(sql_path)
    print("  ✓ demo_retail 数据库已就绪（7 张业务表, 50+ 行数据）")
    print()

    # ==== Step 2: 解析数据库连接信息 ====
    # DATABASE_URL = mysql+aiomysql://user:pass@host:port/starry_aurora
    db_url = settings.DATABASE_URL
    parts = db_url.replace("mysql+aiomysql://", "").split("@")
    user_pass = parts[0].split(":")
    host_port_db = parts[1].split("/")
    host_port = host_port_db[0].split(":")
    db_user = user_pass[0]
    db_pass = ":".join(user_pass[1:]) if len(user_pass) > 1 else ""
    db_host = host_port[0]
    db_port = int(host_port[1]) if len(host_port) > 1 else 3306

    # ==== Step 3: 注册数据源 ====
    print("[2/5] 在 starry_aurora 中注册 demo_retail 数据源...")
    ds_id = await _register_demo_datasource(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_pass,
    )
    print(f"  ✓ 数据源已注册 (id={ds_id}, name=demo_retail)")
    print()

    # ==== Step 4: 完整同步 ====
    print("[3/5] 同步 Schema 元数据 → Qdrant 向量 → ES 全文索引...")
    result = await _full_sync(ds_id)
    print(f"  ✓ 同步完成: {result['tables_count']} 张表, {result['fields_count']} 个字段")
    print(f"  ✓ Qdrant: {result.get('qdrant_count', 0)} 个向量")
    print(f"  ✓ ES:     {result.get('es_count', 0)} 个文档")
    print()

    # ==== Step 5: LLM 批量描述增强 ====
    if not skip_llm:
        print("[4/5] LLM 批量增强字段业务描述...")
        enriched = await _llm_enrich(ds_id)
        print(f"  ✓ LLM 描述增强完成: {enriched} 个字段已更新")
        print()

    # ==== Step 6: 输出报告 ====
    print("[5/5] 生成初始化报告...")
    _print_demo_summary(ds_id)
    print()
    print("=" * 60)
    print("  Demo 环境初始化完成！")
    print("=" * 60)

    return ds_id


# ==================== 内部实现 ====================


async def _execute_sql_file(sql_path: Path):
    """在 MySQL 上执行 SQL 文件"""
    import aiomysql

    from app.core.config import settings

    db_url = settings.DATABASE_URL
    parts = db_url.replace("mysql+aiomysql://", "").split("@")
    user_pass = parts[0].split(":")
    host_port = parts[1].split("/")[0].split(":")
    db_user = user_pass[0]
    db_pass = ":".join(user_pass[1:]) if len(user_pass) > 1 else ""
    db_host = host_port[0]
    db_port = int(host_port[1]) if len(host_port) > 1 else 3306

    sql_content = sql_path.read_text(encoding="utf-8")

    # 连接到 MySQL（不指定数据库）先执行 CREATE DATABASE
    pool = await aiomysql.create_pool(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_pass,
        minsize=1,
        maxsize=1,
    )
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                # 按语句分割执行（忽略 USE 语句和执行结果输出）
                for statement in sql_content.split(";"):
                    stmt = statement.strip()
                    if not stmt or stmt.upper().startswith("SELECT"):
                        continue
                    if stmt.upper().startswith("USE"):
                        db_name = stmt[3:].strip().replace("`", "")
                        await cur.execute(f"USE `{db_name}`")
                        continue
                    try:
                        await cur.execute(stmt)
                    except Exception as e:
                        print(f"  [WARN] SQL 执行警告 (可忽略): {e}")
    finally:
        pool.close()
        await pool.wait_closed()


async def _register_demo_datasource(
    host: str,
    port: int,
    user: str,
    password: str,
) -> int:
    """在 starry_aurora 中注册 demo_retail 数据源（如果已存在则返回已有 ID）"""
    from app.core.database import AsyncSessionLocal
    from app.core.security import encrypt_password
    from app.models.datasource import DataSource
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        # 检查是否已存在
        stmt = select(DataSource).where(DataSource.name == "demo_retail")
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing.id

        ds = DataSource(
            name="demo_retail",
            type="mysql",
            host=host,
            port=port,
            database_name="demo_retail",
            username=user,
            password=encrypt_password(password),
            description="电商零售演示数据库 — 7 张业务表（产品/订单/客户/营销活动等）",
            user_id=1,  # admin 用户
        )
        session.add(ds)
        await session.commit()
        return ds.id


async def _full_sync(ds_id: int) -> dict:
    """执行完整同步 pipeline"""
    from app.core.config import settings
    from app.core.database import AsyncSessionLocal
    from app.core.elasticsearch import get_es
    from app.core.qdrant import ensure_collection
    from app.repositories.schema_repo import SchemaMetaRepository
    from app.search.indexing import sync_schema_to_es, sync_schema_to_qdrant
    from app.search.keyword_search import ensure_schema_index, SCHEMA_INDEX
    from app.search.vector_store import ensure_schema_collection
    from app.services.schema_service import SchemaService

    async with AsyncSessionLocal() as db:
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

    # 3. Qdrant 索引
    ensure_schema_collection(None, settings.EMBEDDING_DIM)
    qdrant_count = await sync_schema_to_qdrant(ds_id, field_dicts)

    # 4. ES 索引
    es = await anext(get_es())
    await ensure_schema_index(es)
    es_count = await sync_schema_to_es(ds_id, field_dicts)

    return {
        "tables_count": result.tables_count,
        "fields_count": result.fields_count,
        "qdrant_count": qdrant_count,
        "es_count": es_count,
    }


async def _llm_enrich(ds_id: int) -> int:
    """用 LLM 为每个表生成业务描述，更新 SchemaMeta."""
    from app.agents.shared.llm_factory import LLMFactory
    from app.core.database import AsyncSessionLocal
    from app.repositories.schema_repo import SchemaMetaRepository

    llm = LLMFactory(temperature=0.0)
    enriched = 0

    async with AsyncSessionLocal() as db:
        repo = SchemaMetaRepository(db)
        tables = await repo.list_tables(ds_id)

        for table_name in tables:
            fields = await repo.get_table_columns(ds_id, table_name)
            if not fields:
                continue

            # 跳过已有描述的字段
            need_enrich = [f for f in fields if not f.description or f.description == f.column_comment]
            if not need_enrich:
                continue

            # 构建 LLM prompt
            field_lines = []
            for f in need_enrich:
                field_lines.append(
                    f"  - {f.column_name} ({f.data_type})"
                    f"{' [PK]' if f.is_primary_key else ''}{' [FK]' if f.is_foreign_key else ''}"
                    f"{' 当前描述: ' + (f.column_comment or '') if f.column_comment else ''}"
                )

            prompt = f"""你是一个数据库语义专家。请为以下数据表「{table_name}」的每个字段生成简短的中文业务描述。

要求：
- 每个描述控制在 20 字以内
- 按业务含义命名，而非直接翻译字段名
- 区分相似字段（如 id vs category_id vs product_id）
- 返回 JSON 格式，key 为字段名，value 为描述

表名: {table_name}
字段列表:
{chr(10).join(field_lines)}

请返回 JSON (不要 markdown 包裹):
{{{{
  "字段名": "业务描述",
  ...
}}}}
"""
            try:
                raw = await llm.generate([{"role": "user", "content": prompt}])
                import json
                import re

                # 提取 JSON
                json_match = re.search(r"\{[\s\S]*\}", raw)
                if json_match:
                    descriptions = json.loads(json_match.group())
                    for f in need_enrich:
                        desc = descriptions.get(f.column_name)
                        if desc and isinstance(desc, str) and len(desc) > 2:
                            await repo.update(f.id, {"description": desc.strip()})
                            enriched += 1
                    print(f"    表 {table_name}: 更新了 {len([d for d in descriptions.values() if d])} 个字段描述")
            except Exception as e:
                print(f"    [WARN] 表 {table_name} 描述生成失败: {e}")
                continue

    return enriched


def _print_demo_summary(ds_id: int):
    """打印初始化报告摘要"""
    print()
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │                   初始化报告                            │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print(f"  │  数据源 ID:    {ds_id:<44}│")
    print("  │  数据源名称:  demo_retail                                │")
    print("  │  数据库:      demo_retail（7 张业务表）                  │")
    print("  │  用户:        admin / analyst                            │")
    print("  │                                                         │")
    print("  │  可用测试查询:                                          │")
    print("  │   - 上个月各品类销售额是多少？                          │")
    print("  │   - 哪个渠道的 ROI 最高？                               │")
    print("  │   - 北京地区的钻石会员有哪些？                          │")
    print("  │   - 按月份统计订单数量和金额趋势                        │")
    print("  └─────────────────────────────────────────────────────────┘")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Demo 零售数据库一键初始化")
    parser.add_argument("--skip-llm", action="store_true", help="跳过 LLM 描述增强")
    parser.add_argument("--datasource-id", type=int, default=None, help="只触发同步，不重建数据库")
    args = parser.parse_args()

    asyncio.run(init_demo(skip_llm=args.skip_llm, datasource_id=args.datasource_id))