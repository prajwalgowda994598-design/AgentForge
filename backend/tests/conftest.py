"""
Shared pytest fixtures for AgentForge tests.
Uses in-memory SQLite for database tests (no PostgreSQL required for unit tests).
"""

import os
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# ── Force test environment BEFORE any settings are imported ──────────────────
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake-key")
os.environ.setdefault("POSTGRES_PASSWORD", "testpassword")
os.environ.setdefault("NEO4J_PASSWORD", "testpassword")
os.environ.setdefault("FAISS_INDEX_PATH", "/tmp/faiss_test")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("REDIS_HOST", "localhost")

from agentforge.backend.database.session import Base


# ── In-memory SQLite engine (no real DB needed for unit tests) ────────────────

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh in-memory SQLite database for each test function."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ── Mock OpenAI LLM ────────────────────────────────────────────────────────────

@pytest.fixture
def mock_llm():
    """A mock LLM that returns a canned response."""
    mock = AsyncMock()
    mock.ainvoke = AsyncMock(return_value="Mocked LLM response for testing.")
    return mock


# ── Mock FAISS Store ───────────────────────────────────────────────────────────

@pytest.fixture
def mock_vector_store():
    store = AsyncMock()
    store.similarity_search = AsyncMock(
        return_value=[
            {
                "faiss_id": 0,
                "score": 0.85,
                "title": "Sample Document",
                "source": "sample.txt",
                "content": "This is a sample document content for testing.",
            }
        ]
    )
    store.add_documents = AsyncMock(return_value=[0, 1])
    store.get_stats = MagicMock(return_value={"total_vectors": 2, "dimension": 1536})
    return store


# ── Sample workflow state ──────────────────────────────────────────────────────

@pytest.fixture
def sample_state() -> dict:
    return {
        "session_id": str(uuid.uuid4()),
        "query": "What are the latest advances in quantum computing?",
        "top_k": 3,
        "iteration": 0,
        "agent_status": {},
        "agent_timings": {},
        "retrieved_chunks": [],
        "web_snippets": [],
    }
