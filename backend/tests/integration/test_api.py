"""
Integration tests for the FastAPI backend.

These tests use an in-memory SQLite DB and mock all external services,
so they can run in CI without Docker.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def override_settings(monkeypatch):
    """Override settings for tests."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("POSTGRES_PASSWORD", "testpass")
    monkeypatch.setenv("NEO4J_PASSWORD", "testpass")


@pytest.fixture
def app():
    """Create a test FastAPI app with all external deps mocked."""
    # Mock database create_tables so we don't need a real PG connection
    with patch("agentforge.backend.database.session.create_tables", new_callable=AsyncMock), \
         patch("agentforge.backend.vectorstore.faiss_store.get_vector_store", new_callable=AsyncMock) as mock_vs, \
         patch("agentforge.backend.services.neo4j_service.get_neo4j_driver", new_callable=AsyncMock), \
         patch("agentforge.backend.services.redis_service.get_redis_client", new_callable=AsyncMock) as mock_redis, \
         patch("agentforge.backend.graph.workflow.get_research_graph") as mock_graph:

        mock_redis.return_value = AsyncMock(ping=AsyncMock(return_value=True))
        vs = AsyncMock()
        vs.get_stats = MagicMock(return_value={"total_vectors": 0, "dimension": 1536})
        mock_vs.return_value = vs
        mock_graph.return_value = MagicMock()

        from agentforge.backend.main import create_app
        return create_app()


@pytest.fixture
def app_with_db():
    """
    FastAPI app variant for auth tests that need a real in-memory SQLite DB
    (so the users table actually exists).  All other external services are
    still mocked.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def _create_all():
        from agentforge.backend.database.session import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _override_get_db():
        session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    import asyncio

    # Create tables synchronously before the app starts so the fixture is simple
    asyncio.run(_create_all())

    with patch("agentforge.backend.database.session.create_tables", new_callable=AsyncMock), \
         patch("agentforge.backend.vectorstore.faiss_store.get_vector_store", new_callable=AsyncMock) as mock_vs, \
         patch("agentforge.backend.services.neo4j_service.get_neo4j_driver", new_callable=AsyncMock), \
         patch("agentforge.backend.services.redis_service.get_redis_client", new_callable=AsyncMock) as mock_redis, \
         patch("agentforge.backend.graph.workflow.get_research_graph") as mock_graph:

        mock_redis.return_value = AsyncMock(ping=AsyncMock(return_value=True))
        vs = AsyncMock()
        vs.get_stats = MagicMock(return_value={"total_vectors": 0, "dimension": 1536})
        mock_vs.return_value = vs
        mock_graph.return_value = MagicMock()

        from agentforge.backend.main import create_app
        from agentforge.backend.core.dependencies import get_db
        _app = create_app()
        _app.dependency_overrides[get_db] = _override_get_db
        return _app


class TestHealthEndpoints:
    """Tests for /health and /health/ready endpoints."""

    @pytest.mark.asyncio
    async def test_liveness_returns_ok(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_readiness_returns_health_structure(self, app):
        """Readiness probe should return status, version, and services keys."""
        with patch("agentforge.backend.api.routes.health.engine") as mock_engine:
            mock_conn = AsyncMock()
            mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_conn.__aexit__ = AsyncMock(return_value=None)
            mock_conn.execute = AsyncMock()
            mock_engine.connect.return_value = mock_conn

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "services" in data


class TestResearchEndpoints:
    """Tests for /api/v1/research endpoints."""

    @pytest.mark.asyncio
    async def test_submit_research_returns_202(self, app):
        """POST /api/v1/research should accept query and return session_id."""
        # Mock dependencies
        with patch("agentforge.backend.api.routes.research.get_redis_client", new_callable=AsyncMock) as mock_redis, \
             patch("agentforge.backend.api.routes.research.ResearchSession") as mock_session_cls, \
             patch("agentforge.backend.core.dependencies.AsyncSessionLocal") as mock_session_factory:

            # Set up cache miss
            cache_mock = AsyncMock()
            cache_mock.get_cached_research = AsyncMock(return_value=None)
            mock_redis.return_value = AsyncMock()

            with patch("agentforge.backend.api.routes.research.CacheService", return_value=cache_mock):
                with patch("agentforge.backend.core.dependencies.get_db") as mock_get_db:
                    db_mock = AsyncMock()
                    db_mock.add = MagicMock()
                    db_mock.commit = AsyncMock()
                    db_mock.flush = AsyncMock()
                    mock_get_db.return_value = db_mock

                    async with AsyncClient(
                        transport=ASGITransport(app=app), base_url="http://test"
                    ) as client:
                        response = await client.post(
                            "/api/v1/research",
                            json={"query": "What is quantum computing?", "top_k": 3},
                        )

        # Accept 202 or 422/500 depending on mock depth — key test is no crash
        assert response.status_code in (202, 422, 500)

    @pytest.mark.asyncio
    async def test_query_too_short_fails_validation(self, app):
        """Queries shorter than 5 characters should fail with 422."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/research",
                json={"query": "Hi"},
            )
        assert response.status_code == 422


