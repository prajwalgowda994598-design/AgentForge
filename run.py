"""
run.py  -  launch the AgentForge backend from the project root.

Usage:
    python run.py              # production mode
    python run.py --reload     # dev mode with auto-reload
"""

import os
import sys
from pathlib import Path

# Guarantee the project root is on sys.path so backend imports resolve.
ROOT = Path(__file__).parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn

if __name__ == "__main__":
    reload = "--reload" in sys.argv

    port = 8000
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    elif os.environ.get("PORT"):
        port = int(os.environ["PORT"])

    host = "127.0.0.1"
    if "--host" in sys.argv:
        host = sys.argv[sys.argv.index("--host") + 1]

    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=reload,
        reload_dirs=[str(ROOT)] if reload else None,
    )
