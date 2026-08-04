# API Documentation – AgentForge

## Base URL
```
http://localhost:8000
```
API version prefix: `/api/v1`

Interactive docs (Swagger UI): `http://localhost:8000/docs`
OpenAPI schema: `http://localhost:8000/openapi.json`

---

## Authentication

AgentForge uses **JWT Bearer tokens**.

### Flow
1. Register a new account → `POST /api/v1/auth/register`
2. Login to receive a token → `POST /api/v1/auth/token`
3. Pass the token on protected endpoints → `Authorization: Bearer <token>`

In Swagger UI: click the **🔒 Authorize** button, paste your token, and all subsequent "Try it out" requests will include the header automatically.

---

## Auth API

### POST `/api/v1/auth/register`
**Create a new user account**

> No authentication required.

Request body:
```json
{
  "email": "alice@example.com",
  "password": "mysecurepassword"
}
```

Constraints:
- `email` – valid email address
- `password` – minimum 8 characters

Response `201 Created`:
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "alice@example.com",
  "message": "Account created."
}
```

Error responses:
- `409 Conflict` – email already registered
- `422 Unprocessable Entity` – validation failure (password too short, invalid email)

---

### POST `/api/v1/auth/token`
**Login — obtain a JWT bearer token**

> No authentication required.

Request body:
```json
{
  "email": "alice@example.com",
  "password": "mysecurepassword"
}
```

Response `200 OK`:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

Error responses:
- `401 Unauthorized` – incorrect email or password (same message for both — no account enumeration)

---

## Research API

> **All research endpoints require authentication.**
> Include `Authorization: Bearer <token>` on every request.

### POST `/api/v1/research`
**Submit a new research query**

Request body:
```json
{
  "query": "What are the latest advances in quantum computing?",
  "context": "Focus on hardware developments in 2024",
  "top_k": 5
}
```

Constraints:
- `query` – minimum 5 characters

Response `202 Accepted`:
```json
{
  "session_id": "3f7a2c1d-...",
  "status": "running",
  "message": "Research pipeline started. Connect to /ws/{session_id} for live updates."
}
```

---

### GET `/api/v1/research/{session_id}`
**Poll session status**

Response `200 OK`:
```json
{
  "id": "3f7a2c1d-...",
  "user_id": "550e8400-...",
  "query": "What are the latest advances in quantum computing?",
  "status": "completed",
  "final_answer": "# Quantum Computing Advances\n...",
  "critic_score": 0.87,
  "iterations": 1,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:31:23Z"
}
```

Status values: `pending` | `running` | `completed` | `failed`

---

### GET `/api/v1/research/{session_id}/runs`
**Get all agent run records for a session**

Response `200 OK`:
```json
[
  {
    "id": "abc123-...",
    "session_id": "3f7a2c1d-...",
    "agent_name": "researcher",
    "status": "completed",
    "execution_time_ms": 3240,
    "tokens_used": null,
    "error_message": null,
    "created_at": "2024-01-15T10:30:01Z"
  }
]
```

---

### GET `/api/v1/research`
**List the authenticated user's sessions**

Query params:
- `limit` – default `20`
- `offset` – default `0`

Response `200 OK`: array of session objects (same schema as GET by ID).

Error: `401 Unauthorized` if no valid token provided.

---

## Document API

### POST `/api/v1/documents`
**Ingest a document into the knowledge base**

```json
{
  "title": "Quantum Computing Overview",
  "source": "https://example.com/qc.html",
  "content": "Quantum computers use qubits...",
  "metadata": {"category": "science", "year": 2024}
}
```

Response `201 Created`:
```json
{
  "document_id": "d1e2f3...",
  "chunks_created": 3,
  "faiss_indexed": true,
  "message": "Ingested 3 chunks, indexed 3 vectors."
}
```

---

### GET `/api/v1/documents/stats`
**Vector store statistics**

```json
{
  "total_vectors": 156,
  "dimension": 384,
  "index_type": "IndexIDMap",
  "index_path": "./vectorstore/faiss_index/index.faiss"
}
```

---

### POST `/api/v1/documents/load-sample`
**Load bundled sample documents into the knowledge base**

Response `200 OK`:
```json
{
  "message": "Loaded N documents from sample_data/",
  "total_chunks": 42
}
```

---

## WebSocket API

### `ws://localhost:8000/ws/{session_id}`

Connect immediately after submitting a research query to receive real-time agent updates.

**Incoming message types:**

`agent_status` – Fired when an agent starts or completes:
```json
{
  "type": "agent_status",
  "session_id": "3f7a2c1d-...",
  "agent_name": "researcher",
  "status": "running",
  "message": "Agent researcher is running",
  "timestamp": "2024-01-15T10:30:05Z"
}
```

`stream_chunk` – Incremental output during LLM streaming:
```json
{
  "type": "stream_chunk",
  "data": "partial text..."
}
```

`final_result` – Fired when the pipeline completes:
```json
{
  "type": "final_result",
  "data": {
    "session_id": "3f7a2c1d-...",
    "final_answer": "# Answer\n...",
    "critic_score": 0.87,
    "iterations": 1,
    "sources": [],
    "execution_time_ms": 52340
  }
}
```

`error` – Fired if the pipeline fails:
```json
{
  "type": "error",
  "message": "Agent researcher failed: network timeout after 120s"
}
```

**Keep-alive:** Send `"ping"` → receive `{"type": "pong"}`

---

## Health API

### GET `/health`
Liveness probe — always `200` if process is running.

```json
{"status": "ok"}
```

### GET `/health/ready`
Readiness probe — checks all downstream services.

```json
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "development",
  "services": {
    "postgres": "ok",
    "redis": "ok",
    "neo4j": "ok",
    "faiss": "ok"
  }
}
```

---

## Error Format

All errors return a consistent envelope:
```json
{
  "error": {
    "code": "AGENT_EXECUTION_ERROR",
    "message": "Agent 'researcher' failed: timed out after 120s",
    "details": {"agent": "researcher"},
    "path": "/api/v1/research"
  }
}
```

Common error codes: `AUTH_ERROR`, `AGENT_EXECUTION_ERROR`, `VALIDATION_ERROR`, `NOT_FOUND`
