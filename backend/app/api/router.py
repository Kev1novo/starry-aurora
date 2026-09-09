"""
主路由聚合
将各业务模块的 v1 路由汇总到统一的路由器下。
"""

from fastapi import APIRouter

from app.api.v1 import attribution, auth, conversations, datasources, health, queries, schemas, users

api_router = APIRouter(prefix="/api/v1")

# ---------- 健康检查 ----------
api_router.include_router(health.router, tags=["health"])

# ---------- 认证 ----------
api_router.include_router(auth.router)

# ---------- 用户管理 ----------
api_router.include_router(users.router)

# ---------- 数据源 ----------
api_router.include_router(datasources.router)

# ---------- Schema 元数据 ----------
api_router.include_router(schemas.router)

# ---------- NL2SQL 查询 ----------
api_router.include_router(queries.router)

# ---------- 会话工作区 ----------
api_router.include_router(conversations.router)

# ---------- 归因分析 ----------
api_router.include_router(attribution.router)