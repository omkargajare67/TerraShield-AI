# TerraShield AI

**AI-Assisted Reforestation Site Planning & Environmental Risk Analysis**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-forestgreen.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.38+-FF4B4B.svg)](https://streamlit.io/)
[![Phase](https://img.shields.io/badge/Phase-2%20of%205%20(Geospatial%20Data%20Engine)-blue.svg)]()
[![Tests](https://img.shields.io/badge/Tests-49%20Passing-brightgreen.svg)]()

---

> **⚠️ Geospatial & Environmental Notice**  
> Terrain slope and aspect derived in Phase 2 are physical geospatial features, not validated geotechnical predictions or landslide probability maps.  
> Slope steepness is one environmental parameter among many; Factor of Safety ($FS$) and root-reinforcement equations will be evaluated in Phase 3.

---

## 1. Project Overview

TerraShield AI is an AI-assisted geospatial decision-support platform designed to identify high-impact reforestation locations and evaluate potential environmental benefits. The project focuses on three primary intervention areas:

1. **Landslide-Risk Mitigation:** Stabilizing steep slopes and reducing shallow slip risk through root-cohesion reinforcement.
2. **Air-Quality Buffers:** Filtering particulate matter via strategic vegetative buffer placement near emissions sources.
3. **Urban-Heat Mitigation:** Countering urban heat island effects through targeted microclimate cooling.

### The Prioritization Concept: Leverage Score ($L$)

Candidate parcels are ranked using the project's central efficiency metric:

$$\text{Leverage Score} = \frac{\text{Risk Reduction Achieved}}{\text{Trees Required}}$$

$$L = \frac{\Delta R}{N}$$

Where:
- $\Delta R$: Modeled change in the environmental risk metric.
- $N$: Total number of trees required for the modeled planting footprint.

---

## 2. Phase 2 Capabilities: Geospatial Data Engine

Phase 2 extends the Phase 1 foundation into a genuine geospatial processing pipeline:

- **DEM Ingestion & Metadata Inspection:** Decodes GeoTIFF elevation rasters, extracting raster dimensions, band counts, data type, pixel resolutions, bounding coordinates, nodata masks, and coordinate reference systems (CRS).
- **Terrain Gradient & Slope Processing:** Computes 2D spatial gradients ($dz/dx$ and $dz/dy$) using finite-difference formulation, yielding terrain slope in degrees. Automatically applies ellipsoidal geodesic scaling when inputs use geographic (WGS84 degrees) coordinates.
- **Terrain Aspect Analysis:** Computes aspect as an azimuth in degrees from North ($0^\circ-360^\circ$), flagging flat areas ($<0.1^\circ$ slope) as $-1.0^\circ$ (flat).
- **Sentinel-2 NDVI Calculation:** Ingests Red (Band 4) and NIR (Band 8) GeoTIFF bands, verifies grid compatibility, and calculates $\text{NDVI} = \frac{\text{NIR} - \text{Red}}{\text{NIR} + \text{Red}}$ with robust zero-denominator handling.
- **SoilGrids Data Ingestion & Validation:** Validates physical soil properties (clay, bulk density, pH, depth), depth intervals, and tabular column integrity against ISRIC SoilGrids standards.
- **Protected-Area Spatial Exclusion:** Performs vector intersection tests between candidate planting parcels and protected-area boundaries, computing overlap area and preserving statutory conservation justifications.
- **Visual Previews & Secure Exports:** Automatically renders multi-panel PNG previews and allows downloading derived GeoTIFF layers (Slope, Aspect, NDVI) through secure, traversal-proof artifact endpoints.

---

## 3. Architecture & Folder Structure

```
TERRASHIELD-AI/
|-- backend/
|   |-- app/
|   |   |-- __init__.py
|   |   |-- main.py                    # FastAPI entrypoint & router mounts
|   |   |-- api/
|   |   |   |-- __init__.py
|   |   |   |-- routes.py              # Phase 1 routes (/parcels, /analysis)
|   |   |   |-- geospatial_routes.py   # Phase 2 geospatial endpoints
|   |   |-- core/
|   |   |   |-- __init__.py
|   |   |   |-- config.py              # Environment settings & upload limits
|   |   |   |-- analysis_service.py    # Phase 1 leverage & exclusion solver
|   |   |   |-- demo_data.py           # GeoJSON data loading
|   |   |   |-- geospatial/            # Phase 2 Geospatial Engine
|   |   |       |-- __init__.py
|   |   |       |-- coordinate_systems.py  # CRS & geodesic scaling
|   |   |       |-- raster_loader.py       # GeoTIFF inspection & writer
|   |   |       |-- terrain.py             # Elevation, slope & aspect solver
|   |   |       |-- ndvi.py                # Sentinel-2 NDVI processor
|   |   |       |-- vector_loader.py       # Shapely vector & intersection engine
|   |   |       |-- soil_data.py           # SoilGrids metadata validator
|   |   |       |-- artifacts.py           # Traversal-safe artifact manager
|   |   |-- schemas/
|   |       |-- __init__.py
|   |       |-- health.py              # Health check schema
|   |       |-- parcel.py              # Parcel GeoJSON schemas
|   |       |-- analysis.py            # Analysis request/response schemas
|   |       |-- geospatial.py          # Terrain, NDVI, Soil & Vector schemas
|   |-- tests/
|       |-- __init__.py
|       |-- test_api.py                # Phase 1 API integration tests
|       |-- test_analysis_service.py   # Phase 1 leverage unit tests
|       |-- test_geospatial.py         # Phase 2 terrain, NDVI, vector tests
|
|-- frontend/
|   |-- __init__.py
|   |-- app.py                         # Streamlit user interface
|   |-- components/
|       |-- __init__.py
|       |-- map_view.py                # Folium map & parcel polygon styling
|       |-- metrics_view.py            # KPI cards & pandas summary table
|       |-- terrain_view.py            # DEM, NDVI & Environmental UI tabs
|
|-- data/
|   |-- sample/
|   |   |-- demo_parcels.geojson       # Synthetic candidate parcels
|   |   |-- synthetic_demo_dem.tif     # Synthetic test DEM fixture
|   |   |-- synthetic_s2_b04_red.tif   # Synthetic Sentinel-2 Red band
|   |   |-- synthetic_s2_b08_nir.tif   # Synthetic Sentinel-2 NIR band
|   |   |-- sample_protected_areas.geojson # Synthetic protected area vector
|   |-- raw/                           # Raw downloaded rasters (.gitignore)
|   |-- processed/                     # Processed rasters (.gitignore)
|   |-- uploads/                       # User uploads (.gitignore)
|   |-- artifacts/                     # Generated PNGs and GeoTIFFs (.gitignore)
|
|-- tests/
|   |-- __init__.py
|   |-- test_geojson.py                # GeoJSON structure & CRS validation
|   |-- test_frontend_components.py    # UI & map component unit tests
|
|-- docs/
|   |-- architecture.md                # System architecture & 5-phase roadmap
|
|-- requirements.txt                   # Pinned dependencies
|-- .gitignore                         # Version control ignore rules
|-- .env.example                       # Environment configuration template
`-- README.md                          # Project documentation
```

---

## 4. Dependencies & Installation

### Core Packages
- **Backend:** FastAPI, Uvicorn, Pydantic, HTTPX, Requests, Python-Multipart.
- **Geospatial & Numerics:** NumPy, SciPy, Shapely, Tifffile, ImageIO, Matplotlib, UTM, GeographicLib.
- **Frontend & Mapping:** Streamlit, Folium, Streamlit-Folium, Pandas.
- **Testing:** Pytest.

### Installation
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 5. Running the Application

### Terminal 1: Start the FastAPI Backend
```powershell
.\.venv\Scripts\uvicorn.exe backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Base: `http://127.0.0.1:8000`
- Swagger Interactive Docs: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/health`

### Terminal 2: Start the Streamlit Frontend
```powershell
.\.venv\Scripts\streamlit.exe run frontend/app.py
```
- Streamlit application opens at `http://localhost:8501`.

---

## 6. API Endpoints (Phase 2)

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service health status and runtime mode |
| `GET` | `/api/v1/parcels` | Demonstration candidate parcels GeoJSON |
| `POST` | `/api/v1/analysis` | Phase 1 prioritization analysis |
| `GET` | `/api/v1/geospatial/status` | Engine capability and supported formats |
| `POST` | `/api/v1/geospatial/dem/inspect` | Upload & inspect DEM GeoTIFF metadata |
| `POST` | `/api/v1/geospatial/dem/terrain` | Compute elevation, slope (deg), aspect (azimuth) |
| `POST` | `/api/v1/geospatial/ndvi` | Compute Sentinel-2 NDVI from Red & NIR bands |
| `POST` | `/api/v1/geospatial/soil/validate` | Validate SoilGrids metadata and parameters |
| `POST` | `/api/v1/geospatial/vectors/validate` | Validate GeoJSON vector geometry |
| `POST` | `/api/v1/geospatial/vectors/intersections` | Evaluate parcel vs protected-area spatial overlap |
| `GET` | `/api/v1/geospatial/artifacts/{id}` | Download generated GeoTIFF or preview PNG |

---

## 7. How to Supply Real Elevation & Environmental Data

### Acquiring Real DEM Rasters
1. **NASA SRTM 30m Global DEM:** Download tiles via [USGS EarthExplorer](https://earthexplorer.usgs.gov/) or [OpenTopography](https://portal.opentopography.org/).
2. **USGS 3DEP High-Resolution DEM:** Download 1m / 10m GeoTIFFs for US locations via the USGS National Map.
3. **Format Requirement:** Uncompressed or LZW-compressed GeoTIFF (`.tif`, `.tiff`) with explicit CRS metadata (e.g. UTM or EPSG:4326).
4. **Testing in UI:** Open the **🏔️ DEM & Terrain** tab in the dashboard, upload the GeoTIFF file, and click **Run Terrain Analysis**.

### Acquiring Sentinel-2 Imagery
1. Download Level-2A surface reflectance products via [Copernicus Data Space](https://dataspace.copernicus.eu/).
2. Select Band 4 (`B04_10m.jp2` / `.tif`, 665 nm) and Band 8 (`B08_10m.jp2` / `.tif`, 842 nm).
3. Upload both bands into the **🌿 Sentinel-2 NDVI** tab.

---

## 8. Running the Automated Test Suite

Execute the full suite with pytest:

```powershell
.\.venv\Scripts\pytest.exe -v
```

**Verification Results:**
- **49 total tests** executed and passing.
- 26 tests cover Phase 1 foundation, APIs, calculations, and GeoJSON structure.
- 23 tests cover Phase 2 DEM inspection, 45° slope validation, 180° aspect verification, NDVI zero-denominator protection, SoilGrids validation, vector spatial intersection, and artifact security.
