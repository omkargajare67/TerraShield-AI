# TerraShield AI

**AI-Assisted Reforestation Site Planning & Environmental Risk Analysis**  
*Integrated Decision Support System for Steep-Slope Landslide Hazard Mitigation*

[![Python 3.10+](https://img.shields.io/badge/python-3.10%20--%203.14-forestgreen.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19.2+-61DAFB.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8.3+-646CFF.svg)](https://vitejs.dev/)
[![Release](https://img.shields.io/badge/Release-1.2.0%20(One--Click%20Auto--Acquisition)-forestgreen.svg)]()
[![Tests](https://img.shields.io/badge/Tests-175%20Passing-brightgreen.svg)]()
[![License](https://img.shields.io/badge/License-Proprietary%20%2F%20Research-lightgrey.svg)]()

---

> **⚠️ Scientific Integrity & Geotechnical Disclaimer**  
> Geotechnical stability outputs and Factor of Safety ($FS$) calculations in TerraShield AI are **exploratory limit-equilibrium benchmark scenario models** (Infinite Slope + simplified Wu–Waldron root-cohesion). They do **NOT** represent site-specific borehole measurements, certified geotechnical engineering predictions, or statutory planting mandates.  
> Official legal forest reserve boundaries remain **unverified** pending state cadastral boundary datasets. Species recommendations remain **pending curated botanical data**.

---

## 1. Project Overview: One-Click Location Analysis & Auto-Acquisition

TerraShield AI is an integrated geospatial and geotechnical decision-support system designed to identify high-impact reforestation sites and evaluate potential slope-stabilization benefits:

1. **Landslide-Risk Mitigation:** Mechanistic evaluation of steep-slope stabilization via vegetative root-cohesion reinforcement.
2. **Air-Quality Buffers:** Spatial planning for vegetative particulate capture.
3. **Urban-Heat Mitigation:** Canopy density evaluation for urban heat alleviation.

### 🚀 NEW: Automatic Geospatial Data Acquisition (One-Click Analysis)
Users no longer need to find, download, convert, or upload GIS rasters. The system provides an end-to-end autonomous pipeline:
- **Interactive Map Selection:** Draw custom polygons or drag bounding boxes directly on the Leaflet map, or pick from high-risk corridor presets (Wayanad, Idukki, Munnar, Shimla, Joshimath).
- **Automated Geometry Validation:** Validates WGS 84 bounds, checks coordinate ordering, and calculates ellipsoidal geodesic area ($1.0\text{ to }25,000\text{ ha}$).
- **Zero-Key STAC Discovery:** Directly queries the **Microsoft Planetary Computer STAC Catalog** without requiring user API keys or subscriptions.
- **Elevation Acquisition (DEM):** Automatically discovers and crops Copernicus 30m Global DEM (`cop-dem-glo-30`), with fallback to NASA SRTM 30m (`nasadem`). Validates elevation bounds, CRS, and land pixels.
- **Multispectral Vegetation (Sentinel-2 L2A):** Searches recent low-cloud Sentinel-2 scenes, fetches Red (B04) and Near-Infrared (B08) rasters, and calculates continuous NDVI with zero-denominator & cloud-mask protections. (Falls back to reduced-data terrain-only analysis if satellite imagery is unavailable).
- **Automated Terrain Derivation:** Computes slope and aspect in-memory using localized Horn's finite-difference method with latitude-aware linear distance scaling.
- **Limit-Equilibrium Geotechnical Solver:** Solves baseline Factor of Safety ($FS_{base}$), root-reinforced Factor of Safety ($FS_{reinf}$), $\Delta FS$, and required stabilizing root cohesion ($c_{r,\text{req}}$).
- **Candidate Parcel Tessellation & Multi-Criteria Ranking:** Generates candidate stabilization parcels, applies slope and reserve eligibility rules, scores parcels via multi-objective weighting, and produces interactive GeoJSON layers.
- **Isolated Project Workspace:** Each run creates a dedicated workspace in `data/projects/<project_id>/` with independent rasters, parcel GeoJSON, acquisition provenance, and run logs without overwriting previous projects.
- **Preserved Benchmark:** The preloaded **Wayanad Watershed Pilot** remains fully available as an instant offline benchmark.

### Verified Pilot Study Dataset: Wayanad Watershed (Kerala, India)
- **Pilot Study Area:** Wayanad Watershed, Western Ghats, Kerala, India (`11.55° N – 11.65° N`, `76.00° E – 76.10° E`).
- **Verified Elevation Dataset:** NASA SRTM NASADEM Global 1 Arc-Second V001 (`NASADEM_HGT_n11e076`, $360 \times 360$ pixels in native `EPSG:4326 WGS 84`).
- **Verified DEM SHA-256 Checksum:**
  ```
  680aa3cb46f4b7d148b2d62224ff8f8daa9591dcee5921d46c0f8c4c8a5ca2b6
  ```

---

## 2. Three-Tier Data Provenance Model

To prevent confusion between synthetic test fixtures, genuine space-agency observations, and custom user uploads, TerraShield AI strictly enforces three data provenance tiers:

1. **Tier 1 — Synthetic Test Fixtures (`data/sample/`):** Tracked in version control; deterministic fixtures (5 demo parcels, 10x10 synthetic DEM, Cascade Foothills test rasters) used for automated offline test suites.
2. **Tier 2 — Real Environmental Observations (`data/raw/real/` and `data/projects/`):** Authentic satellite and terrain data (NASA SRTM NASADEM, Sentinel-2 L2A Red/NIR bands, custom user-uploaded GeoTIFFs).
3. **Tier 3 — Derived Geospatial & Geotechnical Products (`data/processed/` & `data/artifacts/`):** Continuous slope, aspect, NDVI, Factor of Safety, and multi-format recommendation exports generated by the verified engine.

---

## 3. System Architecture & Integrated Capabilities

```
+-----------------------------------------------------------------------------------+
|                         Streamlit Frontend (frontend/app.py)                      |
|                                                                                   |
|  - 🏠 Overview Dashboard           - 🌐 1. Study Area Studio                      |
|  - 📁 2. Data & Raster Ingestion   - ⚙️ 3. Geotechnical Studio                   |
|  - 🎯 4. Prioritization & Run      - 📊 5. Results Explorer & Maps                |
|  - 📥 6. Export Center & Provenance Disclosures                                   |
+------------------------------------+----------------------------------------------+
                                     | HTTP REST (JSON & Multipart Form-Data)
                                     v
+-----------------------------------------------------------------------------------+
|                         FastAPI Backend (backend/app/main.py)                     |
|                                                                                   |
|  - /health                        -> Operational status, version, mode            |
|  - /api/v1/projects/*             -> Project workspace persistence & file uploads |
|  - /api/v1/parcels                -> Candidate parcels FeatureCollection          |
|  - /api/v1/geospatial/*           -> GeoTIFF inspection, slope, aspect, NDVI      |
|  - /api/v1/geotechnical/*         -> Infinite slope, Wu-Waldron root cohesion     |
|  - /api/v1/recommendations/*      -> Generalized parcel ranking & exports         |
+------------------------------------+----------------------------------------------+
```

---

## 4. Local Installation & Quick Start (Windows)

### Prerequisites
- Windows 10 / Windows 11 (64-bit)
- Python 3.10 to 3.14 installed (Verified on **Python 3.14.7**)
- PowerShell 5.1 or PowerShell 7+

### Step-by-Step Installation:
```powershell
# 1. Clone repository and navigate to root directory
cd c:\TERRASHIELD AI

# 2. Create virtual environment
python -m venv .venv

# 3. Allow local script execution (if restricted)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 4. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 5. Install pinned dependencies
pip install -r requirements.txt
```

---

## 5. Running the Application

### Option A: Unified Launcher (Single Command — Recommended)

Start both FastAPI backend and modern React + Vite frontend concurrently with health verification:

```powershell
.\scripts\start_all.ps1
```

- **Modern Interactive App:** `http://127.0.0.1:5173`
- **Backend API:** `http://127.0.0.1:8000`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`

### Option B: Separate Terminal Launchers

```powershell
# Terminal 1: Launch Backend API
.\scripts\start_backend.ps1

# Terminal 2: Launch Frontend Application
cd frontend
npm run dev
```

---

## 6. Testing & Quality Assurance

### Execute Automated Test Suite
```powershell
.\scripts\run_tests.ps1
```
Or directly via pytest:
```powershell
.\.venv\Scripts\pytest.exe -v
```
**Verification Baseline:** **175 passed, 0 failed** in ~13 seconds. Includes 17 comprehensive unit, integration, and offline-mocked tests in `backend/tests/test_auto_acquisition.py`. 100% offline reproducible without external network dependencies.

### Frontend Quality Check & Build
```powershell
cd frontend
npm run build
```
Vite production build succeeds in <1s with 0 TypeScript/bundler errors.


### Execute Operational Smoke Test
Validates API endpoints, NASADEM checksum, geotechnical solvers, and UI components:
```powershell
.\scripts\smoke_test.ps1
```

### Execute Hardware Performance Benchmark
Profiles local hardware execution times across all core workflows:
```powershell
.\.venv\Scripts\python.exe scripts\benchmark_phase5.py
```

---

## 7. Directory & Artifact Structure

```
c:\TERRASHIELD AI\
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entrypoint & router mounts
│   │   ├── api/                       # API router endpoints (Parcels, Geospatial, Geotech, Recommendations)
│   │   ├── core/                      # Geospatial, geotechnical, and recommendation calculation engines
│   │   └── schemas/                   # Pydantic request & response models
│   └── tests/                         # Automated test suite (152 tests across 8 modules)
├── frontend/
│   ├── app.py                         # Streamlit multi-tab application entrypoint
│   └── components/                    # Folium maps, KPI cards, and engine tabs
├── data/
│   ├── sample/                        # Tracked synthetic test fixtures (Tier 1)
│   ├── raw/real/                      # NASA NASADEM & Sentinel-2 input rasters (Tier 2)
│   ├── processed/                     # Derived continuous rasters & recommendation outputs (Tier 3)
│   └── artifacts/                     # Preview images & temporary file slices
├── scripts/
│   ├── start_backend.ps1              # Backend PowerShell launcher
│   ├── start_frontend.ps1             # Frontend PowerShell launcher
│   ├── run_tests.ps1                  # Test runner script
│   ├── smoke_test.ps1                 # Operational sanity smoke test
│   └── benchmark_phase5.py            # Local hardware performance benchmark
├── docs/
│   ├── architecture.md                # System architecture & integration map
│   ├── local_setup.md                 # Fresh checkout developer setup guide
│   ├── phase5_validation_report.md    # Formal release validation audit report
│   ├── recommendation_methodology.md  # Multi-criteria scoring formulation
│   └── geotechnical_model.md          # Geotechnical limit-equilibrium derivations
├── requirements.txt                   # Pinned Python package dependencies
├── CHANGELOG.md                       # Project revision history across Phases 1–5
└── README.md                          # Primary project documentation
```

---

## 8. Release Status & Scientific Caveat

- **Software Status:** **Release Candidate 1 (`v1.0.0-rc1`)** — All software validation tests passed.
- **Scientific Status:** Limit-equilibrium geotechnical stability and Wu-Waldron root-cohesion calculations are mathematically verified exploratory benchmark scenarios. Field geotechnical borehole measurements and authoritative legal reserve cadastres remain required prior to civil engineering works or regulatory enforcement.
