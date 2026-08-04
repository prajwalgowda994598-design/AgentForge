"""
AgentForge – Health Check & System Routes
===========================================
Lightweight health and readiness probes used by Docker, Kubernetes,
and load balancers.

GET /health       – Liveness probe (always returns 200 if process is up)
GET /health/ready – Readiness probe (checks all downstream services)
GET /metrics      – Basic runtime metrics (no Prometheus dependency)
"""

from fastapi import APIRouter

from agentforge.backend.core.config import settings
from agentforge.backend.core.logging import get_logger
from agentforge.backend.database.session import engine
from agentforge.backend.models.schemas import HealthResponse

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/health", response_model=dict, summary="Liveness probe")
async def liveness():
    """Always returns 200 if the process is running."""
    return {"status": "ok", "service": settings.APP_NAME}


@router.get("/health/ready", response_model=HealthResponse, summary="Readiness probe")
async def readiness():
    """
    Checks connectivity to all external services.
    Returns 200 only when all critical services are reachable.
    """
    import asyncio

    service_checks: dict = {}

    # ── PostgreSQL ─────────────────────────────────────────────────────────────
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        service_checks["postgres"] = "ok"
    except Exception as exc:
        logger.warning("health_postgres_failed", error=str(exc))
        service_checks["postgres"] = "down"

    # ── Redis ──────────────────────────────────────────────────────────────────
    try:
        from agentforge.backend.services.redis_service import get_redis_client
        redis = await get_redis_client()
        await redis.ping()
        service_checks["redis"] = "ok"
    except Exception as exc:
        logger.warning("health_redis_failed", error=str(exc))
        service_checks["redis"] = "down"

    # ── Neo4j ──────────────────────────────────────────────────────────────────
    try:
        from agentforge.backend.services.neo4j_service import get_neo4j_driver
        driver = await get_neo4j_driver()
        await driver.verify_connectivity()
        service_checks["neo4j"] = "ok"
    except Exception as exc:
        logger.warning("health_neo4j_failed", error=str(exc))
        service_checks["neo4j"] = "degraded"

    # ── FAISS ──────────────────────────────────────────────────────────────────
    try:
        from agentforge.backend.vectorstore.faiss_store import get_vector_store
        vs = await get_vector_store()
        _ = vs.get_stats()
        service_checks["faiss"] = "ok"
    except Exception as exc:
        logger.warning("health_faiss_failed", error=str(exc))
        service_checks["faiss"] = "degraded"

    overall = (
        "ok"
        if all(v == "ok" for v in service_checks.values())
        else "degraded"
    )

    return HealthResponse(
        status=overall,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        services=service_checks,
    )


@router.get("/metrics", summary="Runtime metrics")
async def metrics():
    """Basic operational metrics — swap for Prometheus exporter in production."""
    import os
    import sys
    from agentforge.backend.services.websocket_manager import ws_manager

    return {
        "active_ws_sessions": ws_manager.active_sessions,
        "python_version": sys.version,
        "environment": settings.ENVIRONMENT,
    }
