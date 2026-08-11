# AgentForge 🤖

> **Portfolio project** — Autonomous multi-agent AI research system. Five specialised LangGraph agents collaborate to answer complex research questions with cited, fact-checked answers. Zero-cost LLM via OpenRouter free tier; no Docker required for local dev.

[![CI/CD](https://github.com/prajwalgowda994598-design/AgentForge/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/prajwalgowda994598-design/AgentForge/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![React](https://img.shields.io/badge/frontend-React%2018%20%2B%20TypeScript-61dafb.svg)](https://react.dev)
[![Tests](https://img.shields.io/badge/tests-45%20passing-brightgreen.svg)](#testing)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/prajwalgowda994598-design/AgentForge)

---

## Live Demo

> ⚠️ Free-tier Render — first request after idle takes **30–60 s** to wake up.

| Service | URL |
|---|---|
| **Frontend** | [agentforge-frontend.onrender.com](https://agentforge-frontend.onrender.com) |
| **Backend API (Swagger)** | [agentforge-backend-0jm1.onrender.com/docs](https://agentforge-backend-0jm1.onrender.com/docs) |
| **Health check** | [agentforge-backend-0jm1.onrender.com/health](https://agentforge-backend-0jm1.onrender.com/health) |

---

## What It Does

You type a research question. Five agents work in a conveyor-line pipeline:

| # | Agent | Job |
|---|---|---|
| 1 | 🔍 **Researcher** | Queries FAISS vector store + DuckDuckGo web search, pulls relevant facts |
| 2 | 📝 **Summarizer** | Condenses raw findings into structured notes |
| 3 | ⚖️ **Critic** | Scores quality 0–1; if score < 0.7, loops back to Researcher |
| 4 | ✅ **Fact Checker** | Cross-verifies each claim, adds citations |
| 5 | 🧩 **Synthesizer** | Produces a polished Markdown answer with sources |

Results stream in real-time via WebSocket. The UI updates each agent's status live.

---

## Architecture

```
Browser (React + Vite)
       │  WebSocket + REST
       ▼
FastAPI Backend (Uvicorn)
       │
       ├── LangGraph Workflow ──► Researcher → Summarizer → Critic → Fact Checker → Synthesizer
       │
       ├── FAISS Vector Store  (OpenAI-compatible embeddings via OpenRouter)
       ├── SQLite / PostgreSQL  (sessions, agent runs, audit log)
       ├── FakeRedis / Redis    (cache, session state)
       └── OpenRouter API       (LLM — free tier, no credit card)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Python 3.11+, FastAPI, Uvicorn |
| Agent Orchestration | LangGraph, LangChain |
| LLM | OpenRouter free tier (`nvidia/nemotron-3-super-120b-a12b:free`) or OpenAI |
| Embeddings | OpenAI `text-embedding-3-small` via OpenRouter (or local sentence-transformers) |
| Vector Store | FAISS (IndexIDMap + IndexFlatL2) |
| Relational DB | SQLite (local dev) / PostgreSQL (production) |
| Cache | FakeRedis (local dev) / Redis (production) |
| Real-time | WebSockets (FastAPI native) |
| Frontend | React 18, TypeScript, Tailwind CSS, Vite |
| CI/CD | GitHub Actions |
| Deployment | Render (backend + frontend) |

---

## Quick Start — Local Dev (No Docker Required)

### Prerequisites
- Python 3.11+
- Node.js 18+
- An OpenRouter API key (free — no credit card): [openrouter.ai/keys](https://openrouter.ai/keys)

### 1. Clone

```bash
git clone https://github.com/prajwalgowda994598-design/AgentForge.git
cd AgentForge/agentforge
```

### 2. Configure

```bash
cp .env.example .env
# Open .env and set:
#   OPENROUTER_API_KEY=sk-or-v1-your-key-here
# Everything else works out of the box for local dev.
```

### 3. Start — Backend (Terminal 1)

**Windows PowerShell:**
```powershell
.\run_backend.ps1
```

**macOS / Linux:**
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-local.txt
export PYTHONPATH=$(pwd)/..
python -m uvicorn agentforge.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

→ API docs at **http://localhost:8000/docs**

### 4. Start — Frontend (Terminal 2)

**Windows PowerShell:**
```powershell
.\run_frontend.ps1
```

**macOS / Linux:**
```bash
cd frontend && npm install && npm run dev
```

→ App at **http://localhost:3000**

---

## API Reference

### Research

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/research` | Optional | Submit a research query |
| `GET` | `/api/v1/research/{id}` | — | Poll session status + result |
| `GET` | `/api/v1/research/{id}/runs` | — | Per-agent run records |
| `GET` | `/api/v1/research` | Required | List your sessions |

**Submit query:**
```bash
curl -X POST http://localhost:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest breakthroughs in quantum computing?", "top_k": 5}'
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "message": "Research pipeline started. Connect to /ws/{session_id} for live updates."
}
```

### WebSocket (live agent updates)

```
ws://localhost:8000/ws/{session_id}
```

Events: `agent_status` · `stream_chunk` · `final_result` · `error`

### Documents

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/documents` | Ingest a document into FAISS |
| `GET` | `/api/v1/documents/stats` | Vector store stats |
| `POST` | `/api/v1/documents/load-sample` | Load bundled sample data |

### Health

```bash
curl http://localhost:8000/health/ready
```

---

## Testing

```bash
# Run all tests (no API key or Docker needed — uses mocks)
cd agentforge
pytest backend/tests/ -v

# With coverage
pytest backend/tests/ --cov=backend --cov-report=term-missing
```

---

## Project Structure

```
agentforge/
├── backend/
│   ├── agents/              # 5 autonomous agents (researcher, summarizer, critic, fact_checker, synthesizer)
│   ├── api/routes/          # FastAPI routes (research, documents, auth, health, websocket)
│   ├── core/                # Config, logging, exceptions, dependencies
│   ├── database/            # SQLAlchemy models + async session factory
│   ├── graph/               # LangGraph workflow (StateGraph + conditional edges)
│   ├── models/              # Pydantic schemas
│   ├── services/            # Redis, Neo4j, auth, ingestion, audit, WebSocket manager
│   ├── vectorstore/         # FAISS vector store (async, thread-safe)
│   ├── tests/               # Unit + integration tests
│   └── main.py              # FastAPI application entry point
├── frontend/
│   ├── src/
│   │   ├── components/      # QueryForm, AgentPipeline, ResearchResultPanel
│   │   ├── hooks/           # useResearchWebSocket
│   │   ├── pages/           # ResearchPage, HistoryPage
│   │   ├── types/           # TypeScript types
│   │   └── utils/           # Axios API client, helpers
│   ├── index.html
│   ├── tailwind.config.js
│   └── vite.config.ts
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── sample_data/             # Bundled documents auto-loaded on first startup
├── .github/workflows/       # CI/CD pipeline
├── .env.example             # Copy to .env and fill in your keys
├── run_backend.ps1          # One-click backend launcher (Windows PowerShell)
├── run_frontend.ps1         # One-click frontend launcher (Windows PowerShell)
├── docker-compose.yml       # Full stack (Postgres + Redis + Neo4j + backend + frontend)
└── README.md
```

---

## Docker (Full Stack)

```bash
cp .env.example .env
# Fill in OPENROUTER_API_KEY, POSTGRES_PASSWORD, NEO4J_PASSWORD, SECRET_KEY

docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000/docs |
| Neo4j Browser | http://localhost:7474 |

---

## Deployment (Render)

The repo includes a [`render.yaml`](render.yaml) Blueprint manifest.

**One-click deploy:** click the button at the top of this README.

Or manually:
1. Go to [dashboard.render.com](https://dashboard.render.com) → **New → Blueprint**
2. Connect your fork of this repo — Render finds `render.yaml` automatically
3. In the Render dashboard set two secrets:
   - `agentforge-backend` → `OPENROUTER_API_KEY` — your `sk-or-v1-...` key ([get one free](https://openrouter.ai/keys))
   - `agentforge-backend` → `SECRET_KEY` — any 64-char random string
4. Click **Manual Deploy → Deploy latest commit**

The backend cold-starts in ~30–60 s on the first request after idle. Both services run on Render's **free tier** — no credit card needed.

---

## Key Design Decisions

**Why LangGraph?**
StateGraph with conditional edges gives explicit control over the retry loop (Critic → Researcher). A plain chain can't route dynamically based on a quality score.

**Why OpenRouter for embeddings?**
OpenRouter provides an OpenAI-compatible API for both LLM calls and embeddings with the same key, keeping deployment to a single secret. Locally, `sentence-transformers/all-MiniLM-L6-v2` can be used for zero-cost dev (`EMBEDDING_PROVIDER=local`).

**Why asyncio.create_task() instead of ThreadPoolExecutor?**
The OpenAI SDK v2 calls `asyncio.to_thread()` on first request. Running the pipeline in a thread with its own `asyncio.run()` loop caused `RuntimeError: cannot schedule new futures after interpreter shutdown`. Using `create_task()` keeps everything on the Uvicorn event loop — all I/O-bound LLM calls yield naturally without blocking.

---

## License

MIT © 2024 — free to use for portfolio and learning purposes.
