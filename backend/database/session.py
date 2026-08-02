"""
AgentForge – Async SQLAlchemy Session Factory
===============================================
Auto-detects environment:
  • LOCAL_DEV=true  → SQLite (aiosqlite) — no PostgreSQL needed
  • otherwise       → PostgreSQL (asyncpg)

All database connections are async for non-blocking I/O.
"""

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# ── Detect local dev mode ──────────────────────────────────────────────────────
_LOCAL_DEV = os.getenv("LOCAL_DEV", "true").lower() in ("true", "1", "yes")


def _build_database_url() -> str:
    """Return the correct async database URL for the current environment."""
    if _LOCAL_DEV:
        # SQLite stored next to the project — zero config required
        db_path = os.path.join(os.path.dirname(__file__), "..", "..", "agentforge_local.db")
        db_path = os.path.abspath(db_path)
        return f"sqlite+aiosqlite:///{db_path}"
    else:
        # Production PostgreSQL — all values come from environment variables
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        db   = os.getenv("POSTGRES_DB",   "agentforge")
        user = os.getenv("POSTGRES_USER", "agentforge")
        pw   = os.getenv("POSTGRES_PASSWORD", "")
        return f"postgresql+asyncpg://{user}:{pw}@{host}:{port}/{db}"


DATABASE_URL = _build_database_url()

# ── Engine ─────────────────────────────────────────────────────────────────────
_engine_kwargs: dict = {
    "echo": os.getenv("APP_DEBUG", "false").lower() == "true",
    "pool_pre_ping": True,
}

# SQLite needs connect_args to allow cross-thread usage in async context
if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs.update({"pool_size": 10, "max_overflow": 20, "pool_recycle": 3600})

engine = create_async_engine(DATABASE_URL, **_engine_kwargs)

# ── Session factory ────────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ── Declarative base ───────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """All ORM models inherit from this base class."""
    pass


async def create_tables() -> None:
    """Create all tables on startup (idempotent — skips existing tables)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    """Drop all tables. Use in test teardown only."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
