# TerraShield AI — Real-Data Acceptance and Phase 2 Validation Report

**Date:** 2026-10-11  
**Target Pilot Study Corridor:** Western Ghats Mountain Corridor (Wayanad Watershed, Kerala, India)  
**Git Branch:** `feature/phase-2-geospatial-engine`  
**Latest Hardening Commit:** `a10887c`  
**Test Suite Status:** 66 Automated Tests Passing (0 Failures)  

---

## 1. Datasets Inspected and Processing Status

In accordance with Step 1 and the project guidelines ("*If a dataset is missing, report it as missing. Do not generate synthetic substitutes and present them as real data.*"):

| Expected Dataset Path | Expected Source / Purpose | Status | Notes |
|---|---|---|---|
| `data/raw/real/wayanad_dem.tif` | NASA SRTM 1-arc-second (30m) or Copernicus 30m DEM for Wayanad, Kerala | **MISSING** | No genuine elevation raster provided in workspace. Directory `data/raw/real/` created for user dataset staging. |
| `data/raw/real/wayanad_b04_red.tif` | Sentinel-2 L2A BOA Red Band (10m) for Wayanad, Kerala | **MISSING** | No genuine Level-2A Red band provided in workspace. |
| `data/raw/real/wayanad_b08_nir.tif` | Sentinel-2 L2A BOA NIR Band (10m) for Wayanad, Kerala | **MISSING** | No genuine Level-2A NIR band provided in workspace. |

**Summary of Real Files Processed:** **0 real files processed.**  
No synthetic test files were fabricated or misrepresented as real observations. The synthetic fixtures (`synthetic_demo_dem.tif`, `synthetic_s2_b04_red.tif`, `synthetic_s2_b08_nir.tif` in `data/sample/`) remain strictly classified as **Tier 1 Synthetic Test Fixtures**.

---

## 2. Verified Metadata and Provenance

Because real datasets have not yet been deposited by the user, verified provenance for real environmental data is **Pending External Input**.

When real datasets are placed in `data/raw/real/`, the following metadata must be documented:
- **NASA SRTM DEM (`wayanad_dem.tif`):**
  - Source: USGS EarthExplorer / NASA Earthdata (SRTM 1 Arc-Second Global V003).
  - Geographic Bounds: ~`11.40° N – 11.95° N`, `75.80° E – 76.40° E` (Wayanad District).
  - Target CRS: `EPSG:32643` (UTM Zone 43N) or `EPSG:4326` (WGS84).
  - Expected Dtype: Signed 16-bit integer (`int16`).
  - Expected Nodata: `-32768`.
- **Sentinel-2 L2A Bands (`wayanad_b04_red.tif`, `wayanad_b08_nir.tif`):**
  - Source: Copernicus Data Space Ecosystem (Level-2A Bottom-of-Atmosphere).
  - Recommended Tile: Tile `43PGT` or `43PFT` (covering Wayanad escarpment).
  - Acquisition Window: Post-monsoon cloud-free window (Dec – Feb).
  - Expected Dtype: `uint16` (Digital Numbers 0–10,000) or scaled `float32`.
  - Resolution: 10m x 10m native pixel size.

---

## 3. Terrain-Processing Verification

### Engine Readiness
The Phase 2 terrain processing engine (`backend/app/core/geospatial/terrain.py`) was hardened and verified across:
1. **Signed `int16` Casting:** Elevation arrays are converted to `float64` before gradient evaluation, avoiding arithmetic underflow on SRTM data.
2. **Directional Slope & Aspect Verification:**
   - Northward gradient: Aspect = $0.0^\circ$ (steepest descent North).
   - Eastward gradient: Aspect = $90.0^\circ$ (steepest descent East).
   - Westward gradient: Aspect = $270.0^\circ$ (steepest descent West).
   - Southwest gradient: Aspect = $225.0^\circ$.
   - Northwest gradient: Aspect = $315.0^\circ$.
   - Flat terrain: Aspect = $-1.0^\circ$, Slope = $0.0^\circ$.
3. **Geodesic Ellipsoidal Scaling:** WGS84 geographic coordinate inputs undergo meridian and parallel scale corrections based on central latitude.
4. **Real DEM Outcome:** **Pending** provision of genuine `wayanad_dem.tif`.

---

## 4. NDVI-Processing Verification

### Engine Readiness
The Sentinel-2 NDVI processing module (`backend/app/core/geospatial/ndvi.py`) was tested and verified for:
1. **Grid Compatibility:** Rejects mismatched pixel dimensions, spatial bounds, or Coordinate Reference Systems with HTTP 400.
2. **Zero-Denominator Safety:** Cells where $NIR + Red \le 0$ are isolated and set to nodata (`-9999.0`).
3. **Mathematical Range Clamping:** Output index values are strictly clamped to $[-1.0, 1.0]$.
4. **Cloud Masking Assumption:** No cloud masking was claimed or executed because no Scene Classification Layer (SCL) or cloud mask was supplied.
5. **Real NDVI Outcome:** **Pending** provision of genuine Wayanad Red and NIR bands.

