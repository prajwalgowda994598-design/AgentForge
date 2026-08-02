"""
AgentForge – WebSocket Route
================================
Provides a persistent WebSocket endpoint so the React frontend can
receive real-time agent status events and streaming text.

WS /ws/{session_id}
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from agentforge.backend.core.logging import get_logger
from agentforge.backend.services.websocket_manager import ws_manager

router = APIRouter(tags=["websocket"])
logger = get_logger(__name__)


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket connection for a specific research session.
    The client connects before or immediately after submitting a query.
    The server pushes:
      • agent_status  – when each agent starts/completes
      • stream_chunk  – incremental text tokens (future enhancement)
      • final_result  – completed answer payload
      • error         – if the pipeline fails
    """
    await ws_manager.connect(websocket, session_id)
    logger.info("ws_session_opened", session_id=session_id)

    try:
        # Keep connection alive; listen for client-side pings or disconnects
        while True:
            data = await websocket.receive_text()
            # Echo ping/pong to keep connection alive
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        logger.info("ws_session_closed", session_id=session_id)
    finally:
        ws_manager.disconnect(websocket, session_id)
