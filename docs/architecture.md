# TerraShield AI - System Architecture & Integration Specification

**Phase 5 Release Candidate (`v1.0.0-rc1`)**  
Pilot Study Area: **Wayanad Watershed, Western Ghats, Kerala, India**

---

## 1. System Overview & Technology Stack

TerraShield AI is an integrated, decoupled decision-support system designed to identify, evaluate, and prioritize candidate reforestation interventions on landslide-prone mountain slopes.

### Technology Stack
- **Backend API:** FastAPI (ASGI), Uvicorn, Pydantic v2
- **Frontend Dashboard:** Streamlit, Folium, `streamlit-folium`, Pandas
- **Geospatial & Numerics:** NumPy, SciPy, Shapely, `tifffile`, `imageio`, Matplotlib, GeographicLib
- **Storage & File I/O:** Native GeoTIFF, RFC 7946 GeoJSON, CSV, JSON, HTML
- **Testing & QA:** Pytest (152 automated tests, 100% offline reproducible)
- **Runtime Environment:** Python 3.10–3.14 (Verified on Python 3.14.7, Windows 64-bit)

---

## 2. End-to-End Architectural Integration Map

```
+--------------------------------------------------------------------------------------------------+
|                                    STREAMLIT FRONTEND (app.py)                                   |
|                                                                                                  |
|   - 🗺️ Interactive Folium Map      - 📊 Priority Dashboard           - 🎯 Recommendations Tab    |
|   - 📐 Geotechnical Intelligence    - 🏔️ DEM & Terrain Engine         - 🌿 Sentinel-2 NDVI Tab    |
|   - 🛡️ Environmental Constraints    - 📍 Western Ghats Pilot Corridor - 📥 Multi-Format Downloads |
+-------------------------------------------------+------------------------------------------------+
                                                  | HTTP / REST (JSON & Multipart Form-Data)
                                                  v
+--------------------------------------------------------------------------------------------------+
|                                  FASTAPI BACKEND (main.py)                                       |
|                                                                                                  |
|   Routers:                                                                                       |
|   ├── /health                              -> Service status, version (v0.1.0/1.0), runtime mode |
|   ├── /api/v1/parcels                      -> Demonstration baseline parcels                     |
|   ├── /api/v1/analysis                     -> Legacy demonstration leverage analysis             |
|   ├── /api/v1/geospatial/*                 -> Terrain slope/aspect, NDVI, soil, vector analysis  |
|   ├── /api/v1/geotechnical/*               -> Infinite slope FS, Wu-Waldron root cohesion        |
|   └── /api/v1/recommendations/*            -> Multi-criteria candidate parcel ranking & exports  |
+-------------------------------------------------+------------------------------------------------+
                                                  | Internal Service Calls
                                                  v
+--------------------------------------------------------------------------------------------------+
|                                  CORE ENGINES & CALCULATION MODULES                              |
|                                                                                                  |
|   1. Geospatial Engine:                                                                          |
|      - raster_loader.py: GeoTIFF inspection (affine transforms, 4x4 matrices, signed int16)      |
|      - terrain.py: Central-difference gradients, ellipsoidal degree scaling, aspect azimuth      |
|      - ndvi.py: Band alignment validation, (NIR - Red) / (NIR + Red) with zero-division safety   |
|      - vector_loader.py: Shapely polygon validation & statutory reserve intersection             |
|                                                                                                  |
|   2. Geotechnical Engine:                                                                        |
|      - infinite_slope.py: Planar translational limit equilibrium Factor of Safety (FS_0)         |
|      - root_cohesion.py: Wu-Waldron vegetative reinforcement (ΔC = K · Tr · RAR) & FS_reinforced |
|      - required_cohesion.py: Analytical solver for target FS (default 1.3)                       |
|      - tree_density.py: Stem density estimator with biological carrying capacity cap             |
|      - sensitivity.py: Multi-parameter stability sensitivity analysis                           |
|                                                                                                  |
|   3. Spatial Recommendation Engine:                                                              |
|      - parcel_generation.py: WGS 84 ellipsoidal candidate parcel grid generation                 |
|      - zonal_statistics.py: Multi-resolution bounding box raster zonal aggregation              |
|      - eligibility.py: Rule-based physical (slope >45°), administrative, and canopy exclusions   |
|      - scoring.py: Multi-criteria explainable priority index (Need, Gain, Area, Confidence)       |
|      - ranking.py: Deterministic sorting, tie-breaking, non-discriminative rank suppression      |
|      - budget_allocation.py: Greedy cost-benefit planting budget optimizer                       |
|      - explainability.py: Rule-based ranking driver explanation generator                        |
|      - provenance.py: Data source lineage, SHA-256 checksums, and scientific limitation audit    |
|      - report_generation.py: GeoJSON, CSV metrics, CSV rankings, JSON summary, sanitized HTML    |
+--------------------------------------------------------------------------------------------------+
```

