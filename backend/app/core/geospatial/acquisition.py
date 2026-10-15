"""Automatic Geospatial Data Acquisition & Pipeline Runner for TerraShield AI.

Provides one-click discovery, retrieval, validation, and processing of openly
accessible elevation (Copernicus DEM GLO-30 / NASA SRTM NASADEM) and multispectral
imagery (Copernicus Sentinel-2 L2A) via Microsoft Planetary Computer STAC APIs.
"""

import hashlib
import io
import json
import logging
import math
import os
import shutil
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import httpx
import numpy as np
import tifffile
from shapely.geometry import Polygon, box, mapping, shape
from shapely.ops import unary_union

from backend.app.core.config import settings
from backend.app.core.geospatial.coordinate_systems import get_meters_per_degree
from backend.app.core.geospatial.ndvi import calculate_ndvi_array
from backend.app.core.geospatial.raster_loader import (
    inspect_geotiff,
    validate_and_inspect_uploaded_raster,
    write_geotiff,
)
from backend.app.core.geospatial.terrain import process_dem_terrain
from backend.app.core.geotechnical.models import RootParameters, SoilParameters
from backend.app.core.geotechnical.raster_analysis import process_geotechnical_raster
from backend.app.core.projects.project_models import (
    ProjectMetadata,
    STANDARD_GEOTECHNICAL_PRESETS,
)
from backend.app.core.projects.project_service import PROJECTS_DIR, ProjectService
from backend.app.core.recommendations.spatial_reference import (
    calculate_polygon_geodesic_area,
    degrees_to_meters,
)

logger = logging.getLogger(__name__)

# Planetary Computer Public STAC & Data APIs (No API key required)
STAC_API = "https://planetarycomputer.microsoft.com/api/stac/v1"
DATA_API = "https://planetarycomputer.microsoft.com/api/data/v1"
SAS_API = "https://planetarycomputer.microsoft.com/api/sas/v1"

CACHE_DIR = settings.BASE_DIR / "data" / "cache" / "geospatial"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Operational limits for study areas
MIN_AREA_HA = 1.0  # Minimum 1 hectare for micro-catchment analysis
MAX_AREA_HA = 25000.0  # Maximum 25,000 hectares (250 km²) for responsive analysis


