"""Comprehensive automated tests for Phase 2 Geospatial Data Engine."""

from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.core.geospatial.artifacts import get_safe_artifact_path
from backend.app.core.geospatial.ndvi import calculate_ndvi_array
from backend.app.core.geospatial.raster_loader import (
    inspect_geotiff,
    write_geotiff,
)
from backend.app.core.geospatial.soil_data import validate_soil_metadata
from backend.app.core.geospatial.terrain import (
    calculate_slope_and_aspect,
    compute_elevation_stats,
    process_dem_terrain,
)
from backend.app.core.geospatial.vector_loader import (
    intersect_parcels_with_protected_areas,
    load_and_validate_vector_file,
)
from backend.app.main import app
from backend.app.schemas.geospatial import SoilDataValidationRequest

client = TestClient(app)


@pytest.fixture
def synthetic_flat_dem(tmp_path: Path) -> Path:
    """Fixture: 10x10 flat DEM (elevation=100m, 10m pixels)."""
    arr = np.full((10, 10), 100.0, dtype=np.float32)
    path = tmp_path / "flat_dem.tif"
    write_geotiff(
        output_path=path,
        array=arr,
        bounds={"minx": 500000.0, "miny": 5000000.0, "maxx": 500100.0, "maxy": 5000100.0},
        pixel_size_x=10.0,
        pixel_size_y=10.0,
        nodata_value=-9999.0,
        crs_str="EPSG:32610 (WGS 84 / UTM zone 10N)",
    )
    return path


@pytest.fixture
def synthetic_sloped_dem(tmp_path: Path) -> Path:
    """Fixture: 10x10 45-degree slope DEM dipping East (z increases by 10m per 10m column).
    dx = 10m, dz = 10m => slope = arctan(1) = 45.0 degrees.
    Aspect dipping East: dz_dx = +1 (rises East, descends West => aspect=270° or dipping East => aspect=90°).
    """
    # z(row, col) = col * 10.0
    arr = np.zeros((10, 10), dtype=np.float32)
    for col in range(10):
        arr[:, col] = col * 10.0

    path = tmp_path / "sloped_dem.tif"
    write_geotiff(
        output_path=path,
        array=arr,
        bounds={"minx": 500000.0, "miny": 5000000.0, "maxx": 500100.0, "maxy": 5000100.0},
        pixel_size_x=10.0,
        pixel_size_y=10.0,
        nodata_value=-9999.0,
        crs_str="EPSG:32610 (WGS 84 / UTM zone 10N)",
    )
    return path


@pytest.fixture
def synthetic_south_sloped_dem(tmp_path: Path) -> Path:
    """Fixture: 10x10 DEM with elevation decreasing to the South (descending South => Aspect=180°)."""
    arr = np.zeros((10, 10), dtype=np.float32)
    for row in range(10):
        arr[row, :] = 1000.0 - (row * 10.0)  # Row 0 (North) is 1000, Row 9 (South) is 910

    path = tmp_path / "south_slope_dem.tif"
    write_geotiff(
        output_path=path,
        array=arr,
        bounds={"minx": 500000.0, "miny": 5000000.0, "maxx": 500100.0, "maxy": 5000100.0},
        pixel_size_x=10.0,
        pixel_size_y=10.0,
        nodata_value=-9999.0,
        crs_str="EPSG:32610 (WGS 84 / UTM zone 10N)",
    )
    return path


class TestRasterInspectionAndValidation:
    """Tests for GeoTIFF metadata inspection and validation."""

    def test_inspect_valid_geotiff(self, synthetic_flat_dem: Path):
        arr, meta = inspect_geotiff(synthetic_flat_dem)
        assert arr.shape == (10, 10)
        assert meta.width == 10
        assert meta.height == 10
        assert meta.bands == 1
        assert meta.pixel_size_x == 10.0
        assert meta.pixel_size_y == 10.0
        assert meta.validation_status == "VALID"
        assert meta.valid_pixel_count == 100
        assert meta.nodata_pixel_count == 0

    def test_inspect_corrupted_file_raises_error(self, tmp_path: Path):
        bad_file = tmp_path / "corrupted.tif"
        bad_file.write_text("not a real geotiff file header")
        with pytest.raises(ValueError):
            inspect_geotiff(bad_file)

    def test_nonexistent_file_raises_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            inspect_geotiff(tmp_path / "nonexistent.tif")