---

## 3. Detailed Data & Execution Flows

### Flow A: Application Startup
1. Backend launches via `backend.app.main:app` (Uvicorn).
2. Reads configuration from `backend.app.core.config:settings` (environment variables, pilot coordinates, upload directories).
3. Verifies that directory trees exist: `data/raw/`, `data/processed/`, `data/artifacts/`, `data/processed/recommendations/`.
4. Registers CORS middleware (local origins) and mounts four core API routers.
5. Frontend launches via `streamlit run frontend/app.py`, initializes `st.session_state`, and verifies API connectivity at `GET /health`.

### Flow B: API Request Flow
1. Client submits request (JSON body or Multipart file upload).
2. FastAPI validates payload against Pydantic schemas in `backend/app/schemas/`.
3. Validated parameters are passed to core calculation functions.
4. If invalid parameters, scoring weights, or unsupported missing-data policies are detected, the API returns a structured HTTP 400/422 response without leaking stack traces or internal paths.
5. Responses are serialized into standard Pydantic response models.

### Flow C: Geospatial-Processing Flow
1. Input raster ingested from `data/raw/real/wayanad_dem.tif` or uploaded GeoTIFF.
2. `inspect_geotiff` parses TIFF tags: dimensions, dtype, bounds, CRS, pixel scale, tiepoints, or 4x4 matrix transforms. Rejects rotated transforms (`ROTATED_TRANSFORM`).
3. `compute_elevation_stats` computes valid-pixel mask, min, max, mean, and median elevation.
4. `calculate_slope_and_aspect` computes 2D central differences:
   - For geographic WGS 84 degrees, applies geodesic metric scaling $meters\_per\_degree(\phi)$.
   - Derives continuous slope array in degrees and aspect azimuth ($0^\circ-360^\circ$).
5. Derived products are saved as continuous GeoTIFFs in `data/processed/real/` or `data/artifacts/`.

### Flow D: Geotechnical-Analysis Flow
1. Receives hillslope angle ($\beta$) and soil parameters ($c', \phi', \gamma, z, m$).
2. Validates physical parameter bounds in `parameter_validation.py`.
3. `calculate_infinite_slope_scalar` evaluates limit equilibrium:
   $$FS_0 = \frac{c' + (\sigma_n - u) \tan \phi'}{\tau}$$
4. If vegetation parameters are supplied ($T_r, RAR, K$), `calculate_root_cohesion` computes $\Delta C = K \cdot T_r \cdot RAR$.
5. `calculate_reinforced_slope_scalar` computes reinforced stability $FS_{root}$ and stability gain $\Delta FS$.
6. `calculate_required_cohesion_scalar` determines target cohesion required to reach $FS_{target} = 1.3$.
7. Output responses explicitly embed illustrative scenario notices and Wu-Waldron disclaimers.

### Flow E: Parcel Recommendation Flow
1. `generate_candidate_parcels` discretizes the study area bounding box (`11.55°N–11.65°N, 76.00°E–76.10°E`) into uniform grid parcels (default 300m cells).
2. Geodesic ellipsoidal area is computed for each polygon.
3. For each candidate parcel, `extract_parcel_zonal_statistics` samples raster layers (DEM, slope, aspect, NDVI, FS baseline, FS reinforced, FS delta, required cohesion, tree density).
4. `evaluate_parcel_eligibility` filters out steep cliffs ($>45^\circ$), statutory protected reserves, user exclusions, and parcels with insufficient terrain coverage ($<80\%$).
5. `calculate_parcel_score` evaluates multi-criteria priority score:
   - $S_{need}$ (Geotechnical Need)
   - $S_{gain}$ (Stability Improvement relative to $\Delta FS_{ref}$)
   - $S_{area}$ (Plantable Acreage relative to $Area_{ref}$)
   - $S_{conf}$ (Data Confidence)
6. `rank_candidate_parcels` deterministically sorts eligible parcels.
7. If active components lack variance across parcels, non-discriminative rank suppression activates (`is_discriminative = False`), replacing arbitrary ranks with ties and issuing clear explanatory warnings.

