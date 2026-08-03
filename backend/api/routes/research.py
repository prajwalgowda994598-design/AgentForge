"""
AgentForge – Research API Routes
====================================
REST endpoints for triggering and monitoring research workflows.

POST /research          – Submit a new research query (async)
GET  /research/{id}     – Poll session status
GET  /research/{id}/runs – Get all agent run records for a session
GET  /sessions          – List recent sessions for the current user
"""

import asyncio
import concurrent.futures
import time
import traceback
import uuid
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.backend.core.dependencies import get_current_user, get_db, get_optional_user
from agentforge.backend.core.exceptions import NotFoundError
from agentforge.backend.core.logging import get_logger
from agentforge.backend.database.models import AgentRun, ResearchSession
from agentforge.backend.graph.workflow import run_research_workflow
from agentforge.backend.models.schemas import (
    AgentRunSchema,
    ResearchQueryRequest,
    ResearchQueryResponse,
    ResearchSessionSchema,
)
from agentforge.backend.services.audit_service import AuditService
from agentforge.backend.services.redis_service import CacheService, get_redis_client
from agentforge.backend.services.websocket_manager import ws_manager

router = APIRouter(prefix="/research", tags=["research"])
logger = get_logger(__name__)


# ── Thread pool for heavy pipeline work ───────────────────────────────────────
# The research pipeline (LLM calls + embeddings + web search) is CPU and I/O
# bound in ways that block the asyncio event loop even with run_in_executor,
# because LangChain's internals use synchronous httpx internally.
# Running the whole pipeline in its own OS thread with its own event loop
# keeps the Uvicorn event loop free for polling and other requests.
_PIPELINE_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=4, thread_name_prefix="pipeline"
)


def _run_pipeline_in_thread(session_id: str, query: str, top_k: int, user_id):
    """Entry point for the pipeline thread — runs its own asyncio event loop."""
    asyncio.run(_run_workflow_background(session_id, query, top_k, user_id))


# ── Background Task ────────────────────────────────────────────────────────────

