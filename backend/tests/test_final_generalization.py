"""Automated tests for Model Generalization, Multi-Format Vector Ingestion, and Project Workspaces."""

import io
import json
import os
import tempfile
import zipfile
from pathlib import Path
import geopandas as gpd
import numpy as np
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Polygon

from backend.app.core.config import settings
from backend.app.core.geospatial.coordinate_systems import (
    detect_and_normalize_crs,
    project_utm_to_latlon,
    project_webmercator_to_latlon,
)
from backend.app.core.geospatial.raster_loader import (
    inspect_geotiff,
    validate_and_inspect_uploaded_raster,
    write_geotiff,
)
from backend.app.core.geospatial.vector_loader import parse_uploaded_study_area
from backend.app.core.projects.project_service import ProjectService
from backend.app.main import app

client = TestClient(app)


def test_coordinate_system_transformations():
    """Verify UTM and Web Mercator coordinate transformations to geographic WGS84."""
    # Test UTM Zone 43N (Kerala / Western Ghats): ~76.05E, 11.60N
    easting, northing = 614400.0, 1282600.0
    lon, lat = project_utm_to_latlon(easting, northing, 43, northern=True)
    assert 75.9 < lon < 76.2
    assert 11.5 < lat < 11.7

    # Test Web Mercator
    lon_m, lat_m = project_webmercator_to_latlon(0.0, 0.0)
    assert abs(lon_m) < 1e-5
    assert abs(lat_m) < 1e-5

    # Test CRS normalization
    name, is_4326 = detect_and_normalize_crs("EPSG:4326")
    assert is_4326 is True
    name, is_4326 = detect_and_normalize_crs("EPSG:32643")
    assert is_4326 is False


def test_parse_uploaded_study_area_geojson():
    """Test vector parsing and validation of GeoJSON study area."""
    poly = Polygon([(76.01, 11.56), (76.09, 11.56), (76.09, 11.64), (76.01, 11.64), (76.01, 11.56)])
    gdf = gpd.GeoDataFrame([{"name": "Custom Watershed"}], geometry=[poly], crs="EPSG:4326")

    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False, mode="w") as tmp:
        tmp.write(gdf.to_json())
        tmp_path = Path(tmp.name)

    try:
        report = parse_uploaded_study_area(tmp_path)
        assert report["format"] == "GeoJSON"
        assert report["feature_count"] == 1
        assert report["is_valid"] is True
        assert 76.0 <= report["bounds"]["minx"] <= 76.02
        assert 11.63 <= report["bounds"]["maxy"] <= 11.65
        assert report["area_approx_ha"] > 0
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def test_parse_uploaded_study_area_shapefile_zip():
    """Test reading zipped Shapefile and verifying CRS reprojection if projected."""
    # Create UTM Zone 43N polygon in Kerala
    poly = Polygon([(610000, 1280000), (615000, 1280000), (615000, 1285000), (610000, 1285000), (610000, 1280000)])
    gdf = gpd.GeoDataFrame([{"name": "UTM Basin"}], geometry=[poly], crs="EPSG:32643")

    with tempfile.TemporaryDirectory() as tmpdir:
        shp_path = Path(tmpdir) / "test_basin.shp"
        gdf.to_file(shp_path)

        zip_path = Path(tmpdir) / "basin.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
                fp = Path(tmpdir) / f"test_basin{ext}"
                if fp.exists():
                    zf.write(fp, arcname=f"test_basin{ext}")

        report = parse_uploaded_study_area(zip_path)
        assert "Shapefile" in report["format"]
        assert report["reprojected"] is True
        assert report["feature_count"] == 1
        # Reprojected bounds must be in decimal degrees in Kerala
        assert 75.0 < report["bounds"]["minx"] < 77.0
        assert 11.0 < report["bounds"]["miny"] < 12.0


def test_project_workspace_lifecycle():
    """Verify project workspace creation, listing, updating, and deletion."""
    # 1. List builtin projects
    resp = client.get("/api/v1/projects")
    assert resp.status_code == 200
    projects = resp.json()
    assert len(projects) >= 2
    proj_ids = [p["id"] for p in projects]
    assert "wayanad_pilot" in proj_ids
    assert "cascade_demo" in proj_ids

    # 2. Create custom project
    create_payload = {
        "name": "Idukki Highland Reserve",
        "description": "High-altitude tea estate stabilization corridor",
        "study_area_type": "bbox",
        "bounds": {"minx": 76.90, "miny": 9.80, "maxx": 77.10, "maxy": 10.00},
        "geotech_preset_id": "colluvial_clay_silt",
    }
    create_resp = client.post("/api/v1/projects", json=create_payload)
    assert create_resp.status_code == 200
    created = create_resp.json()
    p_id = created["id"]
    assert "idukki" in p_id
    assert created["bounds"]["minx"] == 76.90

    # 3. Retrieve project
    get_resp = client.get(f"/api/v1/projects/{p_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Idukki Highland Reserve"

    # 4. Update project parameters
    update_resp = client.put(
        f"/api/v1/projects/{p_id}",
        json={
            "description": "Updated high-altitude corridor",
            "geotechnical_parameters": {"soil": {"depth_m": 2.5}},
        },
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["geotechnical_parameters"]["soil"]["depth_m"] == 2.5

    # 5. Delete project
    del_resp = client.delete(f"/api/v1/projects/{p_id}")
    assert del_resp.status_code == 200

    # Ensure deleted
    get_del = client.get(f"/api/v1/projects/{p_id}")
    assert get_del.status_code == 404


def test_recommendation_run_with_custom_bounds():
    """Verify recommendation pipeline executes successfully with generalized study area parameters."""
    req_body = {
        "cell_size_m": 300.0,
        "study_area_bounds": {
            "minx": 76.02,
            "miny": 11.57,
            "maxx": 76.08,
            "maxy": 11.63,
        },
        "fs_target": 1.3,
    }
    resp = client.post("/api/v1/recommendations/run", json=req_body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_parcels"] > 0
    assert "top_recommendations" in data
    assert "artifacts" in data
    assert "parcels_geojson" in data["artifacts"]



def test_raster_validation_logic():
    """Verify raster validation detects valid DEMs and reports errors on invalid inputs."""
    sample_dem = settings.BASE_DIR / "data" / "sample" / "sample_dem.tif"
    if sample_dem.exists():
        val = validate_and_inspect_uploaded_raster(sample_dem, expected_layer_type="dem")
        assert val["is_valid"] is True
        assert val["width"] > 0
        assert val["height"] > 0
        assert val["min_value"] is not None
