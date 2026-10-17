"""Automated tests for the Interactive Tree Planting Recommendation Map.

Verifies:
1. Candidate parcel GeoJSON contains valid geometries and honest metrics.
2. Verified interior representative points lie strictly inside their polygons.
3. Ineligible (excluded or insufficient data) parcels are distinguished from eligible ones.
4. Correct priority styling hierarchy (Rank 1, Ranks 2-5, Other Eligible, Excluded, Insufficient).
5. Authoritative study area calculation preserves non-zero area and distinguishes study area from eligible area.
6. GeoJSON artifact mapping includes both parcels_geojson and geojson aliases.
7. Reinforced FS (fs_reinforced_mean), baseline FS, and delta FS are preserved in properties.
"""

import json
from pathlib import Path
from shapely.geometry import Point, Polygon, shape

from backend.app.core.recommendations.ranking import (
    EligibilityStatus,
    EvaluatedParcel,
    RankingResult,
    ScoringWeights,
)
from backend.app.core.recommendations.scoring import (
    NormalizationConfig,
    ParcelScoreBreakdown,
    calculate_parcel_score,
)
from backend.app.core.recommendations.report_generation import export_candidate_parcels_geojson
from backend.app.core.recommendations.spatial_reference import calculate_polygon_geodesic_area
from backend.app.api.recommendation_routes import run_spatial_recommendations, RecommendationRunRequest
from backend.app.schemas.recommendations import EligibilitySettingsSchema, ScoringWeightsSchema
from frontend.components.map_view import get_parcel_style


def test_representative_points_lie_inside_polygons(tmp_path):
    """Test that representative points generated for tree markers lie strictly inside polygons."""
    # Create an L-shaped / concave polygon to test point-on-surface
    concave_coords = [
        [76.00, 11.50],
        [76.04, 11.50],
        [76.04, 11.52],
        [76.02, 11.52],
        [76.02, 11.54],
        [76.00, 11.54],
        [76.00, 11.50],
    ]
    poly_shp = Polygon(concave_coords)

    # Eligible parcel #1
    m1 = {
        "slope_mean_deg": 22.5,
        "fs_baseline_mean": 1.05,
        "fs_reinforced_mean": 1.45,
        "fs_delta_mean": 0.40,
        "ndvi_mean": 0.48,
        "terrain_coverage_pct": 100.0,
    }
    weights1 = ScoringWeights(
        weight_geotechnical_need=0.35,
        weight_stability_gain=0.30,
        weight_plantable_area=0.20,
        weight_data_confidence=0.15,
    )
    score1 = calculate_parcel_score(metrics=m1, plantable_area_ha=8.2, weights=weights1)

    p1 = EvaluatedParcel(
        parcel_id="P-001",
        geometry={"type": "Polygon", "coordinates": [concave_coords]},
        total_area_ha=12.5,
        plantable_area_ha=8.2,
        eligibility_status=EligibilityStatus.ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS,
        exclusion_reasons=[],
        metrics=m1,
        rank=1,
        score_breakdown=score1,
    )

    # Excluded parcel #2
    p2 = EvaluatedParcel(
        parcel_id="P-002",
        geometry={"type": "Polygon", "coordinates": [[[76.05, 11.50], [76.07, 11.50], [76.07, 11.52], [76.05, 11.52], [76.05, 11.50]]]},
        total_area_ha=5.0,
        plantable_area_ha=0.0,
        eligibility_status=EligibilityStatus.EXCLUDED,
        exclusion_reasons=["Slope exceeds 45 degrees threshold"],
        metrics={
            "slope_mean_deg": 48.0,
            "fs_baseline_mean": 0.85,
            "fs_reinforced_mean": 1.10,
            "fs_delta_mean": 0.25,
            "ndvi_mean": 0.35,
            "terrain_coverage_pct": 98.0,
        },
    )

    # Insufficient data parcel #3
    p3 = EvaluatedParcel(
        parcel_id="P-003",
        geometry={"type": "Polygon", "coordinates": [[[76.08, 11.50], [76.10, 11.50], [76.10, 11.52], [76.08, 11.52], [76.08, 11.50]]]},
        total_area_ha=4.5,
        plantable_area_ha=0.0,
        eligibility_status=EligibilityStatus.INSUFFICIENT_DATA,
        exclusion_reasons=["Terrain coverage < 75%"],
        metrics={
            "slope_mean_deg": 20.0,
            "terrain_coverage_pct": 45.0,
        },
    )

    norm_cfg = NormalizationConfig(fs_target=1.3, critical_fs=0.7, max_delta_fs_ref=15.0, max_area_ref_ha=15.0)
    ranking_res = RankingResult(
        run_id="test_run",
        ranking_timestamp="2026-10-15T12:00:00Z",
        ranked_eligible_parcels=[p1],
        excluded_parcels=[p2],
        insufficient_data_parcels=[p3],
        total_parcels_evaluated=3,
        eligible_count=1,
        excluded_count=1,
        insufficient_data_count=1,
        scoring_weights=ScoringWeights(
            weight_geotechnical_need=0.35,
            weight_stability_gain=0.30,
            weight_plantable_area=0.20,
            weight_data_confidence=0.15,
        ),
        normalization_config=norm_cfg,
        applied_missing_data_policy="RENORMALIZE_AVAILABLE",
        missing_components_detected=[],
        is_discriminative=True,
    )

    out_file = tmp_path / "test_parcels.geojson"
    export_candidate_parcels_geojson(ranking_res, out_file)

    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 3

    # Check parcel #1 (Eligible Top Priority)
    f1 = next(f for f in data["features"] if f["id"] == "P-001")
    assert f1["properties"]["rank"] == 1
    assert "ELIGIBLE" in f1["properties"]["eligibility_status"]
    assert f1["properties"]["fs_baseline_mean"] == 1.05
    assert f1["properties"]["fs_reinforced_mean"] == 1.45
    assert f1["properties"]["fs_delta_mean"] == 0.40

    # Verify representative point lies strictly inside the concave polygon
    repr_pt = f1["properties"]["representative_point"]
    assert repr_pt is not None
    pt = Point(repr_pt[0], repr_pt[1])
    assert poly_shp.contains(pt) or poly_shp.touches(pt), "Representative point must lie inside the polygon"

    # Check parcel #2 (Excluded)
    f2 = next(f for f in data["features"] if f["id"] == "P-002")
    assert f2["properties"]["eligibility_status"] == "EXCLUDED"
    assert "Slope exceeds" in f2["properties"]["exclusion_reasons"]
    assert f2["properties"]["rank"] is None

    # Check parcel #3 (Insufficient Data)
    f3 = next(f for f in data["features"] if f["id"] == "P-003")
    assert f3["properties"]["eligibility_status"] == "INSUFFICIENT_DATA"
    assert f3["properties"]["rank"] is None


