# TerraShield AI - Local Frontend Startup Script (Windows PowerShell)
# Starts Streamlit geospatial dashboard on http://127.0.0.1:8501

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "  TerraShield AI - Streamlit Frontend Dashboard" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# 1. Virtual Environment Validation
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$VenvStreamlit = Join-Path $ProjectRoot ".venv\Scripts\streamlit.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[ERROR] Virtual environment (.venv) was not found in: $ProjectRoot" -ForegroundColor Red
    Write-Host "Please set up the environment with:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv" -ForegroundColor White
    Write-Host "  .venv\Scripts\pip install -r requirements.txt" -ForegroundColor White
    exit 1
}

# 2. Dependency Health Check
& $VenvPython -c "import streamlit, folium, streamlit_folium, requests" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Frontend dependencies are missing in .venv." -ForegroundColor Red
    Write-Host "Please install required packages using:" -ForegroundColor Yellow
    Write-Host "  .venv\Scripts\pip install -r requirements.txt" -ForegroundColor White
    exit 1
}

# 3. Check Backend Availability Warning
$BackendCheck = & $VenvPython -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=1.0)" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARNING] FastAPI backend does not appear to be running on http://127.0.0.1:8000." -ForegroundColor Yellow
    Write-Host "Start the backend in a separate terminal: .\scripts\start_backend.ps1" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "[OK] Backend connected at http://127.0.0.1:8000" -ForegroundColor Green
}

# 4. Start Streamlit
Write-Host "[OK] Launching Streamlit dashboard on http://127.0.0.1:8501..." -ForegroundColor Green
Write-Host "Press Ctrl+C to terminate the dashboard." -ForegroundColor Gray
Write-Host ""

& $VenvPython -m streamlit run frontend/app.py --server.port 8501 --server.address 127.0.0.1
exit $LASTEXITCODE
