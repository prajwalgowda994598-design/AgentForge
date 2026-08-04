"""
AgentForge – WebSocket Connection Manager
==========================================
Manages all active WebSocket connections.
Agents broadcast live status events through this manager during graph execution.

Connections are keyed by session_id, allowing targeted broadcasts.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

from agentforge.backend.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """
    Thread-safe WebSocket connection registry.

    Sessions map: session_id → set of active WebSocket connections.
    A session can have multiple browser tabs connected simultaneously.
    """

    def __init__(self):
        # session_id → set of WebSocket objects
        self._connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Accept a new WebSocket connection and register it."""
        await websocket.accept()
        if session_id not in self._connections:
            self._connections[session_id] = set()
        self._connections[session_id].add(websocket)
        logger.info("ws_connected", session_id=session_id, total=len(self._connections))

    def disconnect(self, websocket: WebSocket, session_id: str) -> None:
        """Remove a WebSocket from the registry."""
        if session_id in self._connections:
            self._connections[session_id].discard(websocket)
            if not self._connections[session_id]:
                del self._connections[session_id]
        logger.info("ws_disconnected", session_id=session_id)

    async def send_to_session(
        self, session_id: str, message: Dict[str, Any]
    ) -> None:
        """Broadcast a JSON message to all connections for a session."""
        if session_id not in self._connections:
            return

        dead: Set[WebSocket] = set()
        payload = json.dumps(message, default=str)

        for ws in self._connections[session_id].copy():
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)

        # Clean up dead connections
        for ws in dead:
            self._connections[session_id].discard(ws)

    async def broadcast_agent_status(
        self,
        session_id: str,
        agent_name: str,
        status: str,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send a typed agent-status event to the frontend."""
        await self.send_to_session(
            session_id,
            {
                "type": "agent_status",
                "session_id": session_id,
                "agent_name": agent_name,
                "status": status,
                "message": message or f"Agent {agent_name} is {status}",
                "metadata": metadata or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def broadcast_stream_chunk(
        self, session_id: str, chunk: str
    ) -> None:
        """Send a text streaming chunk."""
        await self.send_to_session(
            session_id,
            {"type": "stream_chunk", "content": chunk},
        )

    async def broadcast_final_result(
        self, session_id: str, result: Dict[str, Any]
    ) -> None:
        """Send the completed research result."""
        await self.send_to_session(
            session_id,
            {"type": "final_result", "data": result},
        )

    async def broadcast_error(
        self, session_id: str, error: str
    ) -> None:
        """Send an error event."""
        await self.send_to_session(
            session_id,
            {"type": "error", "message": error},
        )

    @property
    def active_sessions(self) -> int:
        return len(self._connections)


# Module-level singleton
ws_manager = ConnectionManager()