def calculate_file_sha256(filepath: Path) -> str:
    """Calculate the SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


# -------------------------------------------------------------------------
# AOI & Boundary Validation
# -------------------------------------------------------------------------

def validate_aoi(
    boundary_geojson: Optional[Dict[str, Any]] = None,
    bounds: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Validate and sanitize an Area of Interest (AOI).

    Accepts either a GeoJSON polygon/feature or a bounding box dictionary.
    Verifies coordinate limits, geometry validity, and area constraints.

    Returns:
        Dict with keys:
          - is_valid: bool
          - bounds: Dict[str, float] with minx, miny, maxx, maxy
          - boundary_geojson: GeoJSON FeatureCollection
          - area_ha: float
    """
    poly_geom = None

    if boundary_geojson:
        # Extract geometry from FeatureCollection, Feature, or Geometry
        geom_dict = None
        if "features" in boundary_geojson:
            feats = boundary_geojson.get("features", [])
            if not feats:
                raise ValueError("GeoJSON FeatureCollection contains no features.")
            geoms = [shape(f["geometry"]) for f in feats if f.get("geometry")]
            if not geoms:
                raise ValueError("GeoJSON features contain no valid geometries.")
            poly_geom = unary_union(geoms)
        elif "geometry" in boundary_geojson:
            poly_geom = shape(boundary_geojson["geometry"])
        elif "coordinates" in boundary_geojson:
            poly_geom = shape(boundary_geojson)
        else:
            raise ValueError("Unrecognized GeoJSON format for study boundary.")

    elif bounds:
        minx = float(bounds.get("minx", bounds.get("min_lon", 0.0)))
        miny = float(bounds.get("miny", bounds.get("min_lat", 0.0)))
        maxx = float(bounds.get("maxx", bounds.get("max_lon", 0.0)))
        maxy = float(bounds.get("maxy", bounds.get("max_lat", 0.0)))
        if minx >= maxx or miny >= maxy:
            raise ValueError(f"Invalid bounding box: min coordinates ({minx}, {miny}) must be strictly less than max ({maxx}, {maxy}).")
        poly_geom = box(minx, miny, maxx, maxy)
    else:
        raise ValueError("Either boundary_geojson or bounds must be provided.")

    if poly_geom is None or poly_geom.is_empty:
        raise ValueError("Selected area geometry is empty.")

    # Fix minor self-intersections if present
    if not poly_geom.is_valid:
        poly_geom = poly_geom.buffer(0)
        if not poly_geom.is_valid:
            raise ValueError("Selected area boundary is self-intersecting or topologically invalid.")

    minx, miny, maxx, maxy = poly_geom.bounds

    # Coordinate domain validation (WGS 84)
    if not (-180.0 <= minx <= 180.0 and -180.0 <= maxx <= 180.0):
        raise ValueError(f"Longitude coordinates [{minx:.4f}, {maxx:.4f}] are outside valid WGS 84 range [-180, 180].")
    if not (-90.0 <= miny <= 90.0 and -90.0 <= maxy <= 90.0):
        raise ValueError(f"Latitude coordinates [{miny:.4f}, {maxy:.4f}] are outside valid WGS 84 range [-90, 90].")

    # Geodesic area calculation
    if poly_geom.geom_type == "Polygon":
        coords = list(poly_geom.exterior.coords)
        area_ha = calculate_polygon_geodesic_area(coords)
    elif poly_geom.geom_type == "MultiPolygon":
        area_ha = sum(calculate_polygon_geodesic_area(list(p.exterior.coords)) for p in poly_geom.geoms)
    else:
        # Fallback to envelope bounding box area
        coords = list(box(minx, miny, maxx, maxy).exterior.coords)
        area_ha = calculate_polygon_geodesic_area(coords)

    if area_ha < MIN_AREA_HA:
        raise ValueError(
            f"Selected area is {area_ha:.2f} ha, which is below the minimum limit of {MIN_AREA_HA:.1f} ha. "
            "Please select a slightly larger hillslope or watershed section."
        )

    if area_ha > MAX_AREA_HA:
        raise ValueError(
            f"Selected area is {area_ha:.1f} ha (~{area_ha / 100:.1f} km²), which exceeds the maximum supported "
            f"limit of {MAX_AREA_HA:.0f} ha (250 km²) for automated micro-parcel analysis. "
            "Please select a sub-catchment or focus corridor."
        )

    feature_collection = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": mapping(poly_geom),
                "properties": {
                    "area_ha": round(area_ha, 2),
                    "minx": round(minx, 6),
                    "miny": round(miny, 6),
                    "maxx": round(maxx, 6),
                    "maxy": round(maxy, 6),
                },
            }
        ],
    }

    return {
        "is_valid": True,
        "bounds": {
            "minx": round(minx, 6),
            "miny": round(miny, 6),
            "maxx": round(maxx, 6),
            "maxy": round(maxy, 6),
        },
        "boundary_geojson": feature_collection,
        "area_ha": round(area_ha, 2),
    }


# -------------------------------------------------------------------------
# STAC Search & Download Helpers
# -------------------------------------------------------------------------

def _search_stac_items(
    collections: List[str],
    bbox: List[float],
    query: Optional[Dict[str, Any]] = None,
    sortby: Optional[List[Dict[str, str]]] = None,
    limit: int = 5,
    timeout_sec: float = 20.0,
) -> List[Dict[str, Any]]:
    """Search Microsoft Planetary Computer STAC catalog for collection items."""
    payload: Dict[str, Any] = {
        "collections": collections,
        "bbox": bbox,
        "limit": limit,
    }
    if query:
        payload["query"] = query
    if sortby:
        payload["sortby"] = sortby

    with httpx.Client(timeout=timeout_sec) as client:
        res = client.post(f"{STAC_API}/search", json=payload)
        res.raise_for_status()
        data = res.json()
        return data.get("features", [])


