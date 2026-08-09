# AgentForge – Backend launcher (PowerShell)
# Usage:  .\run_backend.ps1
# Requires: Python 3.10+  (no Docker, no PostgreSQL, no Redis, no Neo4j)

Set-StrictMode -Off
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

Write-Host ""
Write-Host " ====================================================" -ForegroundColor Cyan
Write-Host "  AgentForge - Local Dev Startup" -ForegroundColor Cyan
Write-Host "  No Docker / PostgreSQL / Redis / Neo4j needed" -ForegroundColor Cyan
Write-Host " ====================================================" -ForegroundColor Cyan
Write-Host ""

# ── Check Python ──────────────────────────────────────────────────────────────
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python not found. Install Python 3.10+ from https://python.org" -ForegroundColor Red
    exit 1
}

# ── Virtual environment ───────────────────────────────────────────────────────
$venvActivate = Join-Path $here ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvActivate)) {
    Write-Host "[1/4] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

Write-Host "[2/4] Activating virtual environment..." -ForegroundColor Yellow
& $venvActivate

# ── Install dependencies ──────────────────────────────────────────────────────
Write-Host "[3/4] Installing backend dependencies (first run: 3-5 min)..." -ForegroundColor Yellow
pip install -q -r backend\requirements-local.txt

# ── Environment setup ─────────────────────────────────────────────────────────
Write-Host "[4/4] Configuring environment..." -ForegroundColor Yellow

# PYTHONPATH = Project01\ (parent of agentforge\) so 'agentforge' is importable
$env:PYTHONPATH = (Resolve-Path (Join-Path $here "..")).Path

# Hard defaults
$env:LOCAL_DEV              = "true"
$env:ENVIRONMENT            = "development"
$env:APP_DEBUG              = "true"
$env:LOG_JSON               = "false"
$env:FAISS_INDEX_PATH       = "./vectorstore/faiss_index"
$env:FAISS_DIMENSION        = "384"
$env:SECRET_KEY             = "local-dev-secret-key-change-in-production"
$env:LLM_PROVIDER           = "openrouter"
$env:OPENROUTER_MODEL       = "nvidia/nemotron-3-super-120b-a12b:free"
$env:OPENROUTER_BASE_URL    = "https://openrouter.ai/api/v1"
$env:OPENROUTER_SITE_URL    = "http://localhost:3000"
$env:OPENROUTER_SITE_NAME   = "AgentForge"
$env:EMBEDDING_PROVIDER     = "local"

# Load .env — override defaults with anything defined there
$envFile = Join-Path $here ".env"
if (Test-Path $envFile) {
    Write-Host "     Loading .env ..." -ForegroundColor DarkGray
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        # Skip blank lines and comments
        if ($line -eq '' -or $line.StartsWith('#')) { return }
        # Match KEY=VALUE
        if ($line -match '^([A-Za-z_]\w*)\s*=\s*(.*)$') {
            $key = $Matches[1]
            $val = $Matches[2]
            # Strip inline comment
            $val = ($val -split '#')[0].Trim()
            # Strip surrounding quotes
            if ($val.Length -ge 2 -and $val[0] -eq $val[-1] -and $val[0] -in '"',"'") {
                $val = $val.Substring(1, $val.Length - 2)
            }
            [System.Environment]::SetEnvironmentVariable($key, $val, 'Process')
        }
    }
    Write-Host "     .env loaded." -ForegroundColor DarkGray
}

# ── Key check ─────────────────────────────────────────────────────────────────
if (-not $env:OPENROUTER_API_KEY) {
    Write-Host ""
    Write-Host "[WARNING] OPENROUTER_API_KEY is not set!" -ForegroundColor Yellow
    Write-Host "  1. Sign up at https://openrouter.ai" -ForegroundColor Yellow
    Write-Host "  2. Create a key at https://openrouter.ai/keys" -ForegroundColor Yellow
    Write-Host "  3. Add to agentforge\.env:  OPENROUTER_API_KEY=sk-or-v1-..." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to continue anyway (queries will fail), or Ctrl+C to cancel"
}

Write-Host ""
Write-Host "  LLM_PROVIDER      = $env:LLM_PROVIDER"
Write-Host "  OPENROUTER_MODEL  = $env:OPENROUTER_MODEL"
Write-Host "  EMBEDDING_PROVIDER= $env:EMBEDDING_PROVIDER"
Write-Host "  LOCAL_DEV         = $env:LOCAL_DEV"
Write-Host ""
Write-Host " Starting AgentForge backend..." -ForegroundColor Green
Write-Host " API:  http://localhost:8000" -ForegroundColor Green
Write-Host " Docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host " Press Ctrl+C to stop." -ForegroundColor Green
Write-Host ""

python -m uvicorn agentforge.backend.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
