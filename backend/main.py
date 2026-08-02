"""
AgentForge – FastAPI Application Entry Point
==============================================
LOCAL_DEV=true (default):
  • SQLite instead of PostgreSQL
  • FakeRedis instead of Redis
  • Neo4j disabled (stub)
  • Swagger UI always enabled
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from agentforge.backend.api.routes import auth, documents, health, research, websocket
from agentforge.backend.core.config import settings
from agentforge.backend.core.exceptions import (
    AgentForgeError,
    agentforge_exception_handler,
    generic_exception_handler,
)
from agentforge.backend.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

_LOCAL_DEV = os.getenv("LOCAL_DEV", "true").lower() in ("true", "1", "yes")


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Startup and shutdown lifecycle."""
    logger.info("agentforge_starting", version=settings.APP_VERSION,
                env=settings.ENVIRONMENT, local_dev=_LOCAL_DEV)

    # 1. Create database tables (SQLite or PostgreSQL)
    from agentforge.backend.database.session import create_tables
    await create_tables()
    logger.info("database_tables_ready")

    # 2. Initialise FAISS index
    from agentforge.backend.vectorstore.faiss_store import get_vector_store
    await get_vector_store()
    logger.info("faiss_index_ready")

    # 3. Neo4j (stub in local dev, real connection in production)
    from agentforge.backend.services.neo4j_service import (
        KnowledgeGraphService, get_neo4j_driver
    )
    try:
        driver = await get_neo4j_driver()
        kg = KnowledgeGraphService(driver)
        await kg.create_constraints()
        logger.info("neo4j_ready", local_stub=_LOCAL_DEV)
    except Exception as exc:
        logger.warning("neo4j_skipped", error=str(exc))

    # 4. Redis (fakeredis in local dev)
    from agentforge.backend.services.redis_service import get_redis_client
    try:
        redis = await get_redis_client()
        await redis.ping()
        logger.info("redis_ready", local_stub=_LOCAL_DEV)
    except Exception as exc:
        logger.warning("redis_skipped", error=str(exc))

    # 5. Pre-compile LangGraph workflow
    from agentforge.backend.graph.workflow import get_research_graph
    get_research_graph()
    logger.info("langgraph_ready")

    logger.info("agentforge_started")
    yield  # ← application running

    # Shutdown
    from agentforge.backend.services.redis_service import close_redis
    await close_redis()

    from agentforge.backend.database.session import engine
    await engine.dispose()

    logger.info("agentforge_shutdown_complete")


# ── Application Factory ────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "AgentForge – Autonomous Multi-Agent AI Research System.\n\n"
            "Running in **local dev mode** (SQLite + FakeRedis, no Docker needed)."
            if _LOCAL_DEV else
            "AgentForge – Autonomous Multi-Agent AI Research System."
        ),
        version=settings.APP_VERSION,
        docs_url="/docs",      # always enabled so you can explore the API
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AgentForgeError, agentforge_exception_handler)  # type: ignore
    app.add_exception_handler(Exception, generic_exception_handler)           # type: ignore

    prefix = settings.API_PREFIX
    app.include_router(health.router)
    app.include_router(auth.router,      prefix=prefix)
    app.include_router(research.router,  prefix=prefix)
    app.include_router(documents.router, prefix=prefix)
    app.include_router(websocket.router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "agentforge.backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=1,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
