# TerraShield AI - Local Backend Startup Script (Windows PowerShell)
# Starts FastAPI uvicorn server on http://127.0.0.1:8000

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "  TerraShield AI - FastAPI Backend Service Launcher" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# 1. Virtual Environment Validation
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$VenvUvicorn = Join-Path $ProjectRoot ".venv\Scripts\uvicorn.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[ERROR] Virtual environment (.venv) was not found in: $ProjectRoot" -ForegroundColor Red
    Write-Host "Please set up the environment with:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv" -ForegroundColor White
    Write-Host "  .venv\Scripts\pip install -r requirements.txt" -ForegroundColor White
    exit 1
}

# 2. Dependency Health Check
& $VenvPython -c "import fastapi, uvicorn, shapely, tifffile, numpy" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Core backend dependencies are missing in .venv." -ForegroundColor Red
    Write-Host "Please install required packages using:" -ForegroundColor Yellow
    Write-Host "  .venv\Scripts\pip install -r requirements.txt" -ForegroundColor White
    exit 1
}

# 3. Start Backend Server
Write-Host "[OK] Environment verified. Starting backend server on http://127.0.0.1:8000..." -ForegroundColor Green
Write-Host "API Interactive Documentation: http://127.0.0.1:8000/docs" -ForegroundColor Gray
Write-Host "Press Ctrl+C to terminate the process." -ForegroundColor Gray
Write-Host ""

& $VenvPython -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
exit $LASTEXITCODE
