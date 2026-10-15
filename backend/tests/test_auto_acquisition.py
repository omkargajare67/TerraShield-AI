"""Unit and Integration Tests for Automated Geospatial Acquisition & One-Click Analysis."""

import io
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import tifffile
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.core.geospatial.acquisition import (
    acquire_elevation_raster,
    acquire_vegetation_imagery,
    run_auto_acquisition_pipeline,
    validate_aoi,
)
from backend.app.core.projects.project_service import ProjectService
from backend.app.main import app

client = TestClient(app)


# -------------------------------------------------------------------------
# Test AOI Validation
# -------------------------------------------------------------------------

def test_validate_aoi_valid_bbox():
    """Valid bounding box produces proper FeatureCollection and calculated acreage."""
    bounds = {"minx": 76.01, "miny": 11.56, "maxx": 76.06, "maxy": 11.60}
    report = validate_aoi(bounds=bounds)
    assert report["is_valid"] is True
    assert report["bounds"] == bounds
    assert report["area_ha"] > 100.0  # Approx ~1500-2000 ha
    assert report["boundary_geojson"]["type"] == "FeatureCollection"
    assert len(report["boundary_geojson"]["features"]) == 1


def test_validate_aoi_valid_polygon():
    """Valid GeoJSON polygon returns correct bounds and geodesic area."""
    geojson = {
        "type": "Polygon",
        "coordinates": [
            [
                [76.02, 11.57],
                [76.04, 11.57],
                [76.04, 11.59],
                [76.02, 11.59],
                [76.02, 11.57],
            ]
        ],
    }
    report = validate_aoi(boundary_geojson=geojson)
    assert report["is_valid"] is True
    assert report["area_ha"] > 10.0
    assert report["bounds"]["minx"] == 76.02
    assert report["bounds"]["maxx"] == 76.04


def test_validate_aoi_rejects_empty():
    """Reject empty geometry."""
    with pytest.raises(ValueError, match="Either boundary_geojson or bounds must be provided"):
        validate_aoi()


def test_validate_aoi_rejects_out_of_bounds_coords():
    """Reject coordinates outside WGS 84 limits."""
    bounds = {"minx": 190.0, "miny": 10.0, "maxx": 195.0, "maxy": 12.0}
    with pytest.raises(ValueError, match="Longitude coordinates.*outside valid WGS 84 range"):
        validate_aoi(bounds=bounds)

    bounds_lat = {"minx": 70.0, "miny": -95.0, "maxx": 72.0, "maxy": -92.0}
    with pytest.raises(ValueError, match="Latitude coordinates.*outside valid WGS 84 range"):
        validate_aoi(bounds=bounds_lat)


def test_validate_aoi_rejects_too_small_area():
    """Reject microscopic areas (< 1 ha)."""
    # Extremely tiny bounding box (approx 5 meters)
    tiny_bounds = {"minx": 76.00000, "miny": 11.50000, "maxx": 76.00005, "maxy": 11.50005}
    with pytest.raises(ValueError, match="below the minimum limit of 1.0 ha"):
        validate_aoi(bounds=tiny_bounds)


def test_validate_aoi_rejects_excessive_area():
    """Reject enormous areas exceeding 25,000 ha."""
    huge_bounds = {"minx": 75.0, "miny": 10.0, "maxx": 77.0, "maxy": 12.0}
    with pytest.raises(ValueError, match="exceeds the maximum supported limit"):
        validate_aoi(bounds=huge_bounds)


# -------------------------------------------------------------------------
# Test Acquisition Logic with Mocked Network
# -------------------------------------------------------------------------

def _create_mock_tif_bytes(shape=(64, 64), dtype=np.float32, base_val=500.0) -> bytes:
    """Helper to generate valid in-memory GeoTIFF bytes."""
    buf = io.BytesIO()
    arr = (np.ones(shape, dtype=dtype) * base_val).astype(dtype)
    tifffile.imwrite(buf, arr)
    return buf.getvalue()


@patch("backend.app.core.geospatial.acquisition._search_stac_items")
@patch("backend.app.core.geospatial.acquisition._download_cropped_raster_data_api")
def test_acquire_elevation_raster_success(mock_data_api, mock_stac, tmp_path):
    """Verify DEM acquisition, fallback to valid GeoTIFF and correct metadata."""
    mock_stac.return_value = [
        {"id": "Copernicus_DSM_COG_10_N11_00_E076_00_DEM", "assets": {"data": {"href": "http://mock"}}}
    ]
    mock_data_api.return_value = _create_mock_tif_bytes(shape=(32, 32), base_val=450.0)

    bounds = {"minx": 76.02, "miny": 11.56, "maxx": 76.05, "maxy": 11.59}
    dem_path, meta = acquire_elevation_raster(
        bounds=bounds,
        dest_dir=tmp_path,
        project_id="test_proj_1",
    )

    assert dem_path.exists()
    assert dem_path.name == "test_proj_1_dem.tif"
    assert meta["elevation_mean_m"] == 450.0
    assert meta["stac_collection"] == "cop-dem-glo-30"


