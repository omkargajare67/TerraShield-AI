# TerraShield AI — Real-Data Acceptance & Verification Workflow

This document provides exact, reproducible procedures for sourcing, verifying, and ingesting genuine environmental datasets into the TerraShield AI Geospatial Data Engine.

---

## 1. Intended Project Study Region: Western Ghats Corridor

TerraShield AI is designed to support reforestation planning in the **Western Ghats Mountain Corridor (India)**, a UNESCO World Heritage biodiversity hotspot experiencing monsoon-triggered shallow landslides, debris flows, and severe soil loss.

- **Pilot Region:** Western Ghats Corridor (encompassing high-risk sectors across Idukki, Wayanad, and Nilgiris).
- **Geographic Bounding Box:** `9.20° N – 12.00° N`, `75.80° E – 77.50° E`.
- **Recommended Projected CRS:** `EPSG:32643 (WGS 84 / UTM Zone 43N)`.
- **Primary Failure Mechanism:** Heavy rainfall saturation triggering translational shallow slips at soil-bedrock interfaces (15°–45° slope gradients).

---

## 2. Three-Tier Data Provenance Model

To ensure transparency and prevent synthetic artifacts from impersonating ground truth:

| Tier | Category | Description | Storage Location |
|---|---|---|---|
| **Tier 1** | **Synthetic Test Data** | Deterministic fixtures generated for CI/CD test automation (Cascade Foothills demo parcels, 10x10 test rasters). | `data/sample/` |
| **Tier 2** | **Real Environmental Observations** | Genuine satellite imagery, elevation models, soil property maps, and official protected reserve boundaries. | `data/raw/` or `data/uploads/` |
| **Tier 3** | **Derived Geospatial Products** | Continuous GeoTIFFs and vector masks computed deterministically from verified Tier 2 inputs (Slope, Aspect, NDVI). | `data/processed/` & `data/artifacts/` |

---

## 3. Real-Data Ingestion Specifications

### A. Digital Elevation Model (DEM)
- **Source:** NASA SRTM 1 Arc-Second (30m) Global DEM or USGS 3DEP / ALOS PALSAR RTC.
- **Expected Input Format:** GeoTIFF (`.tif`, `.tiff`), uncompressed or LZW/DEFLATE compressed.
- **Data Type:** Signed 16-bit integer (`int16`, standard SRTM elevation in meters) or 32-bit float (`float32`).
- **Required Spatial Metadata:**
  - Standard GeoTIFF tags: `ModelPixelScaleTag` (33550) + `ModelTiepointTag` (33922), OR 4x4 `ModelTransformationTag` (34264).
  - CRS Definition: `GeoKeyDirectoryTag` (34735) or `GeoAsciiParamsTag` (34737).
- **CRS Requirements:** Projected CRS preferred (`EPSG:32643`). If supplied in geographic degrees (`EPSG:4326`), TerraShield applies local geodesic ellipsoidal scaling to calculate metric slope angles accurately.
- **Elevation Units:** Meters above mean sea level (EGM96 vertical datum for SRTM).
- **Validation Checks Performed:**
  - Bounding box and dimensions validation.
  - Zero/negative pixel resolution rejection (`INVALID_RESOLUTION`).
  - Rotated grid detection (`ROTATED_TRANSFORM` warning).
  - Nodata isolation (`-32768` or `-9999`).
- **Expected Outputs:**
  - Elevation statistics: Min, Max, Mean, Median, and valid cell count.
  - Continuous Slope GeoTIFF in degrees (`0°–90°`).
  - Continuous Aspect GeoTIFF as azimuth from North (`0°–360°`, flat terrain recorded as `-1.0°`).
  - 3-Panel Visual Preview PNG (`data/artifacts/`).

---