class TestTerrainCalculations:
    """Tests for elevation statistics, slope in degrees, and aspect."""

    def test_elevation_statistics(self, synthetic_flat_dem: Path):
        arr, meta = inspect_geotiff(synthetic_flat_dem)
        stats, mask = compute_elevation_stats(arr, meta.nodata_value)
        assert stats.min_elevation == 100.0
        assert stats.max_elevation == 100.0
        assert stats.mean_elevation == 100.0
        assert stats.median_elevation == 100.0
        assert stats.valid_pixels == 100
        assert stats.nodata_pixels == 0

    def test_flat_terrain_slope_and_aspect(self, synthetic_flat_dem: Path):
        arr, meta = inspect_geotiff(synthetic_flat_dem)
        _, mask = compute_elevation_stats(arr, meta.nodata_value)
        slope, aspect, slope_stats, aspect_stats = calculate_slope_and_aspect(arr, meta, mask)

        # For a flat terrain, slope should be 0.0 everywhere
        assert slope_stats.min_slope_deg == 0.0
        assert slope_stats.max_slope_deg == 0.0
        assert slope_stats.mean_slope_deg == 0.0
        # All valid pixels should be classified as flat (aspect=-1.0)
        assert aspect_stats.flat_pixel_count == 100

    def test_controlled_45_degree_slope(self, synthetic_sloped_dem: Path):
        arr, meta = inspect_geotiff(synthetic_sloped_dem)
        _, mask = compute_elevation_stats(arr, meta.nodata_value)
        slope, aspect, slope_stats, _ = calculate_slope_and_aspect(arr, meta, mask)

        # Interior pixels (1 to 8) have dx=10m, dz/dx=1.0 => arctan(1.0) = 45.0 degrees
        interior_slopes = slope[2:8, 2:8]
        assert np.allclose(interior_slopes, 45.0, atol=0.5)

    def test_controlled_south_aspect(self, synthetic_south_sloped_dem: Path):
        arr, meta = inspect_geotiff(synthetic_south_sloped_dem)
        _, mask = compute_elevation_stats(arr, meta.nodata_value)
        slope, aspect, _, aspect_stats = calculate_slope_and_aspect(arr, meta, mask)

        # Dipping south: aspect must be 180°
        interior_aspects = aspect[2:8, 2:8]
        assert np.allclose(interior_aspects, 180.0, atol=1.0)

    def test_nodata_pixels_are_masked(self, tmp_path: Path):
        arr = np.full((6, 6), 50.0, dtype=np.float32)
        arr[0, 0] = -9999.0  # Nodata cell
        path = tmp_path / "nodata_dem.tif"
        write_geotiff(
            output_path=path,
            array=arr,
            bounds={"minx": 0.0, "miny": 0.0, "maxx": 60.0, "maxy": 60.0},
            pixel_size_x=10.0,
            pixel_size_y=10.0,
            nodata_value=-9999.0,
        )
        data, meta = inspect_geotiff(path)
        stats, mask = compute_elevation_stats(data, meta.nodata_value)
        assert stats.valid_pixels == 35
        assert stats.nodata_pixels == 1


class TestNDVICalculation:
    """Tests for Sentinel-2 NDVI calculation."""

    def test_standard_ndvi_calculation(self):
        red = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
        nir = np.array([[0.5, 0.6], [0.7, 0.8]], dtype=np.float32)

        # Expected:
        # (0,0): (0.5 - 0.1) / (0.5 + 0.1) = 0.4 / 0.6 = 0.6667
        # (0,1): (0.6 - 0.2) / (0.6 + 0.2) = 0.4 / 0.8 = 0.5000
        # (1,0): (0.7 - 0.3) / (0.7 + 0.3) = 0.4 / 1.0 = 0.4000
        # (1,1): (0.8 - 0.4) / (0.8 + 0.4) = 0.4 / 1.2 = 0.3333
        ndvi, stats = calculate_ndvi_array(red, nir)
        assert np.isclose(ndvi[0, 0], 0.6667, atol=0.001)
        assert np.isclose(ndvi[0, 1], 0.5000, atol=0.001)
        assert stats.valid_pixels == 4
        assert stats.zero_denominator_pixels == 0

    def test_zero_denominator_handling(self):
        # When both Red and NIR are 0, (NIR+Red)==0
        red = np.array([[0.0, 0.2]], dtype=np.float32)
        nir = np.array([[0.0, 0.6]], dtype=np.float32)

        ndvi, stats = calculate_ndvi_array(red, nir)
        # First cell should be masked with nodata, not crash with ZeroDivisionError
        assert ndvi[0, 0] == -9999.0
        assert stats.zero_denominator_pixels == 1
        assert stats.valid_pixels == 1

    def test_incompatible_band_dimensions_raises_error(self):
        red = np.ones((5, 5), dtype=np.float32)
        nir = np.ones((6, 6), dtype=np.float32)
        with pytest.raises(ValueError):
            calculate_ndvi_array(red, nir)


