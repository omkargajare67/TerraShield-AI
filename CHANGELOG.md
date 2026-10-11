# TerraShield AI - Project Changelog

All notable changes to TerraShield AI across all project phases are documented in this file.

---

## [1.0.0-rc1] - Phase 5: Validation, Integration & Release Candidate

### Added
- **Phase 5 End-to-End Integration Test Suite (`backend/tests/test_phase5_integration.py`):**
  - Added 20 comprehensive automated tests covering application health contracts, geospatial data flow, geotechnical physics, complete recommendation pipeline, missing-data policies, non-discriminative ranking suppression, export consistency, and frontend schema alignment.
  - Workspace test suite expanded to **152 passing tests, 0 failures**.
- **Local Windows PowerShell Developer Scripts (`scripts/`):**
  - `scripts/start_backend.ps1`: Automated FastAPI Uvicorn launcher with `.venv` check and dependency verification.
  - `scripts/start_frontend.ps1`: Automated Streamlit geospatial dashboard launcher.
  - `scripts/run_tests.ps1`: Full automated pytest test suite runner with exit-code propagation.
  - `scripts/smoke_test.ps1`: Complete operational sanity and smoke verification harness.
  - `scripts/benchmark_phase5.py`: Performance benchmarking script for local hardware profiling.
- **Release Documentation (`docs/`):**
  - `docs/phase5_validation_report.md`: Formal verification audit report across software, data, scientific, and operational readiness dimensions.
  - `docs/local_setup.md`: Complete Windows PowerShell local developer setup guide from fresh checkout.
  - `docs/architecture.md`: Comprehensive system architecture and internal integration map (Flows A–H).

### Security & Hardening
- **HTML Injection & XSS Defense:** Sanitized all interpolated strings (`parcel_id`, `run_id`, `differentiation_warning`, disclosures, scenario notes) in `export_recommendation_report_html` using Python's `html.escape`.
- **API Contract Hardening:** Added explicit HTTP 400 validation for all-zero or non-positive scoring weights and unsupported missing-data policy strings in `/api/v1/recommendations/run`.
- **Path Traversal Isolation:** Verified strict containment of artifact downloads to `data/artifacts/` using `os.path.basename` and `Path.relative_to`.

### Performance & Benchmarks
- Profiled actual local hardware performance:
  - App initialization: **0.73 s**
  - DEM ingestion ($360 \times 360$ px): **0.002 s**
  - Terrain slope/aspect processing: **0.42 s**
  - Sentinel-2 NDVI calculation ($1099 \times 1099$ px): **0.33 s**
  - Candidate parcel grid generation (1,369 parcels): **0.017 s**
  - Complete recommendation pipeline run (1,369 parcels): **0.62 s**
  - Multi-format report generation (GeoJSON, CSVs, JSON, HTML): **0.009 s**

---

## [0.4.0] - Phase 4: Spatial Recommendation Engine

### Added
- **Candidate Parcel Generator:** Discretized pilot extent into uniform grid cells ($100\text{ m} - 1,000\text{ m}$, default $300\text{ m}$) using WGS 84 ellipsoidal curvatures ($M, N$).
- **Multi-Resolution Zonal Statistics:** Fast bounding-box sampling across DEM, slope, aspect, NDVI, and geotechnical Factor of Safety rasters without resampling.
- **Rule-Based Eligibility Engine:** Enforced physical slope ($>45^\circ$), administrative reserve, user exclusion, and minimum plantable area filters.
- **Multi-Criteria Priority Scoring:** Formulated explainable priority index ($0–100$) based on Geotechnical Need ($35\%$), Modeled Stability Gain ($30\%$), Plantable Acreage ($20\%$), and Data Confidence ($15\%$).
- **Non-Discriminative Ranking Suppression:** Suppressed arbitrary ordinal ranks when active components exhibit zero variance, replacing false precision with explicit tie warnings.
- **Missing-Data Policies:** Implemented `RENORMALIZE_AVAILABLE`, `ZERO_FILL`, and `BLOCK_UNAVAILABLE` policies.
- **Greedy Planting Budget Optimizer:** Allocated sapling planting budgets and parcel setup costs.
- **Multi-Format Export Generators:** Generated RFC 7946 GeoJSON, CSV metrics, CSV rankings, JSON summary, and self-contained HTML audit reports.

---

## [0.3.0] - Phase 3: Geotechnical Intelligence Engine

### Added
- **Limit-Equilibrium Infinite Slope Solver:** Evaluated planar translational shear failure, normal stress ($\sigma_n, \sigma'_n$), shear stress ($\tau$), and baseline Factor of Safety ($FS_0$).
- **Wu-Waldron Root Cohesion Solver:** Modeled additional root cohesion ($\Delta C = K \cdot T_r \cdot RAR$) and root-reinforced Factor of Safety ($FS_{root}$).
- **Target Cohesion Solver:** Solved minimum additional cohesion required to reach $FS_{target} = 1.3$, verified with numerical re-substitution ($|FS_{check} - 1.3| \le 10^{-4}$).
- **Calibrated Tree-Density Estimator:** Translated required Root Area Ratio into stem density ($stems/ha$) strictly when supported by empirical calibration data.
- **Parameter Sensitivity Sweeps:** Evaluated stability response across physical soil and root parameter ranges.
- **Real Wayanad Slope Raster Processing:** Evaluated 129,600 pixels of native WGS 84 Wayanad terrain.

---

## [0.2.0] - Phase 2: Geospatial Data Engine

### Added
- **GeoTIFF Ingestion & Validation:** Pure-Python TIFF tag parser supporting pixel scale, tiepoints, and 4x4 affine matrix transformations.
- **Rotated Grid Detection:** Explicitly flagged rotated non-north-up rasters.
- **Topographic Terrain Processing:** 2D central-difference slope and aspect azimuth calculations with geodesic degree-to-meter scaling.
- **Sentinel-2 NDVI Processor:** Ingested Red (B04) and NIR (B08) bands with dimension validation and zero-denominator safety.
- **Real Environmental Data Acceptance:** Validated genuine NASA SRTM NASADEM Global 1 Arc-Second V001 dataset (`NASADEM_HGT_n11e076`, SHA-256 `680aa3cb46f4b7d148b2d62224ff8f8daa9591dcee5921d46c0f8c4c8a5ca2b6`).
- **Protected-Area Spatial Intersection:** Shapely-based polygon intersection tests for statutory reserve exclusions.

---

## [0.1.0] - Phase 1: Foundation and Working Prototype

### Added
- Decoupled FastAPI backend and Streamlit frontend.
- Interactive Folium map with synthetic Cascade Foothills candidate parcels.
- Demonstration leverage formula ($L = \Delta R / N$).
- Basic statutory reserve and soil depth exclusion filters.
- CSV and GeoJSON tabular data export.
