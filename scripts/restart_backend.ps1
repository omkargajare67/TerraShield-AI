$ErrorActionPreference = "SilentlyContinue"
$stalePids = (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique
foreach ($pidToKill in $stalePids) {
    if ($pidToKill -and $pidToKill -ne 0) {
        Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep -Milliseconds 600
Start-Process -FilePath "C:\TERRASHIELD AI\.venv\Scripts\python.exe" -ArgumentList "-m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload" -WorkingDirectory "C:\TERRASHIELD AI"
Start-Sleep -Seconds 2
$res = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/case-studies"
$res | Select-Object -Property id, name, country, disaster_type, readiness | ConvertTo-Json