async def _run_workflow_background(
    session_id: str,
    query: str,
    top_k: int,
    user_id: Optional[str],
) -> None:
    """
    Execute the research workflow in the background.
    Updates the ResearchSession row on completion or failure.
    Broadcasts agent status updates via WebSockets.
    """
    from agentforge.backend.database.session import AsyncSessionLocal

    start_ms = int(time.time() * 1000)

    async def status_callback(session_id: str, agent_name: str, status: str):
        await ws_manager.broadcast_agent_status(session_id, agent_name, status)

    try:
        final_state = await run_research_workflow(
            query=query,
            session_id=session_id,
            top_k=top_k,
            user_id=user_id,
            status_callback=status_callback,
        )

        elapsed_ms = int(time.time() * 1000) - start_ms

        async with AsyncSessionLocal() as db:
            # SQLite stores UUID as str; PostgreSQL stores as UUID obj.
            # Query with both forms so it works on both backends.
            _sid_uuid = uuid.UUID(session_id)
            result = await db.execute(
                select(ResearchSession).where(ResearchSession.id == _sid_uuid)
            )
            session_obj = result.scalar_one_or_none()
            if session_obj:
                session_obj.status = "completed"
                session_obj.final_answer = final_state.get("final_answer")
                session_obj.critic_score = final_state.get("critic_score")
                session_obj.iterations = final_state.get("iteration", 0)
                from datetime import datetime, timezone
                session_obj.completed_at = datetime.now(timezone.utc)
                await db.commit()

            # Log individual agent runs
            for agent_name, timing_ms in final_state.get("agent_timings", {}).items():
                a_status = final_state.get("agent_status", {}).get(agent_name, "completed")
                run = AgentRun(
                    session_id=_sid_uuid,
                    agent_name=agent_name,
                    status=a_status,
                    execution_time_ms=timing_ms,
                    output_data={
                        "summary_length": len(final_state.get("summary", "")),
                        "critic_score": final_state.get("critic_score"),
                    },
                )
                db.add(run)
            await db.commit()

        await ws_manager.broadcast_final_result(
            session_id,
            {
                "session_id": session_id,
                "final_answer": final_state.get("final_answer"),
                "critic_score": final_state.get("critic_score"),
                "iterations": final_state.get("iteration"),
                "sources": final_state.get("sources", []),
                "execution_time_ms": elapsed_ms,
            },
        )

    except Exception as exc:
        # ── Full traceback so we can see exactly what went wrong ──────────────
        tb = traceback.format_exc()
        error_type = type(exc).__name__
        # Build a concise human-readable message (strip internal class paths).
        raw_msg = str(exc)
        # AgentExecutionError messages already contain the agent name and reason;
        # for network errors surface just the error type + short message.
        if "ConnectError" in error_type or "Connection" in error_type or "Timeout" in error_type:
            error_detail = f"Network error ({error_type}): could not reach upstream service. {raw_msg[:200]}"
        else:
            error_detail = f"{error_type}: {raw_msg[:500]}"

        logger.error(
            "background_workflow_failed",
            session_id=session_id,
            error=error_detail,
            error_type=error_type,
            traceback=tb,
        )
        # Also print directly to stdout so it appears in the terminal window
        print(f"\n{'='*60}")
        print(f"[AgentForge] PIPELINE FAILED  session={session_id}")
        print(f"Error type : {error_type}")
        print(f"Error msg  : {error_detail}")
        print(f"Traceback  :\n{tb}")
        print(f"{'='*60}\n")
        try:
            async with AsyncSessionLocal() as db:
                _sid_uuid = uuid.UUID(session_id)
                result = await db.execute(
                    select(ResearchSession).where(ResearchSession.id == _sid_uuid)
                )
                session_obj = result.scalar_one_or_none()
                if session_obj:
                    session_obj.status = "failed"
                    # Store the error message in metadata so GET /research/{id} shows it
                    session_obj.metadata_ = {
                        **(session_obj.metadata_ or {}),
                        "error": error_detail,
                        "traceback": tb,
                    }
                    await db.commit()
        except Exception as db_exc:
            logger.warning("background_error_db_update_failed", error=str(db_exc))
        await ws_manager.broadcast_error(session_id, error_detail)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a research query",
    description=(
        "Starts the multi-agent research pipeline asynchronously. "
        "Connect to the WebSocket endpoint to receive real-time updates."
    ),
)
async def submit_research(
    body: ResearchQueryRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: Optional[dict] = Depends(get_optional_user),
):
    # Check cache first
    import hashlib
    query_hash = hashlib.sha256(body.query.encode()).hexdigest()
    redis = await get_redis_client()
    cache = CacheService(redis)
    cached = await cache.get_cached_research(query_hash)
    if cached:
        logger.info("research_cache_hit", query_hash=query_hash[:12])
        return {
            "session_id": cached.get("session_id"),
            "status": "completed",
            "cached": True,
            "message": "Result retrieved from cache.",
        }

    # Create session record
    session_id = str(uuid.uuid4())
    session = ResearchSession(
        id=uuid.UUID(session_id),
        user_id=user["user_id"] if user else None,
        query=body.query,
        status="running",
        metadata_={"top_k": body.top_k, "context": body.context},
    )
    db.add(session)

    audit = AuditService(db)
    await audit.log(
        event_type="research.submitted",
        actor=user["user_id"] if user else "anonymous",
        session_id=uuid.UUID(session_id),
        payload={"query": body.query[:200]},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    # Submit pipeline to a dedicated thread pool so it runs in its own
    # event loop and never blocks Uvicorn's event loop.
    # BackgroundTasks is only used to register the fire-and-forget call.
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        _PIPELINE_EXECUTOR,
        _run_pipeline_in_thread,
        session_id,
        body.query,
        body.top_k,
        user["user_id"] if user else None,
    )

    return {
        "session_id": session_id,
        "status": "running",
        "message": "Research pipeline started. Connect to /ws/{session_id} for live updates.",
    }


@router.get(
    "/{session_id}",
    response_model=ResearchSessionSchema,
    summary="Get session status",
)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ResearchSession).where(ResearchSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError("ResearchSession", session_id)
    return session


@router.get(
    "/{session_id}/runs",
    response_model=List[AgentRunSchema],
    summary="Get agent run records for a session",
)
async def get_agent_runs(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.session_id == session_id)
        .order_by(AgentRun.created_at)
    )
    return result.scalars().all()


@router.get(
    "",
    response_model=List[ResearchSessionSchema],
    summary="List recent sessions",
)
async def list_sessions(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(ResearchSession)
        .where(ResearchSession.user_id == user["user_id"])
        .order_by(desc(ResearchSession.created_at))
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()
