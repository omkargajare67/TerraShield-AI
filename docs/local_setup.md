# TerraShield AI - Local Setup & Developer Guide

This document provides complete, reproducible setup and developer instructions for running, testing, and developing **TerraShield AI** on a local Windows environment from a fresh repository checkout.

---

## 1. System Requirements & Verified Environment

- **Operating System:** Windows 10 / Windows 11 (64-bit)
- **Shell:** Windows PowerShell 5.1 or PowerShell 7+
- **Python Version:** Python 3.10 to 3.14 (Verified and tested on **Python 3.14.7**)
- **Network / Internet:** Not required for local testing or demo workflows. All unit, integration, and smoke tests run **100% offline**.
- **External Dependencies:** No cloud accounts, external databases, or third-party paid API keys required.
- **Geospatial Binaries:** Pure-Python native fallback architecture is enabled by default (uses `tifffile`, `numpy`, `scipy`, `shapely`, and `geographiclib`; does **not** mandate complex C GDAL/Rasterio/PyProj compilation).

---

## 2. Step-by-Step Installation (Fresh Checkout)

Open PowerShell in the repository root directory (`c:\TERRASHIELD AI`):

### Step 1: Create Virtual Environment
```powershell
python -m venv .venv
```

### Step 2: Set Execution Policy (if restricted by Windows)
If PowerShell script execution is restricted, enable process-level execution:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Step 3: Activate Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 4: Install Pinned Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Verifying Environmental Data Assets

TerraShield AI operates on a **Three-Tier Data Provenance Model**:
1. **Tier 1 — Synthetic Test Fixtures (`data/sample/`):** Tracked in Git, deterministic offline fixtures for automated test suites.
2. **Tier 2 — Real Environmental Observations (`data/raw/real/`):** Verified datasets from authoritative space agencies.
3. **Tier 3 — Derived Geospatial & Geotechnical Products (`data/processed/` & `data/artifacts/`):** Continuous slope, aspect, NDVI, Factor of Safety, and recommendation exports.

### Verified Elevation Dataset
The pilot study area (Wayanad Watershed, Western Ghats, Kerala) uses:
- **Dataset:** NASA SRTM NASADEM Global 1 Arc-Second V001
- **Granule Identifier:** `NASADEM_HGT_n11e076`
- **File Location:** `data/raw/real/wayanad_dem.tif`
- **Dimensions:** $360 \times 360$ pixels in native `EPSG:4326 (WGS 84)`
- **SHA-256 Checksum:**
  ```
  680aa3cb46f4b7d148b2d62224ff8f8daa9591dcee5921d46c0f8c4c8a5ca2b6
  ```

To verify the checksum in PowerShell:
```powershell
Get-FileHash -Algorithm SHA256 data\raw\real\wayanad_dem.tif
```

---

## 4. Local Execution Commands

The repository provides automated PowerShell launcher scripts in `scripts/`:

### 4.1 Launch Backend Service (FastAPI)
Using the launcher script:
```powershell
.\scripts\start_backend.ps1
```
Or directly:
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- **Service Base:** `http://127.0.0.1:8000`
- **Interactive OpenAPI Docs:** `http://127.0.0.1:8000/docs`
- **Service Health Check:** `http://127.0.0.1:8000/health`

### 4.2 Launch Frontend Dashboard (Streamlit)
In a second PowerShell terminal:
```powershell
.\scripts\start_frontend.ps1
```
Or directly:
```powershell
.\.venv\Scripts\streamlit.exe run frontend/app.py --server.port 8501 --server.address 127.0.0.1
```
- **Dashboard URL:** `http://127.0.0.1:8501`

---

## 5. Automated Testing & Quality Assurance

### 5.1 Run Full Test Suite
Using the PowerShell test runner:
```powershell
.\scripts\run_tests.ps1
```
Or directly via pytest:
```powershell
.\.venv\Scripts\pytest.exe -v
```
**Expected Result:** 152 passed, 0 failed.

### 5.2 Run Operational Smoke Test
Validates end-to-end API health, NASADEM checksum, geotechnical limits, and UI data builders without launching a browser:
```powershell
.\scripts\smoke_test.ps1
```

### 5.3 Run Performance Benchmarks
Measures execution time across raster loading, terrain analysis, NDVI processing, and recommendation generation:
```powershell
.\.venv\Scripts\python.exe scripts\benchmark_phase5.py
```

---

## 6. Troubleshooting Common Issues

### Issue 1: PowerShell Script Execution Restricted
**Symptoms:** `cannot be loaded because running scripts is disabled on this system.`  
**Solution:** Run with process-level bypass:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_backend.ps1
```

### Issue 2: Port Conflict on 8000 or 8501
**Symptoms:** `[Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000)`  
**Solution:** Find and stop the process using the port, or specify an alternative port via environment variable:
```powershell
$env:TERRASHIELD_PORT = "8001"
.\scripts\start_backend.ps1
```

### Issue 3: Missing `.venv` Virtual Environment
**Symptoms:** `[ERROR] Virtual environment (.venv) was not found`  
**Solution:** Create the environment and install requirements as shown in Section 2.

### Issue 4: Offline Warning on Startup
**Symptoms:** Streamlit displays "Backend Disconnected"  
**Solution:** Ensure the FastAPI backend is running in a separate terminal before launching the frontend.

---

## 7. Security Best Practices for Local Deployment

- **Binding Address:** The default configuration binds to `127.0.0.1` (localhost). Do **not** expose the server on `0.0.0.0` or public internet interfaces without reverse-proxy authentication and SSL termination.
- **Path Traversal Protection:** Artifact download routes strictly enforce filename basenames (`os.path.basename`) and containment validation (`relative_to`) within the designated `data/artifacts/` directory.
- **HTML Injection Defense:** All generated HTML audit reports strictly sanitize parcel IDs, run IDs, warnings, and scenario notes via Python's `html.escape`.