### Flow F: Export and Report-Generation Flow
1. Every recommendation run generates a unique timestamped `run_id`.
2. Generates 5 persistent artifacts:
   - `run_<id>_parcels.geojson`: RFC 7946 compliant FeatureCollection with full parcel metrics.
   - `run_<id>_parcel_metrics.csv`: Tabular raw zonal statistics for all candidate parcels.
   - `run_<id>_parcel_rankings.csv`: Priority ranking table for eligible parcels.
   - `run_<id>_summary.json`: JSON run summary with inventory, normalization settings, and disclosures.
   - `run_<id>_report.html`: Self-contained, styled HTML audit report with sanitized, XSS-escaped variables.
3. Artifacts are safely served through `/api/v1/recommendations/artifacts/{filename}` with strict path traversal isolation.

### Flow G: Frontend-to-Backend Interaction
1. Streamlit components query backend REST endpoints using HTTP GET/POST via `requests`.
2. Interactive Folium maps render candidate parcel geometries, coloring eligible parcels green and excluded parcels gray.
3. Recommendation controls allow users to tune grid cell size, eligibility thresholds, scoring weights, normalization divisors, and missing-data policies.
4. Non-discriminative ranking warnings and missing-data notices are prominently displayed in yellow callout banners.

### Flow H: Input and Output Data Locations

```
c:\TERRASHIELD AI\
├── data/
│   ├── sample/                                # Tracked synthetic test fixtures (Tier 1)
│   │   ├── demo_parcels.geojson               # 5 synthetic Cascade Foothills demo parcels
│   │   ├── synthetic_demo_dem.tif             # 10x10 synthetic elevation raster
│   │   ├── synthetic_s2_b04_red.tif           # Synthetic Sentinel-2 Red band
│   │   ├── synthetic_s2_b08_nir.tif           # Synthetic Sentinel-2 NIR band
│   │   └── sample_protected_areas.geojson     # Synthetic ecological reserve polygons
│   │
│   ├── raw/real/                              # Authoritative input rasters (Tier 2)
│   │   ├── wayanad_dem.tif                    # NASA SRTM NASADEM Global 1 Arc-Second (360x360)
│   │   ├── wayanad_b04_red.tif                # Sentinel-2 L2A Red Band (1099x1099)
│   │   └── wayanad_b08_nir.tif                # Sentinel-2 L2A NIR Band (1099x1099)
│   │
│   ├── processed/                             # Derived continuous rasters (Tier 3)
│   │   ├── real/
│   │   │   ├── wayanad_slope.tif              # Derived continuous slope raster (degrees)
│   │   │   ├── wayanad_aspect.tif             # Derived continuous aspect raster (azimuth)
│   │   │   └── wayanad_ndvi.tif               # Derived continuous NDVI raster
│   │   ├── geotechnical/
│   │   │   ├── wayanad_fs_baseline.tif        # Modeled baseline Factor of Safety
│   │   │   ├── wayanad_fs_reinforced.tif      # Modeled root-reinforced Factor of Safety
│   │   │   ├── wayanad_fs_delta.tif           # Modeled stability gain (ΔFS)
│   │   │   ├── wayanad_required_cohesion.tif  # Required additional root cohesion (kPa)
│   │   │   ├── wayanad_required_tree_density.tif # Required stem planting density (stems/ha)
│   │   │   └── wayanad_geotechnical_summary.json # Raster geotechnical summary & disclosures
│   │   └── recommendations/                   # Generated recommendation artifacts
│   │       ├── run_<id>_parcels.geojson
│   │       ├── run_<id>_parcel_metrics.csv
│   │       ├── run_<id>_parcel_rankings.csv
│   │       ├── run_<id>_summary.json
│   │       └── run_<id>_report.html
│   │
│   ├── uploads/                               # Temporary user uploads
│   └── artifacts/                             # Temporary image previews and raster slices
```

---

## 4. Architectural Boundaries & Non-Functional Guarantees

1. **Deterministic Reproducibility:** Identical parcel grids, scoring weights, and raster layers yield identical floating-point scores and rankings across all runs.
2. **Offline Autonomy:** Complete test suite (152 tests) and application workflows execute without remote internet access.
3. **Decoupled Architecture:** The FastAPI backend is wholly functional headlessly and does not depend on Streamlit runtime libraries.
4. **Pure-Python Geospatial Fallback:** Standard algorithms (Shoelace ellipsoidal projection, central-difference gradients, GeoTIFF readers) execute natively in Python without requiring proprietary or compiled GIS binaries.
