# TerraShield AI - Local Application Smoke Test (Windows PowerShell)
# Performs automated end-to-end operational sanity checks across components

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "  TerraShield AI - Operational Smoke Test" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# 1. Virtual Environment Validation
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[ERROR] Virtual environment (.venv) was not found in: $ProjectRoot" -ForegroundColor Red
    exit 1
}

# 2. Run Smoke Test Python Harness
Write-Host "[INFO] Running Python smoke test suite harness..." -ForegroundColor Gray

$SmokeScript = @"
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, r"$ProjectRoot")

print("Checking FastAPI application initialization...")
from backend.app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# 1. Health check
resp = client.get("/health")
assert resp.status_code == 200, f"Health check failed: {resp.status_code}"
data = resp.json()
assert data["status"] == "healthy", f"Health status unexpected: {data}"
print(f"  [OK] /health status: {data['status']}, app: {data['app_name']}")

# 2. Geospatial datasets inspection
from backend.app.core.config import settings
dem_path = settings.BASE_DIR / "data" / "raw" / "real" / "wayanad_dem.tif"
if dem_path.exists():
    import hashlib
    with open(dem_path, "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()
    assert h == "680aa3cb46f4b7d148b2d62224ff8f8daa9591dcee5921d46c0f8c4c8a5ca2b6"
    print("  [OK] Verified NASADEM GeoTIFF SHA-256 checksum matched.")
else:
    print("  [INFO] Real NASADEM file not present; using synthetic fixtures.")

# 3. Geotechnical single-point analysis
payload = {
    "beta_deg": 28.0,
    "soil": {
        "c_prime_kpa": 8.0,
        "phi_prime_deg": 26.0,
        "gamma_kn_m3": 18.5,
        "z_m": 1.8,
        "m_fraction": 0.5,
    },
    "root": {
        "tensile_stress_input": 25.0,
        "tensile_stress_unit": "MPa",
        "root_area_ratio": 0.002,
        "k_factor": 1.2,
    },
    "fs_target": 1.3,
}
resp_geo = client.post("/api/v1/geotechnical/analysis", json=payload)
assert resp_geo.status_code == 200
data_geo = resp_geo.json()
assert data_geo["baseline"]["factor_of_safety"] is not None
assert data_geo["reinforced"]["fs_reinforced"] is not None
print(f"  [OK] Geotechnical analysis: baseline FS={data_geo['baseline']['factor_of_safety']:.2f}, reinforced FS={data_geo['reinforced']['fs_reinforced']:.2f}")

# 4. Recommendation Engine Status
resp_rec_status = client.get("/api/v1/recommendations/status")
assert resp_rec_status.status_code == 200
data_rec = resp_rec_status.json()
print(f"  [OK] Recommendation engine status: {data_rec['status']}, DEM: {data_rec['dem_verified_source'][:30]}...")

# 5. Frontend Components Importability
from frontend.components.map_view import create_parcels_map
from frontend.components.metrics_view import build_analysis_dataframe
from backend.app.core.demo_data import load_demo_geojson
demo_geo = load_demo_geojson()
m = create_parcels_map(demo_geo)
assert m is not None
print("  [OK] Frontend folium map and dataframe builder functional.")

print("\n[ALL SMOKE CHECKS PASSED SUCCESSFULLY]")
"@

$TempSmokeFile = Join-Path $ProjectRoot "scripts\_temp_smoke_check.py"
Set-Content -Path $TempSmokeFile -Value $SmokeScript -Encoding UTF8

try {
    & $VenvPython $TempSmokeFile
    $ExitCode = $LASTEXITCODE
} finally {
    if (Test-Path $TempSmokeFile) {
        Remove-Item $TempSmokeFile -Force
    }
}

Write-Host ""
if ($ExitCode -eq 0) {
    Write-Host "====================================================" -ForegroundColor Green
    Write-Host "  [SMOKE TEST SUCCESSFUL] All systems operational!" -ForegroundColor Green
    Write-Host "====================================================" -ForegroundColor Green
} else {
    Write-Host "====================================================" -ForegroundColor Red
    Write-Host "  [SMOKE TEST FAILED] Please check errors above." -ForegroundColor Red
    Write-Host "====================================================" -ForegroundColor Red
}

exit $ExitCode
