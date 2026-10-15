# TerraShield AI - Unified Local Services Launcher (Windows PowerShell)
# Launches FastAPI Backend and modern React + Vite Frontend concurrently with health verification.

param (
    [switch]$Streamlit = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "==========================================================" -ForegroundColor DarkGreen
Write-Host "  🌲 TerraShield AI - Integrated Local Application Launcher" -ForegroundColor DarkGreen
Write-Host "==========================================================" -ForegroundColor DarkGreen

# 1. Environment Validation
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "[ERROR] Virtual environment (.venv) not found at: $ProjectRoot" -ForegroundColor Red
    Write-Host "Please set up .venv before launching:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv" -ForegroundColor White
    Write-Host "  .venv\Scripts\pip install -r requirements.txt" -ForegroundColor White
    exit 1
}

# 2. Port Conflict Checks & Process Management
function Test-PortInUse($Port) {
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return ($connections -ne $null)
}

if (Test-PortInUse 8000) {
    Write-Host "[NOTICE] Port 8000 is already in use. Terminating stale backend process to reload latest routes..." -ForegroundColor Yellow
    $stalePids = (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique
    foreach ($p in $stalePids) {
        if ($p -and $p -ne 0) {
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Milliseconds 500
}
if (Test-PortInUse 5173) {
    Write-Host "[NOTICE] Port 5173 is already in use (Vite dev server may already be running)." -ForegroundColor Yellow
}

# 3. Launch Backend Process
Write-Host "[1/2] Starting FastAPI Backend on http://127.0.0.1:8000 (with hot reload)..." -ForegroundColor Cyan
$BackendProcess = Start-Process -FilePath $VenvPython -ArgumentList "-m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload" -WorkingDirectory $ProjectRoot -PassThru

# Wait for backend health
$BackendReady = $false
$Attempts = 0
while (-not $BackendReady -and $Attempts -lt 15) {
    Start-Sleep -Milliseconds 600
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 1 -ErrorAction SilentlyContinue
        if ($resp -and ($resp.status -eq "healthy" -or $resp.status -eq "ok")) {
            $BackendReady = $true
        }
    } catch {
        $Attempts++
    }
}

if ($BackendReady) {
    Write-Host "  [OK] Backend operational at http://127.0.0.1:8000 (API Docs: http://127.0.0.1:8000/docs)" -ForegroundColor Green
} else {
    Write-Host "  [WARNING] Backend startup timed out or responded with non-healthy status." -ForegroundColor Yellow
}

# 4. Launch React + Vite Frontend Process
Write-Host "[2/2] Starting Modern React + Vite Frontend on http://127.0.0.1:5173..." -ForegroundColor Cyan
$FrontendDir = Join-Path $ProjectRoot "frontend"

# Use npx vite or npm run dev
$FrontendProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev -- --host 127.0.0.1" -WorkingDirectory $FrontendDir -PassThru

# Optional Streamlit process if requested
$StreamlitProcess = $null
if ($Streamlit) {
    Write-Host "  [+] Starting Legacy Streamlit Interface on http://127.0.0.1:8501..." -ForegroundColor Cyan
    $StreamlitProcess = Start-Process -FilePath $VenvPython -ArgumentList "-m streamlit run frontend/app.py --server.port 8501 --server.address 127.0.0.1" -WorkingDirectory $ProjectRoot -PassThru
}

Start-Sleep -Seconds 2

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  ✅ TerraShield AI Premium Application is Operational!" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  • Modern React Application:   http://127.0.0.1:5173" -ForegroundColor White
Write-Host "  • FastAPI Backend Service:    http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  • Interactive Swagger Docs:   http://127.0.0.1:8000/docs" -ForegroundColor White
if ($Streamlit) {
    Write-Host "  • Streamlit Fallback UI:      http://127.0.0.1:8501" -ForegroundColor Gray
}
Write-Host "==========================================================" -ForegroundColor DarkGreen
Write-Host "Press Ctrl+C to terminate services." -ForegroundColor Gray

try {
    # Keep launcher alive and monitor processes
    while (-not $BackendProcess.HasExited -and -not $FrontendProcess.HasExited) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host "`nStopping background processes..." -ForegroundColor Yellow
    if (-not $BackendProcess.HasExited) {
        Stop-Process -Id $BackendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if (-not $FrontendProcess.HasExited) {
        Stop-Process -Id $FrontendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if ($StreamlitProcess -and -not $StreamlitProcess.HasExited) {
        Stop-Process -Id $StreamlitProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "TerraShield AI services terminated cleanly." -ForegroundColor Gray
}