### B. Copernicus Sentinel-2 Multispectral Vegetation Imagery
- **Source:** Copernicus Data Space Ecosystem (Sentinel-2 Level-2A Bottom-Of-Atmosphere surface reflectance).
- **Expected Input Bands:**
  - Band 4 (Red, 665 nm, 10m native resolution, filename pattern `*B04_10m.jp2` or converted `.tif`).
  - Band 8 (Near-Infrared, 842 nm, 10m native resolution, filename pattern `*B08_10m.jp2` or converted `.tif`).
- **Data Type:** Unsigned 16-bit integer (`uint16`, standard Sentinel-2 Digital Numbers where $\text{Reflectance} = \text{DN} / 10000$) or Float (`float32`).
- **Required Spatial Metadata:** Identical coordinate reference systems, matching bounding coordinates, and identical raster dimensions.
- **Validation Checks Performed:**
  - Dimensional grid equality (`red.shape == nir.shape`).
  - Spatial bounding box alignment (`abs(red_bounds - nir_bounds) < 1.0m`).
  - CRS consistency check (`red_crs == nir_crs`).
  - Zero-denominator protection ($\text{NIR} + \text{Red} \le 0$ masked as nodata `-9999.0`).
- **Expected Outputs:**
  - Continuous NDVI GeoTIFF with values constrained to $[-1.0, 1.0]$.
  - Summary metrics: Min, Max, Mean, valid vegetation cells, zero-denominator count.
  - Reduced-resolution `RdYlGn` preview PNG.
- **Known Limitations:**
  - If source granules lack a valid Scene Classification Layer (SCL) cloud mask, cloud tops (high reflectance in both Red and NIR) and cloud shadows will skew vegetation indices.

---

### C. Protected-Area Boundary Vectors
- **Source:** World Database on Protected Areas (WDPA) / Protected Planet (IUCN Categories I–VI).
- **Expected Input Format:** Standard GeoJSON (`.geojson`, `.json`) FeatureCollection.
- **Geometry Types:** `Polygon` and `MultiPolygon`.
- **Required Attribute Fields:** `name` / `NAME` (Reserve designation), `DESIG` / `designation` (Statutory status).
- **Validation Checks Performed:**
  - Topological validity via Shapely (`geom.is_valid`).
  - Coordinate convention ordering (`[longitude, latitude]`).
  - Spatial intersection tests with candidate parcels.
- **Expected Outputs:**
  - Tabular list of parcels intersecting statutory reserves.
  - Overlapping area in hectares.
  - Preserved legal designation rationale preventing mechanical planting interventions.

---

### D. Soil Dataset Ingestion
- **Source:** ISRIC SoilGrids 250m v2.0 Global Soil Information System.
- **Expected Soil Properties:**
  - `clay`: Clay content (< 2 μm), standard unit `g/kg`.
  - `silt`: Silt content (2–50 μm), standard unit `g/kg`.
  - `sand`: Sand content (50–2000 μm), standard unit `g/kg`.
  - `bdod`: Bulk density of the fine earth fraction, standard unit `cg/cm³` or `kg/m³`.
  - `soil_depth`: Soil mantle depth to bedrock, standard unit `cm`.
- **Depth Intervals:** Standard SoilGrids depths (`0-5cm`, `5-15cm`, `15-30cm`, `30-60cm`, `60-100cm`, `100-200cm`).
- **Validation Checks Performed:**
  - Property nomenclature matching against recognized pedological parameters.
  - Unit consistency check.
  - Spatial coordinate presence for tabular sampling points.
- **Known Limitations:**
  - Phase 2 performs data validation and metadata harmonization. Geotechnical shear strength parameters (internal friction angle $\phi'$, effective cohesion $c'$) will be calculated in Phase 3.

---

## 4. Current Verification Status

- **Automated Synthetic Suite:** **62 passing automated tests**, validating all mathematical and geospatial logic.
- **Real Environmental Dataset Execution:** **Pending user-supplied real-world data files.**
- No large real-world satellite or elevation datasets have been committed or downloaded automatically into the repository.
