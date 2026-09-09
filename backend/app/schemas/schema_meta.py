"""Schema 元数据 Pydantic Schemas"""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SchemaMetaResponse(BaseModel):
    """Schema 元数据响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    datasource_id: int
    table_name: str
    column_name: str
    ordinal_position: int
    data_type: str
    is_nullable: bool
    column_default: str | None = None
    column_comment: str | None = None
    description: str | None = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    indexed: bool = False
    created_at: datetime
    updated_at: datetime


class SchemaTableResponse(BaseModel):
    """数据表响应（含字段列表）"""
    table_name: str
    columns: list[SchemaMetaResponse]
    column_count: int


class SyncResult(BaseModel):
    """Schema 同步结果"""
    tables_count: int = 0
    fields_count: int = 0