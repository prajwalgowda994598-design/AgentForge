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
for %%I in ("%~dp0..") do set "PYTHONPATH=%%~fI"

REM ── Hard defaults (overridden by .env when present) ───────────────────────────
set LOCAL_DEV=true
set ENVIRONMENT=development
set APP_DEBUG=true
set LOG_JSON=false
set FAISS_INDEX_PATH=./vectorstore/faiss_index
set FAISS_DIMENSION=384
set SECRET_KEY=local-dev-secret-key-change-in-production
set LLM_PROVIDER=openrouter
set OPENROUTER_MODEL=nvidia/nemotron-3-super-120b-a12b:free
set OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
set OPENROUTER_SITE_URL=http://localhost:3000
set OPENROUTER_SITE_NAME=AgentForge
set EMBEDDING_PROVIDER=local

REM ── Load .env via helper script ───────────────────────────────────────────────
REM   _load_env.py writes SET "KEY=VALUE" lines to a temp .bat.
REM   We then read each line with for /f "tokens=1* delims= " to execute SET
REM   directly in this process (CALL would set vars in a child scope only).
if exist ".env" (
    echo      Loading .env file...
    for /f "usebackq delims=" %%P in (`python "%~dp0_load_env.py" ".env" 2^>nul`) do set "_ENVBAT=%%P"
    if defined _ENVBAT (
        if exist "%_ENVBAT%" (
            for /f "usebackq tokens=*" %%L in ("%_ENVBAT%") do %%L
            del "%_ENVBAT%" >nul 2>&1
        )
    )
    echo      .env loaded.
)

REM ── Check OpenRouter key ──────────────────────────────────────────────────────
if "%OPENROUTER_API_KEY%"=="" (
    echo.
    echo [WARNING] OPENROUTER_API_KEY is not set!
    echo.
    echo   Steps to get a FREE key (no credit card):
    echo     1. Go to  https://openrouter.ai
    echo     2. Sign up
    echo     3. Go to  https://openrouter.ai/keys
    echo     4. Click "Create Key"  and copy the sk-or-v1-... value
    echo     5. Open your .env file and add:
    echo        OPENROUTER_API_KEY=sk-or-v1-your-key-here
    echo.
    echo   The server will start but agent queries will fail without a valid key.
    echo   Press any key to continue anyway or Ctrl+C to cancel.
    pause >nul
)

echo.
echo  Active configuration:
echo    LLM_PROVIDER      = %LLM_PROVIDER%
echo    OPENROUTER_MODEL  = %OPENROUTER_MODEL%
echo    EMBEDDING_PROVIDER= %EMBEDDING_PROVIDER%
echo    LOCAL_DEV         = %LOCAL_DEV%
echo.

REM ── Start backend ─────────────────────────────────────────────────────────────
echo  Starting AgentForge backend...
echo  API:    http://localhost:8000
echo  Docs:   http://localhost:8000/docs
echo  Press Ctrl+C to stop.
echo.

python -m uvicorn agentforge.backend.main:app --host 0.0.0.0 --port 8000 --reload --log-level info

pause