@patch("backend.app.core.geospatial.acquisition._search_stac_items")
@patch("backend.app.core.geospatial.acquisition._download_cropped_raster_data_api")
def test_acquire_vegetation_imagery_success(mock_data_api, mock_stac, tmp_path):
    """Verify Sentinel-2 B04 & B08 retrieval and accurate NDVI computation."""
    mock_stac.return_value = [
        {
            "id": "S2A_MSIL2A_TEST_SCENE",
            "properties": {"eo:cloud_cover": 2.5, "datetime": "2024-03-01T10:00:00Z"},
            "assets": {"B04": {}, "B08": {}},
        }
    ]
    # Red = 1000, NIR = 3000 -> NDVI = (3000-1000)/(3000+1000) = 0.50
    def _side_effect(collection, item_id, asset_key, bbox, **kwargs):
        if asset_key == "B04":
            return _create_mock_tif_bytes(shape=(32, 32), base_val=1000.0)
        return _create_mock_tif_bytes(shape=(32, 32), base_val=3000.0)

    mock_data_api.side_effect = _side_effect

    bounds = {"minx": 76.02, "miny": 11.56, "maxx": 76.05, "maxy": 11.59}
    ndvi_path, meta = acquire_vegetation_imagery(
        bounds=bounds,
        dest_dir=tmp_path,
        project_id="test_proj_ndvi",
    )

    assert ndvi_path is not None
    assert ndvi_path.exists()
    assert meta["status"] == "AVAILABLE"
    assert abs(meta["mean_ndvi"] - 0.50) < 0.01


@patch("backend.app.core.geospatial.acquisition._search_stac_items")
def test_acquire_vegetation_imagery_graceful_missing(mock_stac, tmp_path):
    """Verify graceful reduced-data mode when no optical scenes exist."""
    mock_stac.return_value = []

    bounds = {"minx": 76.02, "miny": 11.56, "maxx": 76.05, "maxy": 11.59}
    ndvi_path, meta = acquire_vegetation_imagery(
        bounds=bounds,
        dest_dir=tmp_path,
        project_id="test_proj_no_s2",
    )

    assert ndvi_path is None
    assert meta["status"] == "UNAVAILABLE"
    assert meta["mode"] == "REDUCED_DATA_TERRAIN_ONLY"


# -------------------------------------------------------------------------
# Test API Routes
# -------------------------------------------------------------------------