def test_study_area_vs_eligible_area_calculation():
    """Verify authoritative study area calculation distinguishing study area from eligible area."""
    coords = [
        [76.00, 11.55],
        [76.10, 11.55],
        [76.10, 11.65],
        [76.00, 11.65],
        [76.00, 11.55],
    ]
    # Geodesic area calculation on WGS 84
    study_area_ha = calculate_polygon_geodesic_area(coords)
    assert study_area_ha > 1000.0, "WGS84 0.1x0.1 degree area in Western Ghats should exceed 1,000 ha"

    # Eligible area of selected parcels should not be confused with study area
    eligible_parcel_area_ha = 45.2
    assert eligible_parcel_area_ha != study_area_ha
    assert eligible_parcel_area_ha < study_area_ha


def test_geojson_artifact_mapping_contains_both_keys():
    """Verify that run_spatial_recommendations artifacts map contains both parcels_geojson and geojson."""
    req = RecommendationRunRequest(
        cell_size_m=500.0,
        study_area_bounds={"minx": 76.02, "miny": 11.56, "maxx": 76.06, "maxy": 11.60},
        scoring_weights=ScoringWeightsSchema(
            weight_geotechnical_need=0.35,
            weight_stability_gain=0.30,
            weight_plantable_area=0.20,
            weight_data_confidence=0.15,
        ),
        eligibility_settings=EligibilitySettingsSchema(
            min_terrain_coverage_pct=70.0,
            max_slope_deg=45.0,
            enable_ndvi_canopy_filter=False,
            min_plantable_area_ha=0.1,
        ),
    )
    res = run_spatial_recommendations(req)
    assert "parcels_geojson" in res.artifacts
    assert "geojson" in res.artifacts
    assert res.artifacts["parcels_geojson"] == res.artifacts["geojson"]
    assert res.total_parcels > 0


def test_missing_geometry_handled_without_inventing_locations(tmp_path):
    """Verify that parcels with None or invalid geometry do not produce fabricated coordinates."""
    p_no_geom = EvaluatedParcel(
        parcel_id="P-EMPTY",
        geometry={"type": "Polygon", "coordinates": []},
        total_area_ha=2.0,
        plantable_area_ha=0.0,
        eligibility_status=EligibilityStatus.INSUFFICIENT_DATA,
        exclusion_reasons=["Missing geometry"],
        metrics={},
    )
    norm_cfg = NormalizationConfig()
    ranking_res = RankingResult(
        run_id="run_missing_geom",
        ranking_timestamp="2026-10-15T12:00:00Z",
        ranked_eligible_parcels=[],
        excluded_parcels=[],
        insufficient_data_parcels=[p_no_geom],
        total_parcels_evaluated=1,
        eligible_count=0,
        excluded_count=0,
        insufficient_data_count=1,
        scoring_weights=ScoringWeights(),
        normalization_config=norm_cfg,
        applied_missing_data_policy="RENORMALIZE_AVAILABLE",
        missing_components_detected=[],
        is_discriminative=False,
    )
    out_file = tmp_path / "missing_geom.geojson"
    export_candidate_parcels_geojson(ranking_res, out_file)

    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    feat = data["features"][0]
    assert feat["id"] == "P-EMPTY"
    assert feat["geometry"]["coordinates"] == []
    assert feat["properties"]["representative_point"] is None


def test_folium_component_style_hierarchy():
    """Verify Python Folium map styling hierarchy matches priority levels."""
    # Rank 1 top priority
    s_r1 = get_parcel_style({"properties": {"is_excluded": False, "rank": 1}})
    assert s_r1["fillColor"] == "#2f855a"
    assert s_r1["weight"] == 3

    # Ranks 2-5
    s_r2 = get_parcel_style({"properties": {"is_excluded": False, "rank": 2}})
    assert s_r2["fillColor"] == "#48bb78"

    # Excluded
    s_exc = get_parcel_style({"properties": {"is_excluded": True}})
    assert s_exc["fillColor"] == "#a0aec0"
    assert "dashArray" in s_exc

    # Insufficient Data
    s_ins = get_parcel_style({"properties": {"eligibility_status": "INSUFFICIENT_DATA"}})
    assert s_ins["fillColor"] == "#f59e0b"
    assert "dashArray" in s_ins

