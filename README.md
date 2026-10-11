# TerraShield AI

**AI-Assisted Reforestation Site Planning & Environmental Risk Analysis**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-forestgreen.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.38+-FF4B4B.svg)](https://streamlit.io/)
[![Phase](https://img.shields.io/badge/Phase-1%20of%205%20(Foundation)-blue.svg)]()
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen.svg)]()

---

> **⚠️ Phase 1 Demonstration Notice**  
> Sample geometries and attributes are illustrative and are not verified environmental observations.  
> Results are not validated geotechnical predictions or planting prescriptions.

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

## 2. Phase 1 Scope

Phase 1 establishes a modular, decoupled foundation:
- **FastAPI Backend:** Exposes clean REST API endpoints for health monitoring, GeoJSON parcel delivery, and deterministic analysis execution.
- **Analysis Engine:** Calculates $L = \Delta R / N$, enforces exclusion criteria (e.g., statutory wilderness reserves, shallow soil constraints), and handles boundary conditions (such as division-by-zero prevention when $N \le 0$).
- **Streamlit Frontend:** A forest-green themed interface featuring an interactive Folium map, KPI cards, candidate parcel table, and real-time result downloads.
- **Deterministic Demonstration Dataset:** A 5-parcel GeoJSON FeatureCollection in an illustrative watershed (`data/sample/demo_parcels.geojson`).
- **Automated Test Suite:** Comprehensive pytest suite covering unit calculations, edge cases, schema validation, and HTTP endpoints.

---

## 3. Architecture & Folder Structure

```
TERRASHIELD-AI/
|-- backend/
|   |-- app/
|   |   |-- __init__.py
|   |   |-- main.py                    # FastAPI entrypoint & /health route
|   |   |-- api/
|   |   |   |-- __init__.py
|   |   |   |-- routes.py              # API v1 routes (/parcels, /analysis)
|   |   |-- core/
|   |   |   |-- __init__.py
|   |   |   |-- config.py              # Environment settings
|   |   |   |-- analysis_service.py    # Deterministic leverage & exclusion solver
|   |   |   |-- demo_data.py           # GeoJSON data loading & validation
|   |   |-- schemas/
|   |       |-- __init__.py
|   |       |-- health.py              # Health check Pydantic model
|   |       |-- parcel.py              # GeoJSON feature Pydantic models
|   |       |-- analysis.py            # Analysis request/response schemas
|   |-- tests/
|       |-- __init__.py
|       |-- test_api.py                # FastAPI HTTP endpoint tests
|       |-- test_analysis_service.py   # Unit tests for leverage calculations
|
|-- frontend/
|   |-- __init__.py
|   |-- app.py                         # Streamlit user interface
|   |-- components/
|       |-- __init__.py
|       |-- map_view.py                # Folium map & polygon styling
|       |-- metrics_view.py            # KPI cards & pandas tables
|
|-- data/
|   |-- sample/
|       |-- demo_parcels.geojson       # Synthetic candidate parcels
|
|-- tests/
|   |-- __init__.py
|   |-- test_geojson.py                # GeoJSON structure & CRS validation
|   |-- test_frontend_components.py    # Map & DataFrame component tests
|
|-- docs/
|   |-- architecture.md                # System architecture & 5-phase roadmap
|
|-- requirements.txt                   # Production & dev dependencies
|-- .gitignore                         # Version control ignore rules
|-- .env.example                       # Environment configuration template
`-- README.md                          # Project documentation
```

---

## 4. Prerequisites

- **Python:** 3.10, 3.11, 3.12, 3.13, or 3.14.
- **Operating System:** Windows, macOS, or Linux.
- **Git** (optional, for version control).

---

## 5. Environment Setup & Installation

### Step 1: Clone or Navigate to the Repository
```bash
cd "c:\TERRASHIELD AI"
```

### Step 2: Create and Activate a Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**On macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables (Optional)
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Default configuration:
```ini
TERRASHIELD_ENV=demo
TERRASHIELD_HOST=127.0.0.1
TERRASHIELD_PORT=8000
TERRASHIELD_API_URL=http://127.0.0.1:8000
```

---

## 6. Running the System

Start the backend and frontend in separate terminal windows.

### Terminal 1: Start the Backend (FastAPI)
```powershell
.\.venv\Scripts\uvicorn.exe backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- **API Base:** `http://127.0.0.1:8000`
- **Health Check:** `http://127.0.0.1:8000/health`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`
- **ReDoc Documentation:** `http://127.0.0.1:8000/redoc`

### Terminal 2: Start the Frontend (Streamlit)
```powershell
.\.venv\Scripts\streamlit.exe run frontend/app.py
```
- The Streamlit interface will open automatically in your browser at `http://localhost:8501`.

---

## 7. Running the Test Suite

Execute all automated unit and integration tests with pytest:

```powershell
.\.venv\Scripts\pytest.exe -v
```

The test suite validates:
- Health check endpoint status and schema (`GET /health`).
- Parcels endpoint GeoJSON delivery (`GET /api/v1/parcels`).
- Analysis endpoint calculations and HTTP validation (`POST /api/v1/analysis`).
- Formula correctness: $L = \Delta R / N$.
- Zero-tree count division-by-zero protection.
- Negative risk reduction and invalid input handling.
- Statutory reserve and shallow-soil exclusion handling.
- GeoJSON polygon closure and metadata provenance.
- Folium map generation and DataFrame rendering.

---

## 8. Demonstration Workflow & How to Use

1. **Verify Backend Connection:**  
   Open the Streamlit app. The sidebar will display a green `Backend Connected (DEMO MODE)` indicator.
2. **Inspect Candidate Parcels:**  
   On the **Interactive Map** tab, candidate parcels appear as polygons in the illustrative watershed. Click any polygon to see its properties (ID, area, baseline risk, estimated tree count).
3. **Configure & Run Analysis:**  
   In the sidebar:
   - Select scenario: `landslide_mitigation`.
   - Optionally adjust the **Min Baseline Risk Threshold** slider.
   - Click **Run Demonstration Analysis**.
4. **Evaluate Results Dashboard:**  
   - Review KPI metrics: Total parcels, eligible sites, excluded sites, and peak leverage score.
   - Inspect the **Candidate Parcel Prioritization Table** sorted by priority rank.
   - Expand **View Exclusion Explanations & Constraints** to see why parcels were excluded (e.g., protected wilderness reserve, bedrock outcrop).
5. **Download Outputs:**  
   In the **Data Export & Downloads** section:
   - Click **Download Results GeoJSON** for GIS software (QGIS, ArcGIS).
   - Click **Download Results CSV** for spreadsheet analysis.

---

## 9. Current Limitations (Phase 1)

- **Synthetic Data:** Geometries and values are deterministic demonstrations in an illustrative basin, not ground-truth measurements.
- **No Live Rasters:** DEM slope analysis and satellite multispectral imagery are not yet ingested.
- **Linear Leverage Model:** Tree counts and risk reductions are illustrative inputs; physical root-cohesion equations are scheduled for Phase 3.

---

## 10. Planned Future Phases

- **Phase 2: Real Terrain & Elevation Ingestion**  
  NASA SRTM 30m DEM pipeline, slope gradient calculation, aspect, curvature, and hydrological flow paths.
- **Phase 3: Geotechnical Slope Stability & Urban Heat**  
  Infinite slope stability factor of safety ($FS$) solver and the Wu-Waldron root-cohesion model ($\Delta C$). Surface temperature raster analysis.
- **Phase 4: Satellite Monitoring & Environmental Masking**  
  Copernicus Sentinel-2 NDVI time-series, ISRIC SoilGrids texture/depth, and World Database on Protected Areas (WDPA) vector exclusion masking.
- **Phase 5: Multi-Criteria AI Prioritization & Deployment**  
  Multi-objective optimization, containerized deployment, CI/CD pipeline, and public cloud deployment.
