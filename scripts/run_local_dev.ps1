#!/usr/bin/env pwsh
Set-StrictMode -Version Latest

# One-click local dev bootstrap + runner for Windows PowerShell
# Usage: Run this from the `agentforge` folder (double-click or run in PowerShell):
#   .\scripts\run_local_dev.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$AgentDir = Split-Path -Parent $ScriptDir
$ProjectRoot = Split-Path -Parent $AgentDir

Write-Host "AgentForge local runner — agent dir: $AgentDir"

# Create venv if missing
$VenvPath = Join-Path $AgentDir ".venv"
if (-not (Test-Path $VenvPath)) {
    Write-Host "Creating virtual environment..."
    python -m venv $VenvPath
}

# Activate then install backend deps
Write-Host "Installing backend dependencies (if needed)..."
. "$VenvPath\Scripts\Activate.ps1"
pip install -q -r "$AgentDir\backend\requirements-local.txt"

# Frontend deps
$FrontendDir = Join-Path $AgentDir "frontend"
if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Host "Installing frontend dependencies..."
    Push-Location $FrontendDir
    npm ci
    Pop-Location
}

# Ensure logs dir
$LogsDir = Join-Path $AgentDir "logs"
New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null

Write-Host "Starting backend and frontend in new windows..."

# Start backend in new PowerShell window
$backendCmd = "cd `"$AgentDir`"; `$env:PYTHONPATH='$ProjectRoot'; .\ .venv\Scripts\Activate.ps1; python -m uvicorn agentforge.backend.main:app --host 0.0.0.0 --port 8000 --reload --log-level info > `"$LogsDir\backend.log`" 2>&1"
Start-Process -FilePath powershell -ArgumentList '-NoExit','-Command',$backendCmd

# Start frontend in new PowerShell window
$frontendCmd = "cd `"$FrontendDir`"; npm run dev > `"$LogsDir\frontend.log`" 2>&1"
Start-Process -FilePath powershell -ArgumentList '-NoExit','-Command',$frontendCmd

Write-Host "Done. Backend: http://localhost:8000   Frontend: http://localhost:3000"
Write-Host "Logs: $LogsDir\backend.log, $LogsDir\frontend.log"
