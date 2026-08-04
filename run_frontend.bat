@echo off
REM AgentForge – Frontend Dev Server Launcher
REM Run this in a SEPARATE terminal from run_backend.bat

echo.
echo  ====================================================
echo   AgentForge – Frontend Dev Server
echo  ====================================================
echo.

cd frontend

REM ── Check Node.js ─────────────────────────────────────────────────────────────
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install from https://nodejs.org
    pause & exit /b 1
)

REM ── Install packages if node_modules missing ──────────────────────────────────
if not exist "node_modules" (
    echo [1/2] Installing npm packages (first run takes 1-2 minutes)...
    npm install --legacy-peer-deps
)

REM ── Start Vite dev server ─────────────────────────────────────────────────────
echo [2/2] Starting frontend dev server...
echo.
echo  Frontend: http://localhost:3000
echo  Backend:  http://localhost:8000  (must be running separately)
echo  Press Ctrl+C to stop.
echo.

npm run dev