---

## 5. QGIS Comparison Status

- **Host Environment Check:** Neither QGIS (`qgis.exe`) nor standalone GDAL CLI (`gdaldem`) is installed in the local system PATH or Program Files.
- **Status:** **PENDING INDEPENDENT GIS SOFTWARE.**
- **Benchmark Procedure for Future Session:**
  When QGIS is available on a GIS workstation:
  1. Open QGIS and load `wayanad_dem.tif`.
  2. Run `Raster -> Analysis -> Slope...` (Z-factor = 1.0, Degrees).
  3. Run `Raster -> Analysis -> Aspect...` (Azimuth 0°–360° from North).
  4. Compare pixel-by-pixel with TerraShield's exported `slope_{id}.tif` and `aspect_{id}.tif`.
  5. Compute Mean Absolute Error (MAE) and report the percentage of pixels within $\pm 0.5^\circ$ tolerance.

---

## 6. Dashboard & API Verification

The Streamlit UI (`frontend/app.py`) and FastAPI backend (`backend/app/api/geospatial_routes.py`) were validated:
- **DEM Inspect Endpoint:** Successfully parses metadata and returns HTTP 400 on invalid file types.
- **Terrain Processing Endpoint:** Computes statistics, exports GeoTIFFs, and generates 3-panel preview PNGs.
- **NDVI Endpoint:** Enforces grid alignment and returns HTTP 400 on mismatched inputs.
- **Artifact Downloads:** Traversal-safe downloads via `/api/v1/geospatial/artifacts/{id}` tested and verified (path traversal returns HTTP 400/404; non-existent files return HTTP 404).

---

## 7. Test Results

The complete automated test suite was executed:
```powershell
.\.venv\Scripts\pytest.exe -v
```

**Results:**
- **66 passed**, 1 warning in 2.73s.
- 26 tests cover Phase 1 Foundation, APIs, and GeoJSON parcels.
- 40 tests cover Phase 2 Geospatial Engine (raster inspection, 4x4 matrix transforms, signed `int16` SRTM, unsigned `uint16` S2, rotated transform rejection, directional aspect gradients, boundary nodata, NDVI zero-denominator and grid alignment, SoilGrids validation, vector spatial intersection, and API error handling).

---

## 8. Output Artifact Locations

- Artifacts Directory: `data/artifacts/` (configured in `.gitignore`).
- Temporary Uploads Directory: `data/uploads/` (configured in `.gitignore`).
- Real Data Staging Directory: `data/raw/real/` (created for user dataset ingestion).
- Tracked Synthetic Fixtures: `data/sample/` (`synthetic_demo_dem.tif`, `synthetic_s2_b04_red.tif`, `synthetic_s2_b08_nir.tif`, `demo_parcels.geojson`, `sample_protected_areas.geojson`).

---

## 9. Remaining Limitations

1. **Absence of Real Input Rasters:** Verification on real Western Ghats datasets cannot be completed until genuine GeoTIFF files are placed in `data/raw/real/`.
2. **Independent GIS Comparison:** QGIS or GDAL comparison remains pending until executed in an environment with GIS desktop tools installed.
3. **Rotated Geotransforms:** Oblique/rotated rasters are rejected with `status="ROTATED_TRANSFORM"` and must be pre-rectified.
4. **Physical Terrain vs. Landslide Risk:** The slope raster is a physical terrain angle map, not a validated geotechnical landslide hazard map (scheduled for Phase 3).

---

## 10. Real-Data Acceptance Status

> **CRITICAL DETERMINATION: REAL-DATA ACCEPTANCE IS INCOMPLETE / PENDING.**
>
> In strict compliance with the task specification:
> - *Do not declare real-data acceptance complete without processing at least one genuine DEM and checking its output.*
> - *Do not declare independent comparison complete without performing the comparison.*
>
> Because no genuine real-world DEM or Sentinel-2 observations have been supplied to the workspace, **real-data acceptance cannot and must not be declared complete**.
> 
> The geospatial data engine is **fully hardened, verified, and technically prepared** to ingest and process real datasets as soon as they are supplied.

---

## 11. Prerequisites Before Beginning Phase 3

Before proceeding to **Phase 3 (Geotechnical Intelligence Engine)**:
1. Place genuine SRTM 30m DEM (`wayanad_dem.tif`) and Sentinel-2 L2A Red/NIR GeoTIFFs (`wayanad_b04_red.tif`, `wayanad_b08_nir.tif`) into `data/raw/real/`.
2. Execute the processing workflow documented in `docs/real_data_acceptance_workflow.md`.
3. If QGIS is available, perform the numeric difference comparison for slope and aspect.
4. Once verified on real data, proceed with Phase 3 geotechnical modeling (Factor of Safety, Wu-Waldron root-cohesion).