def test_api_validate_aoi_endpoint():
    """Test POST /api/v1/projects/validate-aoi."""
    res = client.post(
        "/api/v1/projects/validate-aoi",
        json={"bounds": {"minx": 76.02, "miny": 11.56, "maxx": 76.05, "maxy": 11.59}},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert data["area_ha"] > 10.0


def test_api_validate_aoi_rejection():
    """Test POST /api/v1/projects/validate-aoi rejects invalid inputs with 400."""
    res = client.post(
        "/api/v1/projects/validate-aoi",
        json={"bounds": {"minx": 100.0, "miny": 11.0, "maxx": 50.0, "maxy": 12.0}},
    )
    assert res.status_code == 400
    assert "strictly less than max" in res.json()["detail"]


def test_api_route_precedence_and_no_405_error():
    """Verify static routes are NOT masked by /{project_id} and never return 405."""
    # 1. GET /api/v1/projects/auto-analyze returns info, not 404 project not found
    get_res = client.get("/api/v1/projects/auto-analyze")
    assert get_res.status_code == 200
    assert "POST" in get_res.json().get("methods_supported", [])

    # 2. Trailing slash on validate-aoi
    val_res = client.post(
        "/api/v1/projects/validate-aoi/",
        json={"bounds": {"minx": 76.02, "miny": 11.56, "maxx": 76.05, "maxy": 11.59}},
    )
    assert val_res.status_code == 200
    assert val_res.json()["is_valid"] is True

    # 3. GET /api/v1/projects/auto-analyze/status/nonexistent returns 404 for job, not 405
    status_res = client.get("/api/v1/projects/auto-analyze/status/nonexistent_job_123")
    assert status_res.status_code == 404
    assert "not found" in status_res.json()["detail"].lower()


@patch("backend.app.core.geospatial.acquisition._search_stac_items")
@patch("backend.app.core.geospatial.acquisition._download_cropped_raster_data_api")
def test_api_auto_analyze_sync(mock_data_api, mock_stac):
    """Test synchronous execution of POST /api/v1/projects/auto-analyze."""
    def _mock_stac_fn(collections, **kwargs):
        if "cop-dem-glo-30" in collections:
            return [{"id": "Cop_DEM_TEST", "assets": {"data": {"href": "mock"}}}]
        return []
    mock_stac.side_effect = _mock_stac_fn
    mock_data_api.return_value = _create_mock_tif_bytes(shape=(40, 40), base_val=600.0)

    bounds = {"minx": 76.02, "miny": 11.56, "maxx": 76.05, "maxy": 11.59}
    res = client.post(
        "/api/v1/projects/auto-analyze",
        json={
            "name": "Sync Auto Test Area",
            "bounds": bounds,
            "cell_size_m": 300.0,
            "priority_preset": "balanced",
            "async_job": False,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["area_ha"] > 10.0
    assert "recommendation_run" in data
    rec_run = data["recommendation_run"]
    assert rec_run["total_parcels"] > 0
    # Clean up created test project
    ProjectService.delete_project(data["project_id"])


def test_api_auto_analyze_async_and_status():
    """Test asynchronous trigger and progress status polling."""
    bounds = {"minx": 76.02, "miny": 11.56, "maxx": 76.05, "maxy": 11.59}
    res = client.post(
        "/api/v1/projects/auto-analyze",
        json={
            "name": "Async Test Area",
            "bounds": bounds,
            "async_job": True,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "STARTED"
    job_id = data["job_id"]

    # Check status endpoint
    poll_res = client.get(f"/api/v1/projects/auto-analyze/status/{job_id}")
    assert poll_res.status_code == 200
    poll_data = poll_res.json()
    assert poll_data["job_id"] == job_id
    assert poll_data["status"] in ["RUNNING", "COMPLETED", "FAILED"]
    assert 1 <= poll_data["stage_number"] <= 9

    # Clean up project
    ProjectService.delete_project(data["project_id"])


def test_workspace_isolation(tmp_path):
    """Verify that auto-acquired layers are strictly isolated in the project's own workspace."""
    proj = ProjectService.create_project(
        name="Isolation Workspace Test",
        bounds={"minx": 76.02, "miny": 11.56, "maxx": 76.05, "maxy": 11.59},
    )
    p_dir = Path("data/projects") / proj.id
    assert p_dir.exists()

    # Wayanad pilot files must exist and remain untouched
    wayanad_meta = Path("data/projects/wayanad_pilot/project.json")
    assert wayanad_meta.exists()
    wayanad_mtime_before = wayanad_meta.stat().st_mtime

    with patch("backend.app.core.geospatial.acquisition._search_stac_items") as mock_stac, \
         patch("backend.app.core.geospatial.acquisition._download_cropped_raster_data_api") as mock_data_api:
        mock_stac.return_value = [{"id": "DEM_ISO", "assets": {"data": {"href": "mock"}}}]
        mock_data_api.return_value = _create_mock_tif_bytes(shape=(32, 32), base_val=750.0)

        dem_path, _ = acquire_elevation_raster(
            bounds={"minx": 76.02, "miny": 11.56, "maxx": 76.05, "maxy": 11.59},
            dest_dir=p_dir,
            project_id=proj.id,
        )

        assert dem_path.parent == p_dir
        assert dem_path.name == f"{proj.id}_dem.tif"

    # Wayanad pilot project metadata is unchanged
    assert wayanad_meta.stat().st_mtime == wayanad_mtime_before

    # Clean up
    ProjectService.delete_project(proj.id)


def test_dem_insufficient_valid_pixels_rejected(tmp_path):
    """Reject raster containing all ocean / NoData pixels (< 16 valid pixels)."""
    with patch("backend.app.core.geospatial.acquisition._search_stac_items") as mock_stac, \
         patch("backend.app.core.geospatial.acquisition._download_cropped_raster_data_api") as mock_data_api:
        mock_stac.return_value = [{"id": "DEM_OCEAN", "assets": {"data": {"href": "mock"}}}]
        # All NoData / -9999
        mock_data_api.return_value = _create_mock_tif_bytes(shape=(32, 32), base_val=-9999.0)

        with pytest.raises(RuntimeError, match="contains only 0 valid land pixels"):
            acquire_elevation_raster(
                bounds={"minx": 70.0, "miny": 10.0, "maxx": 70.1, "maxy": 10.1},
                dest_dir=tmp_path,
                project_id="test_ocean",
            )


def test_wayanad_pilot_compatibility():
    """Verify built-in Wayanad benchmark project continues to function identically."""
    wayanad = ProjectService.get_project("wayanad_pilot")
    assert wayanad is not None
    assert wayanad.is_builtin is True
    assert "dem" in wayanad.layers
    assert "slope" in wayanad.layers
    assert Path(wayanad.layers["dem"]["path"]).exists()
    assert Path(wayanad.layers["slope"]["path"]).exists()


def test_live_planetary_computer_smoke():
    """Optional live network smoke test verifying actual Planetary Computer STAC availability."""
    import httpx
    try:
        with httpx.Client(timeout=8) as client:
            res = client.get("https://planetarycomputer.microsoft.com/api/stac/v1")
            assert res.status_code == 200
    except Exception as exc:
        pytest.skip(f"Live network unavailable for Planetary Computer: {exc}")

