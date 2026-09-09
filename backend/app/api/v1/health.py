"""
健康检查端点
提供 Liveness 和 Readiness 探针，用于容器编排与监控。
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.elasticsearch import get_es
from app.core.qdrant import get_qdrant
from app.core.redis import get_redis

router = APIRouter()


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis: "Redis" = Depends(get_redis),  # noqa: F821
) -> dict:
    """
    综合健康检查
    依次检查数据库、Redis、Qdrant、Elasticsearch 连通性。
    任一组件不可用不返回 500，而是标记其状态为 unhealthy。
    """
    checks = {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {},
    }

    # ---- 数据库 ----
    try:
        await db.execute(text("SELECT 1"))
        checks["services"]["database"] = "healthy"
    except Exception as e:
        checks["services"]["database"] = f"unhealthy: {e}"
        checks["status"] = "degraded"

    # ---- Redis ----
    try:
        await redis.ping()
        checks["services"]["redis"] = "healthy"
    except Exception as e:
        checks["services"]["redis"] = f"unhealthy: {e}"
        checks["status"] = "degraded"

    # ---- Qdrant ----
    try:
        qdrant = get_qdrant()
        qdrant.get_collections()
        checks["services"]["qdrant"] = "healthy"
    except Exception as e:
        checks["services"]["qdrant"] = f"unhealthy: {e}"
        checks["status"] = "degraded"

    # ---- Elasticsearch ----
    try:
        es = await get_es().__anext__()
        await es.ping()
        checks["services"]["elasticsearch"] = "healthy"
    except Exception as e:
        checks["services"]["elasticsearch"] = f"unhealthy: {e}"
        checks["status"] = "degraded"

    return checks


@router.get("/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
    redis: "Redis" = Depends(get_redis),  # noqa: F821
) -> dict:
    """
    Kubernetes Readiness Probe
    检查必要组件（DB + Redis）是否就绪，任一不可用返回 503。
    """
    errors = []

    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        errors.append(f"database: {e}")

    try:
        await redis.ping()
    except Exception as e:
        errors.append(f"redis: {e}")

    if errors:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"ready": False, "errors": errors},
        )

    return {"ready": True, "timestamp": datetime.now(timezone.utc).isoformat()}