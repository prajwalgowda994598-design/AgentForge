@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM AgentForge – One-click local startup (No Docker required)
REM Run this file from inside the agentforge\ folder.
REM ─────────────────────────────────────────────────────────────────────────────

echo.
echo  ====================================================
echo   AgentForge – Local Dev Startup
echo   No Docker, No PostgreSQL, No Redis, No Neo4j needed
echo  ====================================================
echo.

REM ── Check Python ──────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ from https://python.org
    pause & exit /b 1
)

REM ── Create virtual environment if missing ─────────────────────────────────────
if not exist ".venv\Scripts\activate.bat" (
    echo [1/4] Creating virtual environment...
    python -m venv .venv
)

REM ── Activate virtual environment ──────────────────────────────────────────────
echo [2/4] Activating virtual environment...
call .venv\Scripts\activate.bat

REM ── Install backend dependencies ──────────────────────────────────────────────
echo [3/4] Installing backend dependencies (first run takes 3-5 minutes)...
pip install -q -r backend\requirements-local.txt
echo      Note: sentence-transformers may take a few extra minutes on first install.

REM ── Set PYTHONPATH so Python can find the agentforge package ──────────────────
echo [4/4] Configuring local dev environment...
REM %~dp0 is the agentforge\ folder. One level up is Project01\ (the package root).
REM We resolve the absolute path of the parent directory so imports work from anywhere.
for %%I in ("%~dp0..") do set "PYTHONPATH=%%~fI"
set LOCAL_DEV=true
set ENVIRONMENT=development
set APP_DEBUG=true
set LOG_JSON=false
set FAISS_INDEX_PATH=./vectorstore/faiss_index
set SECRET_KEY=local-dev-secret-key-change-in-production
set LLM_PROVIDER=openrouter
set OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
set OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
set OPENROUTER_SITE_URL=http://localhost:3000
set OPENROUTER_SITE_NAME=AgentForge
set EMBEDDING_PROVIDER=local

setlocal enabledelayedexpansion
REM ── Load .env file if present ─────────────────────────────────────────────────
if exist ".env" (
    echo      Loading .env file...
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        if not "%%A"=="" if not "%%A:~0,1%"=="#" (
            set "VALUE=%%B"
            for /f "delims=#" %%C in ("!VALUE!") do set "VALUE=%%C"
            set "%%A=!VALUE!"
        )
    )
)

REM ── Check OpenRouter key ──────────────────────────────────────────────────────
if "%OPENROUTER_API_KEY%"=="" (
    echo.
    echo [WARNING] OPENROUTER_API_KEY is not set!
    echo.
    echo   Steps to get a FREE key:
    echo     1. Go to https://openrouter.ai
    echo     2. Sign up (no credit card needed)
    echo     3. Go to https://openrouter.ai/keys
    echo     4. Click "Create Key"  - copy the sk-or-v1-... value
    echo     5. Open your .env file and set:
    echo        OPENROUTER_API_KEY=sk-or-v1-your-key-here
    echo.
    echo   The server will start but agents will fail without a valid key.
    echo   Press any key to continue anyway or Ctrl+C to cancel.
    pause >nul
)

REM ── Start backend ─────────────────────────────────────────────────────────────
echo.
echo  Starting AgentForge backend...
echo  API:    http://localhost:8000
echo  Docs:   http://localhost:8000/docs
echo  Press Ctrl+C to stop.
echo.

python -m uvicorn agentforge.backend.main:app --host 0.0.0.0 --port 8000 --reload --log-level info

pause