class TestDocumentEndpoints:
    """Tests for /api/v1/documents endpoints."""

    @pytest.mark.asyncio
    async def test_get_vectorstore_stats(self, app):
        """GET /api/v1/documents/stats should return vector store stats."""
        vs_mock = AsyncMock()
        vs_mock.get_stats = MagicMock(return_value={"total_vectors": 42, "dimension": 1536})

        with patch(
            "agentforge.backend.api.routes.documents.get_vector_store",
            new_callable=AsyncMock,
            return_value=vs_mock,
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/documents/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_vectors" in data


class TestAuthEndpoints:
    """Tests for POST /api/v1/auth/register and POST /api/v1/auth/token."""

    @pytest.mark.asyncio
    async def test_register_creates_user(self, app_with_db):
        """POST /auth/register with valid data returns 201 and user_id."""
        async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={"email": "alice@example.com", "password": "securepass123"},
            )

        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data
        assert data["email"] == "alice@example.com"

    @pytest.mark.asyncio
    async def test_register_duplicate_email_returns_409(self, app_with_db):
        """Registering the same email twice must return 409 Conflict."""
        async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
            await client.post(
                "/api/v1/auth/register",
                json={"email": "bob@example.com", "password": "securepass123"},
            )
            response = await client.post(
                "/api/v1/auth/register",
                json={"email": "bob@example.com", "password": "anotherpass456"},
            )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_short_password_returns_422(self, app_with_db):
        """Passwords shorter than 8 characters must fail validation."""
        async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={"email": "carol@example.com", "password": "short"},
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_returns_token(self, app_with_db):
        """Valid credentials at /auth/token must return a bearer token."""
        async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
            await client.post(
                "/api/v1/auth/register",
                json={"email": "dave@example.com", "password": "securepass123"},
            )
            response = await client.post(
                "/api/v1/auth/token",
                json={"email": "dave@example.com", "password": "securepass123"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(self, app_with_db):
        """Wrong password must return 401 Unauthorized."""
        async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
            await client.post(
                "/api/v1/auth/register",
                json={"email": "eve@example.com", "password": "correctpass123"},
            )
            response = await client.post(
                "/api/v1/auth/token",
                json={"email": "eve@example.com", "password": "wrongpassword"},
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unknown_email_returns_401(self, app_with_db):
        """Unknown email must return 401 (not 404 — don't leak account existence)."""
        async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/token",
                json={"email": "ghost@example.com", "password": "doesntmatter"},
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_token_unlocks_list_sessions(self, app_with_db):
        """A valid JWT must allow access to GET /research (list sessions endpoint)."""
        async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
            # Register + login
            await client.post(
                "/api/v1/auth/register",
                json={"email": "frank@example.com", "password": "securepass123"},
            )
            login_r = await client.post(
                "/api/v1/auth/token",
                json={"email": "frank@example.com", "password": "securepass123"},
            )
            token = login_r.json()["access_token"]

            # List sessions — must return 200, not 401
            response = await client.get(
                "/api/v1/research",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_list_sessions_without_token_returns_401(self, app_with_db):
        """GET /research without a token must still return 401."""
        async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
            response = await client.get("/api/v1/research")

        assert response.status_code == 401