class TestSoilDataValidation:
    """Tests for soil metadata validation."""

    def test_valid_soil_metadata(self):
        req = SoilDataValidationRequest(
            source="ISRIC SoilGrids 250m",
            property_name="clay",
            depth_interval="0-30cm",
            units="g/kg",
        )
        resp = validate_soil_metadata(req)
        assert resp.is_valid is True
        assert resp.status == "validated"

    def test_unrecognized_soil_property(self):
        req = SoilDataValidationRequest(
            source="Custom Survey",
            property_name="unrecognized_magic_compound",
        )
        resp = validate_soil_metadata(req)
        assert resp.is_valid is False
        assert resp.status == "invalid"
        assert any("Unrecognized soil property" in m for m in resp.messages)


class TestVectorAndProtectedAreaIntersections:
    """Tests for vector validation and spatial intersections."""

    def test_load_and_validate_demo_geojson(self):
        features, val = load_and_validate_vector_file(settings.SAMPLE_DATA_PATH)
        assert len(features) == 5
        assert val.is_valid is True
        assert val.feature_count == 5
        assert "Polygon" in val.geometry_types

    def test_protected_area_intersection(self):
        # Create a mock protected area overlapping PARCEL-003
        mock_pa_features = [
            {
                "type": "Feature",
                "properties": {
                    "name": "Cascade Ecological Reserve",
                    "designation": "Strict Nature Reserve",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-121.800, 47.455],
                            [-121.785, 47.455],
                            [-121.785, 47.470],
                            [-121.800, 47.470],
                            [-121.800, 47.455],
                        ]
                    ],
                },
            }
        ]
        from backend.app.core.demo_data import load_demo_geojson

        parcels = load_demo_geojson()
        resp = intersect_parcels_with_protected_areas(parcels, mock_pa_features)
        assert resp.status == "completed"
        assert resp.intersecting_parcels_count > 0

        # Find PARCEL-003
        p3 = next(p for p in resp.results if p.parcel_id == "PARCEL-003")
        assert p3.intersects_protected_area is True
        assert p3.exclusion_recommended is True
        assert "Cascade Ecological Reserve" in p3.protected_area_names


class TestGeospatialAPIEndpoints:
    """FastAPI integration tests for /api/v1/geospatial endpoints."""

    def test_geospatial_status_endpoint(self):
        response = client.get("/api/v1/geospatial/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "engine_backend" in data

    def test_inspect_dem_endpoint(self, synthetic_flat_dem: Path):
        with open(synthetic_flat_dem, "rb") as f:
            response = client.post(
                "/api/v1/geospatial/dem/inspect",
                files={"file": ("synthetic_dem.tif", f, "image/tiff")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["width"] == 10
        assert data["height"] == 10
        assert data["validation_status"] == "VALID"

    def test_terrain_analysis_endpoint(self, synthetic_flat_dem: Path):
        with open(synthetic_flat_dem, "rb") as f:
            response = client.post(
                "/api/v1/geospatial/dem/terrain",
                files={"file": ("synthetic_dem.tif", f, "image/tiff")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "elevation" in data
        assert "slope" in data
        assert "aspect" in data
        assert data["slope"]["mean_slope_deg"] == 0.0

    def test_safe_artifact_retrieval(self, tmp_path: Path):
        # Create an artifact inside ARTIFACTS_DIR
        test_artifact = settings.ARTIFACTS_DIR / "test_artifact_sample.png"
        test_artifact.write_bytes(b"dummy png content")

        resp = client.get("/api/v1/geospatial/artifacts/test_artifact_sample.png")
        assert resp.status_code == 200

        # Test path traversal prevention
        traversal_resp = client.get("/api/v1/geospatial/artifacts/../../main.py")
        assert traversal_resp.status_code in (404, 400)

        # Cleanup
        test_artifact.unlink(missing_ok=True)


class TestPhase1Integrity:
    """Verify Phase 1 endpoints still function with 100% integrity."""

    def test_phase1_health_check(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_phase1_parcels(self):
        resp = client.get("/api/v1/parcels")
        assert resp.status_code == 200
        assert len(resp.json()["features"]) == 5

    def test_phase1_analysis(self):
        resp = client.post("/api/v1/analysis", json={"scenario": "landslide_mitigation"})
        assert resp.status_code == 200
        assert resp.json()["highest_leverage_score"] == 0.0008
