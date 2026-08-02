# AgentForge – Testing Guide

## Overview

The test suite covers three layers:
- **Unit tests** – isolated agent logic, workflow routing, vector store
- **Integration tests** – FastAPI endpoint contracts (including auth)

**No real database, Docker, or API keys are needed for the full test suite.**  
All external dependencies are mocked: in-memory SQLite, FakeRedis, mock LLM.

---

## Running Tests

### Install test dependencies
```bash
cd agentforge
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r backend/requirements.txt
```

### Run all 45 tests
```bash
# From the agentforge/ directory:
pytest backend/tests/ -v
```

### Run specific test categories
```bash
# Unit tests only
pytest backend/tests/unit/ -v

# Integration tests only
pytest backend/tests/integration/ -v

# A single test class
pytest backend/tests/unit/test_agents.py::TestCriticAgent -v

# Auth tests only
pytest backend/tests/integration/test_api.py::TestAuthEndpoints -v

# With coverage report
pytest backend/tests/ --cov=backend --cov-report=html --cov-report=term-missing
```

---

## Test Environment

Tests automatically set required environment variables via `conftest.py`.  
No `.env` file is needed.

For end-to-end tests against real services (Docker stack must be running):
```bash
LOCAL_DEV=false \
ENVIRONMENT=test \
OPENROUTER_API_KEY=sk-or-v1-your-key \
POSTGRES_HOST=localhost \
REDIS_HOST=localhost \
NEO4J_URI=bolt://localhost:7687 \
pytest backend/tests/ -v
```

---

## Test Structure

```
backend/tests/
├── conftest.py              # Shared fixtures: mock DB, mock LLM, sample state
├── unit/
│   ├── test_agents.py       # All 5 agents + network failure scenarios (19 tests)
│   ├── test_workflow.py     # LangGraph routing, state management (9 tests)
│   └── test_vectorstore.py  # FAISS store: add, search, hash (4 tests)
└── integration/
    └── test_api.py          # FastAPI endpoint contracts incl. JWT auth (13 tests)
```

Total: **45 tests**

---

## Mocking Strategy

| External Service | Mock Used |
|-----------------|-----------|
| OpenAI / OpenRouter LLM | `AsyncMock` on `agent._llm` |
| FAISS / Embeddings | `AsyncMock` returning fixed vectors |
| PostgreSQL (unit tests) | `aiosqlite` in-memory SQLite via `conftest` |
| PostgreSQL (auth tests) | `create_async_engine("sqlite+aiosqlite:///:memory:")` |
| Redis | `AsyncMock` with `ping()`, `get()`, `set()` |
| Neo4j | `AsyncMock` driver |
| DuckDuckGo Search | `patch("langchain_community.tools.DuckDuckGoSearchRun")` |

---

## Writing New Tests

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_my_agent(sample_state):
    from agentforge.backend.agents.my_agent import MyAgent

    agent = MyAgent()
    with patch.object(agent, "_llm") as llm_mock:
        chain_mock = AsyncMock()
        chain_mock.ainvoke = AsyncMock(return_value="Expected output")
        llm_mock.__or__ = MagicMock(return_value=chain_mock)

        result = await agent._execute(sample_state)

    assert "expected_key" in result
```

For auth integration tests, use the `app_with_db` fixture (creates a real in-memory SQLite DB with the `users` table):

```python
@pytest.mark.asyncio
async def test_register(app_with_db):
    async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/register",
                                     json={"email": "x@example.com", "password": "pass1234"})
    assert response.status_code == 201
```

---

## CI/CD Test Configuration

Tests run automatically on every push via GitHub Actions.  
The CI job uses `LOCAL_DEV=true` so no Postgres or Redis Docker services are required.  
See [`.github/workflows/ci-cd.yml`](../.github/workflows/ci-cd.yml) for the full configuration.
