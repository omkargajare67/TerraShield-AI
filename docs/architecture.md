# TerraShield AI - Architecture Document (Phases 1 & 2)

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

## Phase 2 Implementation Architecture: Geospatial Data Engine

```
+-----------------------------------------------------------------------------------+
|                        Streamlit Frontend (app.py)                                |
|                                                                                   |
|  - Folium Interactive Map (Candidate parcels, status styling, spatial bounds)     |
|  - Prioritization Dashboard (KPI metrics, DataFrame table, GeoJSON/CSV exports)   |
|  - DEM & Terrain Engine Tab (Upload DEM, inspect metadata, compute slope & aspect)|
|  - Sentinel-2 NDVI Engine Tab (Upload Red B04 / NIR B08, calculate vegetation)    |
|  - Environmental Constraints Tab (SoilGrids validation, Protected Area exclusions)|
|  - Continuous GeoTIFF & Preview PNG Exporters                                     |
+------------------------------------+----------------------------------------------+
                                     | HTTP REST (Multipart Form & JSON)
                                     v
+-----------------------------------------------------------------------------------+
|                        FastAPI Backend (backend/app/main.py)                      |
|                                                                                   |
|  Endpoints:                                                                       |
|   - GET  /health                                 -> Service status & runtime mode |
|   - GET  /api/v1/parcels                         -> Demonstration GeoJSON features|
|   - POST /api/v1/analysis                        -> Leverage & exclusion solver   |
|   - GET  /api/v1/geospatial/status               -> Engine backend capabilities   |
|   - POST /api/v1/geospatial/dem/inspect          -> Metadata, CRS, bounds check   |
|   - POST /api/v1/geospatial/dem/terrain          -> Elevation, slope, aspect      |
|   - POST /api/v1/geospatial/ndvi                 -> Sentinel-2 NDVI calculation   |
|   - POST /api/v1/geospatial/soil/validate        -> SoilGrids metadata validator  |
|   - POST /api/v1/geospatial/vectors/validate     -> Vector GeoJSON validator      |
|   - POST /api/v1/geospatial/vectors/intersections-> Protected Area spatial tests  |
|   - GET  /api/v1/geospatial/artifacts/{id}       -> Secure GeoTIFF/PNG downloads  |
+------------------------------------+----------------------------------------------+
                                     |
                                     v
+------------------------------------+----------------------------------------------+
|                   Geospatial Data Engine & Core Services                          |
|                                                                                   |
|  - raster_loader.py:                                                              |
|      - GeoTIFF inspection (width, height, bands, dtype, nodata, CRS, bounds)      |
|      - GeoTIFF writer with georeferencing tags (PixelScale, Tiepoint, ASCII CRS)  |
|  - terrain.py:                                                                    |
|      - Elevation statistics (min, max, mean, median, valid count)                 |
|      - 2D Central-difference gradient slope in degrees: arctan(sqrt(dx²+dy²))     |
|      - Geodesic scaling for geographic WGS84 degree inputs                        |
|      - Aspect azimuth from North (0°-360°), flat terrain flagged as -1.0°         |
|      - 3-Panel Matplotlib preview generation (Elevation, Slope, Aspect)           |
|  - ndvi.py:                                                                       |
|      - Grid compatibility validation                                              |
|      - NDVI = (NIR - Red) / (NIR + Red) with zero-denominator protection          |
|      - Continuous GeoTIFF export and RdYlGn preview generation                    |
|  - vector_loader.py:                                                              |
|      - Shapely geometry validation and coordinate bounds calculation              |
|      - Spatial intersection tests between parcels and protected statutory reserves|
|  - soil_data.py:                                                                  |
|      - ISRIC SoilGrids standard parameters validation without fabricating data    |
|  - coordinate_systems.py:                                                         |
|      - Pure-Python geodesic ellipsoidal scaling and UTM projection support        |
+-----------------------------------------------------------------------------------+
```

---

## 5-Phase Project Roadmap

1. **Phase 1: Foundation & Working Prototype (Complete)**
   - Decoupled FastAPI backend and Streamlit frontend.
   - Deterministic 5-parcel sample watershed dataset.
   - Robust $L = \Delta R / N$ formula evaluation with zero-division handling.
   - Preserved and explicit exclusion reasoning.
2. **Phase 2: Geospatial Data Engine (Complete)**
   - Ingestion and metadata validation of Digital Elevation Models (GeoTIFF).
   - Real gradient-based slope calculation in degrees (with geodesic latitude scaling).
   - Terrain aspect calculation as azimuth degrees from North.
   - Sentinel-2 Red and NIR band ingestion and NDVI computation.
   - SoilGrids metadata validation and vector protected-area intersection checks.
   - Secure artifact downloads and visual preview generation.
3. **Phase 3: Geotechnical Intelligence Engine (Next Phase)**
   - Infinite slope stability equation solving for Factor of Safety ($FS$).
   - Wu-Waldron root-cohesion model ($\Delta C$) integration.
   - Surface temperature raster integration for urban-heat island mitigation.
4. **Phase 4: Spatial Recommendation Engine**
   - Live multi-spectral Copernicus Sentinel-2 NDVI time-series monitoring.
   - ISRIC SoilGrids spatial raster sampling.
   - Official World Database on Protected Areas (WDPA) vector exclusion masking.
5. **Phase 5: Multi-Criteria Optimization, Validation & Production Release**
   - Pareto multi-objective optimization across risk reduction, planting cost, and biodiversity.
   - Cloud containerization, automated testing, and production deployment.
