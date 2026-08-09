# AgentForge - Frontend Dev Server (PowerShell)
# Usage:  .\run_frontend.ps1
# Run this in a SEPARATE terminal from run_backend.ps1

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $here "frontend")

Write-Host ""
Write-Host " ====================================================" -ForegroundColor Cyan
Write-Host "  AgentForge - Frontend Dev Server" -ForegroundColor Cyan
Write-Host " ====================================================" -ForegroundColor Cyan
Write-Host ""

# Check Node.js
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Node.js not found. Install from https://nodejs.org" -ForegroundColor Red
    exit 1
}

# Install packages on first run
if (-not (Test-Path "node_modules")) {
    Write-Host "[1/2] Installing npm packages (first run: 1-2 min)..." -ForegroundColor Yellow
    npm install --legacy-peer-deps
}

Write-Host "[2/2] Starting Vite dev server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Frontend : http://localhost:3000" -ForegroundColor Green
Write-Host "  Backend  : http://localhost:8000  (must be running in another terminal)" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop." -ForegroundColor Green
Write-Host ""

npm run dev
