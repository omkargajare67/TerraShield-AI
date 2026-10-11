# TerraShield AI - Unified Local Services Launcher (Windows PowerShell)
# Launches both FastAPI Backend and Streamlit Frontend concurrently with health verification.

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

# 2. Port Conflict Checks
function Test-PortInUse($Port) {
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return ($connections -ne $null)
}

if (Test-PortInUse 8000) {
    Write-Host "[NOTICE] Port 8000 is already in use (FastAPI backend may already be running)." -ForegroundColor Yellow
}
if (Test-PortInUse 8501) {
    Write-Host "[NOTICE] Port 8501 is already in use (Streamlit frontend may already be running)." -ForegroundColor Yellow
}

# 3. Launch Backend Process
Write-Host "[1/3] Starting FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Cyan
$BackendProcess = Start-Process -FilePath $VenvPython -ArgumentList "-m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000" -WorkingDirectory $ProjectRoot -PassThru

# Wait for backend health
$BackendReady = $false
$Attempts = 0
while (-not $BackendReady -and $Attempts -lt 15) {
    Start-Sleep -Milliseconds 600
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 1 -ErrorAction SilentlyContinue
        if ($resp -and $resp.status -eq "healthy") {
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

# 4. Launch Frontend Process
Write-Host "[2/3] Starting Streamlit Frontend on http://127.0.0.1:8501..." -ForegroundColor Cyan
$FrontendProcess = Start-Process -FilePath $VenvPython -ArgumentList "-m streamlit run frontend/app.py --server.port 8501 --server.address 127.0.0.1" -WorkingDirectory $ProjectRoot -PassThru

Start-Sleep -Seconds 2

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  ✅ TerraShield AI Services are Operational!" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  • Web Application Dashboard:  http://127.0.0.1:8501" -ForegroundColor White
Write-Host "  • Backend API Service:        http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  • Interactive Swagger Docs:   http://127.0.0.1:8000/docs" -ForegroundColor White
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
    Write-Host "TerraShield AI services terminated cleanly." -ForegroundColor Gray
}