def _download_cropped_raster_data_api(
    collection: str,
    item_id: str,
    asset_key: str,
    bbox: List[float],
    timeout_sec: float = 45.0,
    max_retries: int = 3,
) -> bytes:
    """Download a cropped GeoTIFF window using Planetary Computer Data API.

    Retries with exponential backoff on transient errors.
    """
    minx, miny, maxx, maxy = bbox
    url = f"{DATA_API}/item/bbox/{minx},{miny},{maxx},{maxy}.tif?collection={collection}&item={item_id}&assets={asset_key}"

    last_error = None
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=timeout_sec) as client:
                res = client.get(url)
                if res.status_code == 200 and len(res.content) > 500:
                    return res.content
                if res.status_code == 404:
                    raise RuntimeError(f"Asset '{asset_key}' for item '{item_id}' not found in Data API.")
                res.raise_for_status()
        except Exception as e:
            last_error = e
            time.sleep(1.0 * (attempt + 1))

    raise RuntimeError(f"Failed to acquire cropped raster from Data API after {max_retries} attempts: {last_error}")


# -------------------------------------------------------------------------
# Elevation Acquisition (DEM)
# -------------------------------------------------------------------------

def acquire_elevation_raster(
    bounds: Dict[str, float],
    dest_dir: Path,
    project_id: str,
    buffer_deg: float = 0.003,
) -> Tuple[Path, Dict[str, Any]]:
    """Automatically discover, download, and validate a DEM raster covering the AOI.

    Primary Source: Copernicus DEM GLO-30 (Global 30m, cop-dem-glo-30).
    Fallback Source: NASA SRTM NASADEM Global 1 Arc-Second (nasadem).

    Adds a small spatial buffer to ensure valid terrain gradient calculation
    at the exact boundary edges without kernel clipping artifacts.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    target_dem_path = dest_dir / f"{project_id}_dem.tif"

    minx = bounds["minx"] - buffer_deg
    miny = bounds["miny"] - buffer_deg
    maxx = bounds["maxx"] + buffer_deg
    maxy = bounds["maxy"] + buffer_deg
    buffered_bbox = [round(minx, 6), round(miny, 6), round(maxx, 6), round(maxy, 6)]

    # Check cache first
    cache_key = f"dem_{buffered_bbox[0]}_{buffered_bbox[1]}_{buffered_bbox[2]}_{buffered_bbox[3]}"
    cache_path = CACHE_DIR / f"{cache_key}.tif"
    if cache_path.exists() and cache_path.stat().st_size > 1000:
        try:
            arr, meta = inspect_geotiff(cache_path)
            if meta.validation_status == "VALID" and meta.valid_pixel_count > 0:
                shutil.copy2(cache_path, target_dem_path)
                sha = calculate_file_sha256(target_dem_path)
                valid_elevs = arr[arr > -500.0]
                min_elev = float(np.min(valid_elevs)) if valid_elevs.size else 0.0
                max_elev = float(np.max(valid_elevs)) if valid_elevs.size else 0.0
                mean_elev = float(np.mean(valid_elevs)) if valid_elevs.size else 0.0
                return target_dem_path, {
                    "dataset_name": "Cached Global 30m Digital Elevation Model",
                    "stac_collection": "cop-dem-glo-30",
                    "item_id": "CACHED_TILE",
                    "local_file": target_dem_path.name,
                    "sha256": sha,
                    "dimensions": [int(arr.shape[1]), int(arr.shape[0])],
                    "bounds": bounds,
                    "crs": "EPSG:4326 (WGS 84)",
                    "resolution_deg": meta.pixel_size_x,
                    "elevation_units": "meters",
                    "elevation_min_m": round(min_elev, 1),
                    "elevation_max_m": round(max_elev, 1),
                    "elevation_mean_m": round(mean_elev, 1),
                    "valid_pixels": int(meta.valid_pixel_count),
                    "is_cached": True,
                }
        except Exception:
            pass

    # 1. Search Copernicus GLO-30 DEM
    dem_feature = None
    collection_used = "cop-dem-glo-30"
    asset_key = "data"

    try:
        cop_features = _search_stac_items(
            collections=["cop-dem-glo-30"],
            bbox=buffered_bbox,
            limit=1,
        )
        if cop_features:
            dem_feature = cop_features[0]
            collection_used = "cop-dem-glo-30"
            asset_key = "data"
    except Exception as exc:
        logger.warning(f"Copernicus DEM STAC query failed: {exc}. Trying NASADEM fallback.")

    # 2. Fallback to NASADEM
    if not dem_feature:
        try:
            nasa_features = _search_stac_items(
                collections=["nasadem"],
                bbox=buffered_bbox,
                limit=1,
            )
            if nasa_features:
                dem_feature = nasa_features[0]
                collection_used = "nasadem"
                asset_key = "elevation"
        except Exception as exc:
            logger.error(f"NASADEM STAC fallback query failed: {exc}")

    if not dem_feature:
        raise RuntimeError(
            f"No elevation data tiles discovered in Copernicus DEM or NASADEM for coordinates "
            f"[{bounds['minx']:.4f}, {bounds['miny']:.4f}, {bounds['maxx']:.4f}, {bounds['maxy']:.4f}]. "
            "Please verify the selected location is on continental or island landmass."
        )

    item_id = dem_feature["id"]
    dataset_title = (
        "Copernicus GLO-30 Global Digital Elevation Model (30m)"
        if collection_used == "cop-dem-glo-30"
        else "NASA SRTM NASADEM Global 1 Arc-Second V001 (30m)"
    )

    # 3. Download cropped GeoTIFF window
    tif_bytes = _download_cropped_raster_data_api(
        collection=collection_used,
        item_id=item_id,
        asset_key=asset_key,
        bbox=buffered_bbox,
    )

    # 4. Parse & validate array
    import io
    with tifffile.TiffFile(io.BytesIO(tif_bytes)) as tif:
        raw_arr = tif.pages[0].asarray()

    # Extract primary band
    if raw_arr.ndim == 3:
        elev_arr = raw_arr[..., 0].astype(np.float32)
    elif raw_arr.ndim == 2:
        elev_arr = raw_arr.astype(np.float32)
    else:
        raise RuntimeError(f"Unexpected DEM array dimension: {raw_arr.ndim}")

    # Validate pixel coverage and physical sanity
    valid_mask = ~np.isnan(elev_arr) & (elev_arr > -500.0) & (elev_arr < 9000.0)
    valid_count = int(np.sum(valid_mask))
    if valid_count < 16:
        raise RuntimeError(
            f"Acquired DEM raster contains only {valid_count} valid land pixels. "
            "The area may be over open ocean or missing valid elevation values."
        )

    # Clean NoData values
    nodata_val = -9999.0
    elev_arr[~valid_mask] = nodata_val

    # Calculate pixel resolution in degrees
    rows, cols = elev_arr.shape
    pixel_x = (buffered_bbox[2] - buffered_bbox[0]) / cols
    pixel_y = (buffered_bbox[3] - buffered_bbox[1]) / rows

    # 5. Write validated GeoTIFF
    write_geotiff(
        output_path=target_dem_path,
        array=elev_arr,
        bounds={
            "minx": buffered_bbox[0],
            "miny": buffered_bbox[1],
            "maxx": buffered_bbox[2],
            "maxy": buffered_bbox[3],
        },
        pixel_size_x=pixel_x,
        pixel_size_y=pixel_y,
        nodata_value=nodata_val,
        crs_str="EPSG:4326 (WGS 84)",
    )

    # Cache for reuse
    try:
        shutil.copy2(target_dem_path, cache_path)
    except Exception:
        pass

    sha = calculate_file_sha256(target_dem_path)
    valid_elevs = elev_arr[valid_mask]
    min_elev = float(np.min(valid_elevs))
    max_elev = float(np.max(valid_elevs))
    mean_elev = float(np.mean(valid_elevs))

    provenance = {
        "dataset_name": dataset_title,
        "stac_collection": collection_used,
        "item_id": item_id,
        "local_file": target_dem_path.name,
        "file_size_bytes": target_dem_path.stat().st_size,
        "sha256": sha,
        "dimensions": [int(cols), int(rows)],
        "bounds": {
            "minx": buffered_bbox[0],
            "miny": buffered_bbox[1],
            "maxx": buffered_bbox[2],
            "maxy": buffered_bbox[3],
        },
        "crs": "EPSG:4326 (WGS 84)",
        "resolution_deg": pixel_x,
        "elevation_units": "meters",
        "elevation_min_m": round(min_elev, 1),
        "elevation_max_m": round(max_elev, 1),
        "elevation_mean_m": round(mean_elev, 1),
        "valid_pixels": valid_count,
    }

    return target_dem_path, provenance


# -------------------------------------------------------------------------
# Multispectral Imagery Acquisition (Sentinel-2 L2A & NDVI)
# -------------------------------------------------------------------------

def acquire_vegetation_imagery(
    bounds: Dict[str, float],
    dest_dir: Path,
    project_id: str,
    buffer_deg: float = 0.003,
) -> Tuple[Optional[Path], Dict[str, Any]]:
    """Search, retrieve, and calculate Sentinel-2 NDVI for the study area.

    Queries Sentinel-2 Level-2A surface reflectance (B04 Red, B08 NIR).
    Filters for lowest cloud cover scene.
    If no optical scene is available, gracefully returns (None, metadata)
    allowing the scientific engine to run in reduced-data mode without failure.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    target_ndvi_path = dest_dir / f"{project_id}_ndvi.tif"

    minx = bounds["minx"] - buffer_deg
    miny = bounds["miny"] - buffer_deg
    maxx = bounds["maxx"] + buffer_deg
    maxy = bounds["maxy"] + buffer_deg
    buffered_bbox = [round(minx, 6), round(miny, 6), round(maxx, 6), round(maxy, 6)]

    # 1. Query Sentinel-2 L2A catalog
    s2_feature = None
    cloud_thresholds = [15.0, 35.0, 60.0]

    for c_thresh in cloud_thresholds:
        try:
            feats = _search_stac_items(
                collections=["sentinel-2-l2a"],
                bbox=buffered_bbox,
                query={"eo:cloud_cover": {"lt": c_thresh}},
                sortby=[{"field": "properties.eo:cloud_cover", "direction": "asc"}],
                limit=3,
            )
            if feats:
                s2_feature = feats[0]
                break
        except Exception as exc:
            logger.warning(f"Sentinel-2 STAC query (cloud < {c_thresh}%) failed: {exc}")

    # Fallback to any recent scene if cloud filter returned empty
    if not s2_feature:
        try:
            feats = _search_stac_items(
                collections=["sentinel-2-l2a"],
                bbox=buffered_bbox,
                limit=3,
            )
            if feats:
                s2_feature = feats[0]
        except Exception:
            pass

    if not s2_feature:
        return None, {
            "status": "UNAVAILABLE",
            "reason": "No Sentinel-2 Level-2A observations discovered covering the study area.",
            "mode": "REDUCED_DATA_TERRAIN_ONLY",
        }

    scene_id = s2_feature["id"]
    props = s2_feature.get("properties", {})
    cloud_cover = float(props.get("eo:cloud_cover", 0.0))
    acq_date = props.get("datetime", "unknown")
    platform = props.get("platform", "Sentinel-2")

    try:
        # 2. Download B04 (Red) and B08 (NIR) crops
        b04_bytes = _download_cropped_raster_data_api(
            collection="sentinel-2-l2a",
            item_id=scene_id,
            asset_key="B04",
            bbox=buffered_bbox,
        )
        b08_bytes = _download_cropped_raster_data_api(
            collection="sentinel-2-l2a",
            item_id=scene_id,
            asset_key="B08",
            bbox=buffered_bbox,
        )

        with tifffile.TiffFile(io.BytesIO(b04_bytes)) as t4:
            arr4 = t4.pages[0].asarray()
            if arr4.ndim == 3:
                arr4 = arr4[..., 0]
        with tifffile.TiffFile(io.BytesIO(b08_bytes)) as t8:
            arr8 = t8.pages[0].asarray()
            if arr8.ndim == 3:
                arr8 = arr8[..., 0]

        # Ensure matching shapes
        if arr4.shape != arr8.shape:
            # Match dimensions
            min_r = min(arr4.shape[0], arr8.shape[0])
            min_c = min(arr4.shape[1], arr8.shape[1])
            arr4 = arr4[:min_r, :min_c]
            arr8 = arr8[:min_r, :min_c]

        # 3. Calculate NDVI: (NIR - Red) / (NIR + Red)
        ndvi_arr, stats = calculate_ndvi_array(
            red_array=arr4,
            nir_array=arr8,
            red_nodata=0.0,
            nir_nodata=0.0,
        )

        rows, cols = ndvi_arr.shape
        pixel_x = (buffered_bbox[2] - buffered_bbox[0]) / cols
        pixel_y = (buffered_bbox[3] - buffered_bbox[1]) / rows

        write_geotiff(
            output_path=target_ndvi_path,
            array=ndvi_arr,
            bounds={
                "minx": buffered_bbox[0],
                "miny": buffered_bbox[1],
                "maxx": buffered_bbox[2],
                "maxy": buffered_bbox[3],
            },
            pixel_size_x=pixel_x,
            pixel_size_y=pixel_y,
            nodata_value=-9999.0,
            crs_str="EPSG:4326 (WGS 84)",
        )

        sha = calculate_file_sha256(target_ndvi_path)

        provenance = {
            "status": "AVAILABLE",
            "dataset_name": "Copernicus Sentinel-2 Level-2A Surface Reflectance",
            "stac_collection": "sentinel-2-l2a",
            "scene_id": scene_id,
            "platform": platform,
            "acquisition_datetime": acq_date,
            "cloud_cover_percent": round(cloud_cover, 2),
            "local_file": target_ndvi_path.name,
            "sha256": sha,
            "dimensions": [int(cols), int(rows)],
            "bounds": {
                "minx": buffered_bbox[0],
                "miny": buffered_bbox[1],
                "maxx": buffered_bbox[2],
                "maxy": buffered_bbox[3],
            },
            "crs": "EPSG:4326 (WGS 84)",
            "mean_ndvi": stats.mean_ndvi,
            "min_ndvi": stats.min_ndvi,
            "max_ndvi": stats.max_ndvi,
            "valid_pixels": stats.valid_pixels,
        }

        return target_ndvi_path, provenance

    except Exception as exc:
        logger.warning(f"NDVI processing for scene {scene_id} failed: {exc}. Continuing in terrain-only mode.")
        return None, {
            "status": "UNAVAILABLE",
            "reason": f"Vegetation raster download or processing failed: {str(exc)}",
            "mode": "REDUCED_DATA_TERRAIN_ONLY",
        }


