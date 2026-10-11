# TerraShield AI - Architecture Document (Phase 1)

## Overview
TerraShield AI is an AI-assisted geospatial decision-support platform designed to prioritize reforestation interventions for:
1. **Landslide Risk Mitigation:** Stabilizing unstable slopes through root-cohesion reinforcement.
2. **Air-Quality Buffers:** Filtering particulate matter via vegetative canopy placement.
3. **Urban Heat Mitigation:** Alleviating urban heat islands through strategic urban forestry.

The central prioritization metric across candidate planting sites is the **Leverage Score**:

$$L = \frac{\Delta R}{N}$$

Where:
- $\Delta R$: Modeled risk reduction achieved by the vegetative intervention.
- $N$: Number of trees required for the intervention footprint.

---

## Phase 1 Implementation Architecture

```
+-------------------------------------------------------------------------+
|                        Streamlit Frontend (app.py)                      |
|                                                                         |
|  - Folium Interactive Map (Polygon rendering, status styling, bounds)   |
|  - Prioritization Dashboard (KPI metric cards, ranked DataFrame table)   |
|  - Export Module (GeoJSON & CSV file generators)                        |
|  - Parameter Controls (Scenario selection, Risk threshold sliders)      |
+------------------------------------+------------------------------------+
                                     | HTTP Requests (REST JSON)
                                     v
+-------------------------------------------------------------------------+
|                         FastAPI Backend (main.py)                       |
|                                                                         |
|  Endpoints:                                                             |
|   - GET  /health              -> Service status and runtime mode        |
|   - GET  /api/v1/parcels      -> Demonstration GeoJSON features         |
|   - POST /api/v1/analysis     -> Prioritization & exclusion solver      |
+------------------------------------+------------------------------------+
                                     |
                                     v
+------------------------------------+------------------------------------+
|                      Core Analysis Engine & Data                        |
|                                                                         |
|  - analysis_service.py:                                                 |
|      - evaluate_parcel_eligibility(props, min_threshold)                |
|      - calculate_leverage_score(delta_risk, tree_count)                 |
|      - run_demonstration_analysis(request)                              |
|  - demo_data.py / demo_parcels.geojson:                                 |
|      - 5 deterministic synthetic candidate parcels                      |
|      - Simulated wilderness reserve & shallow bedrock constraints       |
+-------------------------------------------------------------------------+
```

---

## 5-Phase Roadmap

1. **Phase 1 (Current):** Foundation & Working Prototype.
   - Clean decoupled architecture (FastAPI + Streamlit + Folium).
   - Deterministic sample GeoJSON dataset in illustrative watershed.
   - Robust $L = \Delta R / N$ formula evaluation with zero-division handling.
   - Preserved and explicit exclusion reasoning.
   - 100% automated test coverage.
2. **Phase 2 (Planned):** Terrain Ingestion & Real Geospatial Data.
   - NASA SRTM 30m DEM raster pipeline.
   - Slope angle, aspect, flow accumulation computation.
   - Real GeoPandas and Rasterio spatial joins.
3. **Phase 3 (Planned):** Geotechnical Slope Stability & Urban Heat.
   - Infinite slope stability equation ($FS$).
   - Wu-Waldron root-cohesion modeling ($\Delta C$).
   - Surface temperature raster integration for urban heat scenarios.
4. **Phase 4 (Planned):** Environmental Constraints & Satellite Monitoring.
   - Copernicus Sentinel-2 NDVI time-series.
   - ISRIC SoilGrids texture and bulk density ingestion.
   - World Database on Protected Areas (WDPA) vector masks.
5. **Phase 5 (Planned):** Production Deployment, Optimization & Multi-Criteria AI.
   - Multi-objective Pareto optimization across risk, cost, and biodiversity.
   - Cloud containerization and automated CI/CD.
