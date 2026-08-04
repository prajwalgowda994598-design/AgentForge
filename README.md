# AgentForge 🤖
## Autonomous Multi-Agent AI Research System

[![CI/CD](https://github.com/prajwalgowda994598-design/AgentForge/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/prajwalgowda994598-design/AgentForge/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-45%20passing-brightgreen.svg)](#testing)

AgentForge is a production-ready **autonomous multi-agent AI research system** that uses a collaborative pipeline of five specialised agents to answer complex research questions with high factual accuracy.

---

## Architecture

```
User  ──►  React Frontend  ──►  FastAPI Backend  ──►  LangGraph Workflow
                                      │
                    ┌─────────────────┼─────────────────────┐
                    │                 │                       │
                  FAISS           PostgreSQL                Neo4j
               (Vectors)         (Sessions,               (Knowledge
                                 Audit Logs,                Graph)
                                   Users)
                    │
                  Redis
               (Cache, WS
                Sessions)

LangGraph Workflow:
  START
    │
    ▼
  Researcher ◄──────────────────────────┐
    │                                   │ score < 0.7
    ▼                                   │
  Summarizer                            │
    │                                   │
    ▼                                   │
  Critic ──────── score < 0.7 ──────────┘
    │
  score ≥ 0.7
    │
    ▼
  Fact Checker
    │
    ▼
  Synthesizer
    │
    ▼
  END → Final Answer
```

---

## Agents

| Agent | Role | Key Output |
|-------|------|-----------|
| 🔍 **Researcher** | Searches FAISS + Web, extracts key facts | `raw_context`, `refined_research` |
| 📝 **Summarizer** | Condenses findings into structured notes | `summary` |
| ⚖️ **Critic** | Scores quality 0–1, triggers retry if needed | `critic_score`, `should_retry` |
| ✅ **Fact Checker** | Verifies claims, adds citations | `verified_summary` |
| 🧩 **Synthesizer** | Generates polished Markdown answer | `final_answer` |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | Python 3.12+, FastAPI, Uvicorn |
| Agent Orchestration | LangGraph, LangChain |
| LLM | OpenRouter (free tier) or OpenAI GPT-4o |
| Embeddings | Local `all-MiniLM-L6-v2` (free) or OpenAI |
| Vector Store | FAISS (IndexIDMap + IndexFlatL2) |
| Knowledge Graph | Neo4j 5 Community |
| Relational DB | PostgreSQL 16 + SQLAlchemy async |
| Cache / Sessions | Redis 7 |
| Real-time | WebSockets (FastAPI native) |
| Auth | JWT (python-jose) + bcrypt passwords |
| Frontend | React 18, TypeScript, Tailwind CSS, Vite |
| Containerisation | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Deployment | AWS EC2 |

---

## Quick Start

### Prerequisites
- Docker ≥ 24 + Docker Compose ≥ 2.20
- An LLM API key (OpenRouter free tier recommended — no credit card needed)

### 1. Clone
```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/agentforge.git
cd agentforge
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env:
#   - Set OPENROUTER_API_KEY (get one free at https://openrouter.ai/keys)
#   - Set SECRET_KEY to a random 64-char string
#   - Set POSTGRES_PASSWORD and NEO4J_PASSWORD
```

### 3. Start
```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost |
| Backend API docs | http://localhost:8000/docs |
| Neo4j Browser | http://localhost:7474 |

### 4. Load sample data
```bash
curl -X POST http://localhost:8000/api/v1/documents/load-sample
```

---

## Run locally (one-click)

If you want a single command to prepare the environment and run the backend + frontend for local development, use the provided one-click scripts in `scripts/`.

- Windows (PowerShell):

```powershell
# from inside the agentforge folder
.\scripts\run_local_dev.ps1
```

- macOS / Linux (Bash):

```bash
# from inside the agentforge folder
./scripts/run_local_dev.sh
```

What the scripts do:
- Create and/or activate a Python virtual environment (`.venv`) and install backend dependencies.
- Install frontend dependencies (`npm ci`) if missing.
- Start the FastAPI backend on port 8000 and the Vite frontend on port 3000 (or 5173 if configured).
- Logs are written to `logs/backend.log` and `logs/frontend.log` so you can inspect startup output.

If you prefer manual steps, see the "Local Development (without Docker)" section above.

---

## Local Development (without Docker)

### Backend — no Docker, no API key needed for tests

```bash
cd agentforge

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r backend/requirements.txt

# Copy and configure environment
cp .env.example .env
# Set LOCAL_DEV=true (default) — uses SQLite + FakeRedis, no Docker needed
# Set OPENROUTER_API_KEY for live queries

# Run
set PYTHONPATH=..  # Windows — one level up from agentforge/
python -m uvicorn agentforge.backend.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

---

## API Reference

### Auth Endpoints *(new — required for session access)*

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/register` | None | Create a new account |
| `POST` | `/api/v1/auth/token` | None | Login — returns JWT bearer token |

**Register:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "yourpassword"}'
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "yourpassword"}'
# → {"access_token": "eyJ...", "token_type": "bearer", "expires_in": 3600}
```

Use the token in subsequent requests:
```bash
curl http://localhost:8000/api/v1/research \
  -H "Authorization: Bearer eyJ..."
```

---

### Research Endpoints *(requires auth)*

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/research` | Submit research query |
| `GET`  | `/api/v1/research/{id}` | Get session status |
| `GET`  | `/api/v1/research/{id}/runs` | Agent run details |
| `GET`  | `/api/v1/research` | List user sessions |

### Document Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/documents` | Ingest document |
| `GET`  | `/api/v1/documents/stats` | Vector store stats |
| `POST` | `/api/v1/documents/load-sample` | Load sample data |

### System Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Liveness probe |
| `GET`  | `/health/ready` | Readiness probe |

### WebSocket

```
ws://localhost:8000/ws/{session_id}
```
Events: `agent_status`, `stream_chunk`, `final_result`, `error`

---

## Testing

```bash
cd agentforge

# Run all 45 tests (no API keys or Docker needed)
pytest backend/tests/ -v

# Unit tests only
pytest backend/tests/unit/ -v

# Integration tests only
pytest backend/tests/integration/ -v

# With coverage report
pytest backend/tests/ --cov=backend --cov-report=html
```

All tests use in-memory SQLite + mocked services — no real API calls.

---

## Database Schema

### PostgreSQL Tables

```sql
users             (id, email, hashed_password, is_active, created_at)
research_sessions (id, user_id, query, status, final_answer, critic_score, ...)
agent_runs        (id, session_id, agent_name, status, execution_time_ms, ...)
audit_logs        (id, session_id, event_type, actor, payload, ip_address, ...)
documents         (id, title, source, content, content_hash, faiss_id, ...)
knowledge_nodes   (id, neo4j_id, node_type, label, properties, ...)
```

### Neo4j Schema

```
(:Concept)    -[:RELATES_TO]->  (:Concept)
(:Finding)    -[:DERIVED_FROM]-> (:Source)
(:Finding)    -[:MENTIONS]->    (:Concept)
(:Source)     -[:CITES]->       (:Source)
```

---

## Deployment Guide (AWS EC2)

1. **Launch EC2** – Ubuntu 22.04 LTS, t3.medium or larger
2. **Install Docker** on the instance
3. **Clone the repo** to `/opt/agentforge`
4. **Create `.env`** with production values
5. **Configure GitHub Secrets** (see `.github/workflows/ci-cd.yml` header)
6. **Push to `main`** — GitHub Actions builds, pushes to Docker Hub, deploys via SSH

See [`docs/deployment.md`](docs/deployment.md) for detailed steps.

---

## Project Structure

```
agentforge/
├── backend/
│   ├── agents/           # 5 autonomous agents
│   ├── api/routes/       # FastAPI route handlers (auth, research, documents, health, ws)
│   ├── core/             # Config, logging, exceptions, dependencies
│   ├── database/         # SQLAlchemy models (users, sessions, runs, ...), session factory
│   ├── graph/            # LangGraph workflow
│   ├── models/           # Pydantic schemas
│   ├── services/         # Redis, Neo4j, auth, ingestion, audit, WebSocket
│   ├── vectorstore/      # FAISS vector store
│   ├── tests/            # 45 unit + integration tests
│   ├── main.py           # FastAPI application entry point
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── hooks/        # Custom React hooks
│   │   ├── pages/        # Page-level components
│   │   ├── types/        # TypeScript types
│   │   └── utils/        # API client, helpers
│   ├── package.json
│   └── vite.config.ts
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── docs/
│   ├── api.md
│   ├── deployment.md
│   └── testing.md
├── sample_data/
├── .github/workflows/ci-cd.yml
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## License

MIT © 2024 AgentForge Contributors
