#!/usr/bin/env bash
set -euo pipefail

# One-click local dev bootstrap + runner for macOS / Linux
# Usage: run from the `agentforge` folder:
#   ./scripts/run_local_dev.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$AGENT_DIR")"

echo "AgentForge local runner — agent dir: $AGENT_DIR"

# Create venv if missing
if [ ! -d "$AGENT_DIR/.venv" ]; then
  python3 -m venv "$AGENT_DIR/.venv"
fi

echo "Installing backend dependencies (if needed)..."
# shellcheck disable=SC1090
. "$AGENT_DIR/.venv/bin/activate"
pip install -q -r "$AGENT_DIR/backend/requirements-local.txt"

echo "Installing frontend dependencies (if needed)..."
if [ ! -d "$AGENT_DIR/frontend/node_modules" ]; then
  (cd "$AGENT_DIR/frontend" && npm ci)
fi

mkdir -p "$AGENT_DIR/logs"

echo "Starting backend and frontend (logs -> $AGENT_DIR/logs)..."

# Start backend in background
PYTHONPATH="$PROJECT_ROOT" "$AGENT_DIR/.venv/bin/python" -m uvicorn agentforge.backend.main:app --host 0.0.0.0 --port 8000 --reload --log-level info > "$AGENT_DIR/logs/backend.log" 2>&1 &

# Start frontend in background
(cd "$AGENT_DIR/frontend" && npm run dev > "$AGENT_DIR/logs/frontend.log" 2>&1 &) 

echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000 (or 5173)"
echo "Tail backend logs with: tail -f $AGENT_DIR/logs/backend.log"
