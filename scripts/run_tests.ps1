# TerraShield AI - Test Suite Runner (Windows PowerShell)
# Executes full test suite with detailed output and exit code propagation

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "  TerraShield AI - Automated Test Suite Runner" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# 1. Virtual Environment Validation
$VenvPytest = Join-Path $ProjectRoot ".venv\Scripts\pytest.exe"

if (-not (Test-Path $VenvPytest)) {
    Write-Host "[ERROR] pytest not found in .venv\Scripts\pytest.exe." -ForegroundColor Red
    Write-Host "Please set up the environment with:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv" -ForegroundColor White
    Write-Host "  .venv\Scripts\pip install -r requirements.txt" -ForegroundColor White
    exit 1
}

# 2. Run Tests
Write-Host "[INFO] Executing pytest with verbose test discovery..." -ForegroundColor Gray
& $VenvPytest -v $args

$TestExit = $LASTEXITCODE

Write-Host ""
if ($TestExit -eq 0) {
    Write-Host "====================================================" -ForegroundColor Green
    Write-Host "  [ALL TESTS PASSED] Workspace validation succeeded!" -ForegroundColor Green
    Write-Host "====================================================" -ForegroundColor Green
} else {
    Write-Host "====================================================" -ForegroundColor Red
    Write-Host "  [TEST FAILURES DETECTED] Exit Code: $TestExit" -ForegroundColor Red
    Write-Host "====================================================" -ForegroundColor Red
}

exit $TestExit
