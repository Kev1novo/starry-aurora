"""数据画像工具"""
from typing import Any


async def profile_table(db, table_name: str, datasource_id: int) -> dict[str, Any]:
    """获取表数据概况"""
    return {"table_name": table_name, "note": "schema explorer - profile not yet implemented"}


async def get_metric_summary(db, table: str, metric_column: str) -> dict:
    """获取指标字段汇总统计"""
    return {"min": 0, "max": 0, "avg": 0, "count": 0}