# -------------------------------------------------------------------------
# Comprehensive One-Click Pipeline Execution
# -------------------------------------------------------------------------

@dataclass
class PipelineProgress:
    stage_number: int
    stage_title: str
    stage_message: str
    is_completed: bool = False
    is_failed: bool = False


# Active background jobs status store
ACTIVE_JOBS: Dict[str, Dict[str, Any]] = {}


def run_auto_acquisition_pipeline(
    project_id: str,
    boundary_geojson: Optional[Dict[str, Any]] = None,
    bounds: Optional[Dict[str, float]] = None,
    cell_size_m: float = 250.0,
    priority_preset: str = "balanced",
    progress_callback: Optional[Callable[[int, str, str], None]] = None,
) -> Dict[str, Any]:
    """Execute end-to-end automated data acquisition, terrain processing,

    geotechnical modeling, and candidate parcel prioritization for a user-selected AOI.
    """
    def report_step(step: int, title: str, msg: str):
        if progress_callback:
            progress_callback(step, title, msg)
        logger.info(f"[Step {step}/9] {title}: {msg}")

    # Step 1: Validate Selected Area
    report_step(1, "Validating selected area", "Verifying geographic coordinates, topology, and study area size...")
    aoi_report = validate_aoi(boundary_geojson=boundary_geojson, bounds=bounds)
    effective_bounds = aoi_report["bounds"]
    effective_geojson = aoi_report["boundary_geojson"]
    area_ha = aoi_report["area_ha"]

    # Step 2: Workspace Setup
    report_step(2, "Searching for available datasets", f"Setting up project workspace and querying Planetary Computer STAC for {area_ha} ha...")
    project = ProjectService.get_project(project_id)
    if not project:
        raise ValueError(f"Project '{project_id}' not found.")

    proj_dir = PROJECTS_DIR / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    project.bounds = effective_bounds
    project.boundary_geojson = effective_geojson
    project.study_area_type = "polygon_draw" if boundary_geojson else "bbox"

    # Step 3: Acquire Elevation Data (DEM)
    report_step(3, "Acquiring elevation data", "Fetching high-resolution 30m Copernicus / NASA DEM...")
    dem_path, dem_meta = acquire_elevation_raster(
        bounds=effective_bounds,
        dest_dir=proj_dir,
        project_id=project_id,
    )
    project.layers["dem"] = {
        "path": str(dem_path),
        "status": "REAL_OBSERVED",
        "description": f"{dem_meta['dataset_name']} ({dem_meta.get('item_id', 'STAC')})",
        "provenance": dem_meta,
    }

    # Step 4: Acquire Vegetation Imagery (Sentinel-2 NDVI)
    report_step(4, "Acquiring vegetation imagery", "Searching cloud-free Sentinel-2 L2A observations...")
    ndvi_path, ndvi_meta = acquire_vegetation_imagery(
        bounds=effective_bounds,
        dest_dir=proj_dir,
        project_id=project_id,
    )
    if ndvi_path and ndvi_path.exists():
        project.layers["ndvi"] = {
            "path": str(ndvi_path),
            "status": "DERIVED_GEOSPATIAL",
            "description": f"Sentinel-2 L2A BOA NDVI ({ndvi_meta.get('scene_id', 'STAC')})",
            "provenance": ndvi_meta,
        }
    else:
        project.layers["ndvi"] = {
            "path": "",
            "status": "UNAVAILABLE",
            "description": "Optical vegetation observations unavailable for study area.",
            "provenance": ndvi_meta,
        }

    # Step 5: Process Terrain (Slope & Aspect)
    report_step(5, "Processing terrain", "Calculating Horn's 8-neighbourhood slope and compass aspect...")
    terrain_res = process_dem_terrain(dem_path)

    slope_file = settings.ARTIFACTS_DIR / terrain_res.slope_raster_id
    aspect_file = settings.ARTIFACTS_DIR / terrain_res.aspect_raster_id
    final_slope_path = proj_dir / f"{project_id}_slope.tif"
    final_aspect_path = proj_dir / f"{project_id}_aspect.tif"
    shutil.copy2(slope_file, final_slope_path)
    shutil.copy2(aspect_file, final_aspect_path)

    project.layers["slope"] = {
        "path": str(final_slope_path),
        "status": "DERIVED_GEOSPATIAL",
        "description": f"Derived slope raster from {dem_path.name}",
    }
    project.layers["aspect"] = {
        "path": str(final_aspect_path),
        "status": "DERIVED_GEOSPATIAL",
        "description": f"Derived aspect raster from {dem_path.name}",
    }

    # Step 6: Prepare Geotechnical Stability Model
    report_step(6, "Preparing geotechnical analysis", "Evaluating infinite slope baseline and reinforced Factor of Safety...")
    gp = project.geotechnical_parameters or {}
    soil_dict = gp.get("soil", {})
    root_dict = gp.get("root", {})
    target_fs = float(gp.get("target_fs", 1.3))

    depth_val = float(soil_dict.get("depth_m", soil_dict.get("z_m", 1.8)))
    gamma_val = float(soil_dict.get("gamma_kn_m3", 18.5))
    m_ratio = float(soil_dict.get("m_water_table", 0.5))
    # Pore pressure u = m * gamma_w * z
    u_val = float(soil_dict.get("u_kpa", m_ratio * 9.81 * depth_val))

    soil = SoilParameters(
        c_prime_kpa=float(soil_dict.get("c_prime_kpa", 8.0)),
        phi_prime_deg=float(soil_dict.get("phi_deg", soil_dict.get("phi_prime_deg", 26.0))),
        gamma_kn_m3=gamma_val,
        z_m=depth_val,
        u_kpa=u_val,
    )
    root = RootParameters(
        tensile_stress_input=float(root_dict.get("tensile_stress_kpa", root_dict.get("tensile_stress_input", 25000.0))),
        root_area_ratio=float(root_dict.get("rar", root_dict.get("root_area_ratio", 0.002))),
        k_factor=float(root_dict.get("k_factor", 1.2)),
    )

    geo_res = process_geotechnical_raster(
        slope_path=final_slope_path,
        soil=soil,
        root=root,
        fs_target=target_fs,
    )

    art_rasters = geo_res.get("artifacts", {}).get("rasters", {})
    for k in ["fs_baseline", "fs_reinforced", "fs_delta", "required_cohesion"]:
        fname = art_rasters.get(k)
        if fname:
            src_art = settings.ARTIFACTS_DIR / fname
            dest_proj_art = proj_dir / f"{project_id}_{k}.tif"
            if src_art.exists():
                shutil.copy2(src_art, dest_proj_art)
                project.layers[k] = {
                    "path": str(dest_proj_art),
                    "status": "ILLUSTRATIVE_SCENARIO" if gp.get("is_demo_parameters", False) else "DERIVED_GEOTECHNICAL",
                    "description": f"Modeled geotechnical {k} raster",
                }

    ProjectService.update_project(project)

    # Step 7 & 8: Candidate Parcel Discretization & Priority Ranking
    report_step(7, "Evaluating candidate parcels", f"Tessellating study area into {cell_size_m}m parcels and extracting zonal metrics...")

    # Configure scoring weights from priority preset
    if priority_preset == "landslide":
        w_need, w_gain, w_area, w_conf = 0.50, 0.35, 0.10, 0.05
    elif priority_preset == "plantable":
        w_need, w_gain, w_area, w_conf = 0.20, 0.20, 0.50, 0.10
    else:  # balanced
        w_need, w_gain, w_area, w_conf = 0.35, 0.30, 0.20, 0.15

    from backend.app.api.recommendation_routes import (
        RecommendationRunRequest,
        run_spatial_recommendations,
    )
    from backend.app.schemas.recommendations import (
        EligibilitySettingsSchema,
        ScoringWeightsSchema,
    )

    rec_req = RecommendationRunRequest(
        project_id=project_id,
        cell_size_m=cell_size_m,
        study_area_bounds=effective_bounds,
        study_area_geojson=effective_geojson,
        eligibility_settings=EligibilitySettingsSchema(
            min_terrain_coverage_pct=75.0,
            max_slope_deg=45.0,
            enable_ndvi_canopy_filter=bool(ndvi_path and ndvi_path.exists()),
            ndvi_canopy_threshold=0.65,
            min_plantable_area_ha=0.15,
        ),
        scoring_weights=ScoringWeightsSchema(
            weight_geotechnical_need=w_need,
            weight_stability_gain=w_gain,
            weight_plantable_area=w_area,
            weight_data_confidence=w_conf,
        ),
    )

    report_step(8, "Generating recommendations", "Calculating composite priority scores and bio-engineering recommendations...")
    recommendation_run = run_spatial_recommendations(rec_req)

    # Step 9: Preparing Final Results
    report_step(9, "Preparing final results", "Finalizing spatial overlays, provenance records, and GeoJSON exports...")

    return {
        "success": True,
        "project_id": project_id,
        "project_name": project.name,
        "area_ha": area_ha,
        "bounds": effective_bounds,
        "dem_provenance": dem_meta,
        "vegetation_provenance": ndvi_meta,
        "recommendation_run": recommendation_run.model_dump(),
    }
