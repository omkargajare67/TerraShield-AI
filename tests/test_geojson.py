"""Validation tests for the demonstration GeoJSON dataset."""

import json
from pathlib import Path

SAMPLE_GEOJSON_PATH = Path(__file__).resolve().parent.parent / "data" / "sample" / "demo_parcels.geojson"


def test_geojson_file_exists():
    assert SAMPLE_GEOJSON_PATH.exists(), f"Missing sample file: {SAMPLE_GEOJSON_PATH}"


def test_geojson_is_valid_json():
    with open(SAMPLE_GEOJSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_geojson_structure_and_metadata():
    with open(SAMPLE_GEOJSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("type") == "FeatureCollection"
    assert "metadata" in data
    metadata = data["metadata"]
    assert metadata.get("is_synthetic") is True
    assert "warning" in metadata
    assert "provenance" in metadata
    assert "study_area" in metadata


def test_geojson_features_validity():
    with open(SAMPLE_GEOJSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    assert len(features) >= 3

    for feature in features:
        assert feature.get("type") == "Feature"
        assert "id" in feature
        assert "properties" in feature
        assert "geometry" in feature

        # Geometry validation
        geom = feature["geometry"]
        assert geom.get("type") == "Polygon"
        coords = geom.get("coordinates")
        assert isinstance(coords, list)
        assert len(coords) >= 1  # outer ring
        outer_ring = coords[0]
        assert len(outer_ring) >= 4  # closed polygon has at least 4 vertices
        # First and last vertex match (closed ring)
        assert outer_ring[0] == outer_ring[-1]

        # Properties validation
        props = feature["properties"]
        assert "parcel_id" in props
        assert "name" in props
        assert "demo_baseline_risk" in props
        assert "demo_delta_risk" in props
        assert "demo_tree_count" in props
        assert "is_excluded" in props
        assert props.get("is_synthetic") is True
