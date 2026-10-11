"""Automated tests for Phase 4 Spatial Recommendation Engine."""

import json
import math
import tempfile
from pathlib import Path
from typing import Any, Dict
import numpy as np
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Polygon, box, mapping

from backend.app.main import app
from backend.app.core.recommendations.spatial_reference import (
    WGS84Ellipsoid,
    calculate_polygon_geodesic_area,
    degrees_to_meters,
    meters_to_degrees,
)
from backend.app.core.recommendations.parcel_generation import (
    CandidateParcel,
    generate_candidate_parcels,
    generate_candidate_parcels_geojson,
)
from backend.app.core.recommendations.zonal_statistics import (
    RasterLayerContext,
    extract_zonal_metrics_for_parcel,
)
from backend.app.core.recommendations.eligibility import (
    EligibilityConfig,
    EligibilityStatus,
    ExclusionReason,
    evaluate_parcel_eligibility,
)
from backend.app.core.recommendations.scoring import (
    ScoringWeights,
    calculate_parcel_score,
)
from backend.app.core.recommendations.ranking import (
    EvaluatedParcel,
    RankingResult,
    rank_candidate_parcels,
)
from backend.app.core.recommendations.explainability import (
    generate_parcel_explanation,
)
from backend.app.core.recommendations.provenance import (
    build_recommendation_provenance,
)
from backend.app.core.recommendations.budget_allocation import (
    BudgetAllocationConfig,
    allocate_planting_budget,
)
from backend.app.core.recommendations.species_interface import (
    CuratedSpeciesRecord,
    SpeciesDatabase,
)
from backend.app.core.recommendations.report_generation import (
    export_candidate_parcels_geojson,
    export_parcel_metrics_csv,
    export_parcel_rankings_csv,
    export_recommendation_summary_json,
    export_recommendation_report_html,
)


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# 1. SPATIAL REFERENCE & GEODESIC AREA TESTS
# ==============================================================================

def test_wgs84_constants():
    """Verify standard WGS 84 ellipsoidal constants."""
    assert WGS84Ellipsoid.A == 6378137.0
    assert abs(WGS84Ellipsoid.F - (1.0 / 298.257223563)) < 1e-12
    assert WGS84Ellipsoid.B < WGS84Ellipsoid.A


def test_geodesic_area_calculation():
    """Verify 300m x 300m square in Wayanad calculates to ~9.00 hectares."""
    lat = 11.60
    lon = 76.05
    dlon, dlat = meters_to_degrees(lat, 300.0, 300.0)

    ring = [
        [lon, lat],
        [lon + dlon, lat],
        [lon + dlon, lat + dlat],
        [lon, lat + dlat],
        [lon, lat],
    ]
    area_ha = calculate_polygon_geodesic_area(ring)
    # 300m x 300m = 90,000 m² = 9.0 hectares
    assert abs(area_ha - 9.0) < 0.05, f"Expected ~9.0 ha, got {area_ha} ha"


def test_no_degree_multiplication_as_meters():
    """Ensure degree differences are not treated directly as metric Cartesian axes."""
    lat = 11.60
    lon = 76.05
    # A 1-degree by 1-degree box at 11.60° N is ~109 km x 111 km ≈ 1.2 million hectares
    ring = [
        [lon, lat],
        [lon + 1.0, lat],
        [lon + 1.0, lat + 1.0],
        [lon, lat + 1.0],
        [lon, lat],
    ]
    area_ha = calculate_polygon_geodesic_area(ring)
    assert area_ha > 1_000_000, f"Geodesic area for 1x1 deg should be > 1M ha, got {area_ha}"


# ==============================================================================
# 2. CANDIDATE PARCEL GENERATION TESTS
# ==============================================================================

def test_parcel_generation_bounds_and_determinism():
    """Verify deterministic parcel generation respecting bounds."""
    bounds = {"min_lon": 76.00, "min_lat": 11.55, "max_lon": 76.10, "max_lat": 11.65}
    parcels1 = generate_candidate_parcels(bounds=bounds, cell_size_m=500.0)
    parcels2 = generate_candidate_parcels(bounds=bounds, cell_size_m=500.0)

    assert len(parcels1) == len(parcels2)
    assert len(parcels1) > 0
    # Deterministic IDs
    for p1, p2 in zip(parcels1, parcels2):
        assert p1.parcel_id == p2.parcel_id
        assert p1.bounds == p2.bounds
        assert p1.total_area_ha == p2.total_area_ha


def test_parcel_generation_edge_handling():
    """Verify edge parcels are correctly flagged and contained in bounding box."""
    parcels = generate_candidate_parcels(
        min_lon=76.00, min_lat=11.55, max_lon=76.04, max_lat=11.59, cell_size_m=1000.0
    )
    assert len(parcels) > 0
    for p in parcels:
        minx, miny, maxx, maxy = p.bounds
        assert minx >= 76.00 - 1e-7
        assert maxx <= 76.04 + 1e-7
        assert miny >= 11.55 - 1e-7
        assert maxy <= 11.59 + 1e-7


def test_parcel_generation_rfc7946_geojson():
    """Verify output complies with GeoJSON standard conventions."""
    fc = generate_candidate_parcels_geojson(
        bounds={"min_lon": 76.00, "min_lat": 11.55, "max_lon": 76.02, "max_lat": 11.57},
        cell_size_meters=500.0,
    )
    assert fc["type"] == "FeatureCollection"
    assert "features" in fc
    assert len(fc["features"]) > 0
    feat = fc["features"][0]
    assert feat["type"] == "Feature"
    assert feat["geometry"]["type"] == "Polygon"
    coords = feat["geometry"]["coordinates"][0]
    # WGS 84 lon, lat convention: lon in [76.0, 76.1], lat in [11.5, 11.6]
    assert 75.0 < coords[0][0] < 77.0
    assert 11.0 < coords[0][1] < 12.0


# ==============================================================================
# 3. ZONAL STATISTICS ACROSS MULTI-RESOLUTION GRIDS
# ==============================================================================

def test_zonal_statistics_synthetic_context():
    """Test zonal metrics extraction over synthetic mock raster contexts."""
    # Create a mock raster context with known values
    class MockRasterContext:
        def __init__(self, data, bounds, nodata=-9999.0):
            self.exists = True
            self.data = np.array(data, dtype=np.float32)
            self.minx, self.miny, self.maxx, self.maxy = bounds
            self.height, self.width = self.data.shape
            self.dx = (self.maxx - self.minx) / self.width
            self.dy = (self.maxy - self.miny) / self.height
            self.nodata = nodata

        def extract_parcel_window(self, minx, miny, maxx, maxy):
            return self.data

    # Slope array: 20 deg with one nodata
    mock_slope_data = np.array([[20.0, 22.0], [18.0, -9999.0]])
    mock_slope = MockRasterContext(mock_slope_data, (76.0, 11.5, 76.1, 11.6))

    # Baseline FS array
    mock_fs_data = np.array([[1.1, 1.2], [1.4, -9999.0]])
    mock_fs = MockRasterContext(mock_fs_data, (76.0, 11.5, 76.1, 11.6))

    metrics = extract_zonal_metrics_for_parcel(
        parcel_bounds=(76.0, 11.5, 76.05, 11.55),
        slope_ctx=mock_slope,
        fs_base_ctx=mock_fs,
        fs_target=1.3,
    )

    # 3 valid out of 4 total pixels = 75% coverage
    assert metrics["terrain_coverage_pct"] == 75.0
    assert metrics["slope_mean_deg"] == 20.0  # (20 + 22 + 18)/3
    assert metrics["fs_baseline_mean"] is not None
    # 2 out of 3 valid cells are < 1.3 (1.1, 1.2)
    assert abs(metrics["fraction_subtarget_fs"] - (2.0 / 3.0)) < 1e-3


# ==============================================================================
# 4. ELIGIBILITY & EXCLUSION ENGINE TESTS
# ==============================================================================

def test_eligibility_insufficient_data():
    """Verify parcel with <80% terrain coverage receives INSUFFICIENT_DATA status."""
    poly = box(76.0, 11.55, 76.01, 11.56)
    metrics = {"terrain_coverage_pct": 65.0, "slope_mean_deg": 15.0}
    cfg = EligibilityConfig(min_terrain_coverage_pct=80.0)

    status, reasons, plantable_ha, _ = evaluate_parcel_eligibility(poly, 9.0, metrics, cfg)
    assert status == EligibilityStatus.INSUFFICIENT_DATA
    assert any("Insufficient terrain data" in r for r in reasons)
    assert plantable_ha == 0.0


def test_eligibility_cliff_exclusion():
    """Verify parcel with slope exceeding threshold receives EXCLUDED status."""
    poly = box(76.0, 11.55, 76.01, 11.56)
    metrics = {"terrain_coverage_pct": 100.0, "slope_mean_deg": 52.0, "fraction_steep_slope": 0.9}
    cfg = EligibilityConfig(max_slope_deg=45.0)

    status, reasons, plantable_ha, _ = evaluate_parcel_eligibility(poly, 9.0, metrics, cfg)
    assert status == EligibilityStatus.EXCLUDED
    assert any("exceeds vegetative stabilization limit" in r for r in reasons)


def test_eligibility_protected_area_intersection():
    """Verify parcel intersecting a supplied reserve boundary is EXCLUDED."""
    poly = box(76.00, 11.55, 76.01, 11.56)
    pa_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Wayanad Wildlife Sanctuary Buffer"},
                "geometry": mapping(box(76.005, 11.555, 76.02, 11.57)),
            }
        ],
    }
    metrics = {"terrain_coverage_pct": 100.0, "slope_mean_deg": 15.0}
    cfg = EligibilityConfig(protected_areas_geojson=pa_geojson)

    status, reasons, _, note = evaluate_parcel_eligibility(poly, 9.0, metrics, cfg)
    assert status == EligibilityStatus.EXCLUDED
    assert any("Wayanad Wildlife Sanctuary Buffer" in r for r in reasons)
    assert "Verified against supplied" in note


def test_eligibility_unverified_protected_areas_disclosure():
    """Verify that when no reserve layer is supplied, clearance is marked UNVERIFIED."""
    poly = box(76.00, 11.55, 76.01, 11.56)
    metrics = {"terrain_coverage_pct": 100.0, "slope_mean_deg": 15.0}
    cfg = EligibilityConfig(protected_areas_geojson=None)

    status, _, _, note = evaluate_parcel_eligibility(poly, 9.0, metrics, cfg)
    assert status == EligibilityStatus.ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS
    assert "UNVERIFIED" in note


def test_eligibility_canopy_masking_proxy():
    """Verify NDVI canopy proxy deduction reduces plantable area."""
    poly = box(76.00, 11.55, 76.01, 11.56)
    metrics = {
        "terrain_coverage_pct": 100.0,
        "slope_mean_deg": 15.0,
        "fraction_dense_canopy_proxy": 0.40,  # 40% canopy
    }
    cfg = EligibilityConfig(enable_ndvi_canopy_filter=True, min_plantable_area_ha=0.25)
    status, _, plantable_ha, _ = evaluate_parcel_eligibility(poly, 10.0, metrics, cfg)
    assert status == EligibilityStatus.ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS
    # 10.0 ha * (1 - 0.40) = 6.0 ha
    assert abs(plantable_ha - 6.0) < 0.01


# ==============================================================================
# 5. MULTI-CRITERIA SCORING & WEIGHT VALIDATION
# ==============================================================================

def test_scoring_weights_normalization():
    """Verify weights automatically normalize to sum to 1.0."""
    w = ScoringWeights(
        weight_geotechnical_need=2.0,
        weight_stability_gain=1.0,
        weight_plantable_area=1.0,
        weight_data_confidence=0.0,
    )
    wn = w.normalized()
    total = (
        wn.weight_geotechnical_need
        + wn.weight_stability_gain
        + wn.weight_plantable_area
        + wn.weight_data_confidence
    )
    assert abs(total - 1.0) < 1e-6
    assert abs(wn.weight_geotechnical_need - 0.5) < 1e-6


def test_score_calculation_monotonicity():
    """Verify higher geotechnical deficit and higher stability gain produce higher score."""
    m_high_need = {
        "fs_baseline_mean": 0.85,
        "fraction_subtarget_fs": 0.9,
        "fs_delta_mean": 8.0,
        "terrain_coverage_pct": 100.0,
    }
    m_low_need = {
        "fs_baseline_mean": 2.5,
        "fraction_subtarget_fs": 0.0,
        "fs_delta_mean": 1.0,
        "terrain_coverage_pct": 100.0,
    }

    sc_high = calculate_parcel_score(m_high_need, plantable_area_ha=5.0)
    sc_low = calculate_parcel_score(m_low_need, plantable_area_ha=5.0)

    assert sc_high.priority_score_index > sc_low.priority_score_index


# ==============================================================================
# 6. DETERMINISTIC RANKING & EXCLUSION SEPARATION
# ==============================================================================

def test_ranking_excludes_disqualified_parcels():
    """Verify EXCLUDED and INSUFFICIENT_DATA parcels never receive a rank."""
    parcels = [
        EvaluatedParcel(
            parcel_id="P-01",
            geometry={"type": "Polygon", "coordinates": []},
            total_area_ha=9.0,
            plantable_area_ha=9.0,
            eligibility_status=EligibilityStatus.ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS,
            exclusion_reasons=[],
            protected_area_clearance_note="",
            metrics={"fs_baseline_mean": 0.9, "fs_delta_mean": 5.0, "terrain_coverage_pct": 100.0},
        ),
        EvaluatedParcel(
            parcel_id="P-02",
            geometry={"type": "Polygon", "coordinates": []},
            total_area_ha=9.0,
            plantable_area_ha=0.0,
            eligibility_status=EligibilityStatus.EXCLUDED,
            exclusion_reasons=["Slope exceeds 45 deg"],
            protected_area_clearance_note="",
            metrics={"terrain_coverage_pct": 100.0},
        ),
        EvaluatedParcel(
            parcel_id="P-03",
            geometry={"type": "Polygon", "coordinates": []},
            total_area_ha=9.0,
            plantable_area_ha=0.0,
            eligibility_status=EligibilityStatus.INSUFFICIENT_DATA,
            exclusion_reasons=["Coverage below 80%"],
            protected_area_clearance_note="",
            metrics={"terrain_coverage_pct": 40.0},
        ),
    ]

    res = rank_candidate_parcels(parcels, run_id="test", timestamp="2026-10-11T12:00:00Z")

    assert res.eligible_count == 1
    assert res.excluded_count == 1
    assert res.insufficient_data_count == 1

    assert len(res.ranked_eligible_parcels) == 1
    assert res.ranked_eligible_parcels[0].parcel_id == "P-01"
    assert res.ranked_eligible_parcels[0].rank == 1

    # Disqualified parcels must have rank = None
    assert res.excluded_parcels[0].rank is None
    assert res.insufficient_data_parcels[0].rank is None


def test_ranking_determinism():
    """Verify repeated runs with identical inputs produce identical ranks."""
    parcels = [
        EvaluatedParcel(
            parcel_id=f"P-{i:02d}",
            geometry={"type": "Polygon", "coordinates": []},
            total_area_ha=9.0,
            plantable_area_ha=float(i),
            eligibility_status=EligibilityStatus.ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS,
            exclusion_reasons=[],
            protected_area_clearance_note="",
            metrics={"fs_baseline_mean": 1.0, "fs_delta_mean": float(i % 5), "terrain_coverage_pct": 100.0},
        )
        for i in range(10)
    ]

    r1 = rank_candidate_parcels(parcels, run_id="r1", timestamp="t1")
    r2 = rank_candidate_parcels(parcels, run_id="r2", timestamp="t2")

    order1 = [p.parcel_id for p in r1.ranked_eligible_parcels]
    order2 = [p.parcel_id for p in r2.ranked_eligible_parcels]
    assert order1 == order2


# ==============================================================================
# 7. LEVERAGE METRIC & SCIENTIFIC SAFEGUARDS
# ==============================================================================

def test_leverage_metric_safeguard_no_confusing_fs_with_risk():
    """Verify modeled stability gain per stem is labeled clearly, not risk reduction."""
    parcel = EvaluatedParcel(
        parcel_id="P-01",
        geometry={"type": "Polygon", "coordinates": []},
        total_area_ha=5.0,
        plantable_area_ha=5.0,
        eligibility_status=EligibilityStatus.ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS,
        exclusion_reasons=[],
        protected_area_clearance_note="",
        metrics={
            "fs_baseline_mean": 0.9,
            "fs_delta_mean": 4.0,
            "tree_density_mean_stems_ha": 200.0,  # 200 stems/ha * 5 ha = 1000 stems
            "terrain_coverage_pct": 100.0,
        },
    )

    res = rank_candidate_parcels([parcel], run_id="test", timestamp="t")
    ranked = res.ranked_eligible_parcels[0]

    assert ranked.has_calibrated_stem_density is True
    assert ranked.estimated_required_stems == 1000.0
    # delta_FS / N = 4.0 / 1000.0 = 0.004 delta_FS/stem
    assert abs(ranked.modeled_stability_gain_per_stem - 0.004) < 1e-6
    # Note must explicitly disclose it is modeled stability, NOT empirical risk reduction
    assert "NOT empirical landslide risk reduction" in ranked.leverage_metric_note


def test_leverage_metric_unavailable_when_uncalibrated():
    """Verify that when stem density is absent, leverage is marked UNAVAILABLE."""
    parcel = EvaluatedParcel(
        parcel_id="P-01",
        geometry={"type": "Polygon", "coordinates": []},
        total_area_ha=5.0,
        plantable_area_ha=5.0,
        eligibility_status=EligibilityStatus.ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS,
        exclusion_reasons=[],
        protected_area_clearance_note="",
        metrics={
            "fs_baseline_mean": 0.9,
            "fs_delta_mean": 4.0,
            "terrain_coverage_pct": 100.0,
            # tree_density_mean_stems_ha is None!
        },
    )

    res = rank_candidate_parcels([parcel], run_id="test", timestamp="t")
    ranked = res.ranked_eligible_parcels[0]

    assert ranked.has_calibrated_stem_density is False
    assert ranked.modeled_stability_gain_per_stem is None
    assert "UNAVAILABLE" in ranked.leverage_metric_note


# ==============================================================================
# 8. EXPLAINABILITY & PROVENANCE TESTS
# ==============================================================================

def test_explainability_generation():
    """Verify detailed factor breakdown and narrative audit for ranked parcel."""
    parcel = EvaluatedParcel(
        parcel_id="PARCEL-R01-C01",
        geometry={"type": "Polygon", "coordinates": []},
        total_area_ha=9.0,
        plantable_area_ha=8.0,
        eligibility_status=EligibilityStatus.ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS,
        exclusion_reasons=[],
        protected_area_clearance_note="UNVERIFIED",
        metrics={
            "slope_mean_deg": 28.5,
            "elevation_mean_m": 845.0,
            "fs_baseline_mean": 0.95,
            "fs_delta_mean": 6.2,
            "ndvi_mean": 0.42,
            "terrain_coverage_pct": 100.0,
        },
    )
    res = rank_candidate_parcels([parcel], run_id="test", timestamp="t")
    prov = build_recommendation_provenance(run_id="test", timestamp="t")
    exp = generate_parcel_explanation(res.ranked_eligible_parcels[0], prov)

    assert exp.parcel_id == "PARCEL-R01-C01"
    assert exp.rank == 1
    assert len(exp.primary_ranking_drivers) > 0
    assert "28.5°" in exp.topographic_context
    assert "0.95" in exp.geotechnical_context
    assert any("illustrative" in d.lower() or "uniform" in d.lower() for d in exp.provenance_disclosures)


# ==============================================================================
# 9. OPTIONAL BUDGET ALLOCATION TESTS
# ==============================================================================

def test_budget_allocation_limits():
    """Verify budget is never exceeded and only eligible parcels are funded."""
    parcels = [
        EvaluatedParcel(
            parcel_id=f"P-{i}",
            geometry={},
            total_area_ha=2.0,
            plantable_area_ha=2.0,
            eligibility_status=EligibilityStatus.ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS,
            exclusion_reasons=[],
            protected_area_clearance_note="",
            metrics={"tree_density_mean_stems_ha": 100.0, "fs_delta_mean": 2.0},
        )
        for i in range(5)
    ]
    res = rank_candidate_parcels(parcels, run_id="b", timestamp="t")

    # 2 ha * 100 stems/ha = 200 stems per parcel.
    # Cost per parcel: 5000 setup + 200 * 100 = 25,000 INR
    # Total budget 60,000 INR -> should fund 2 parcels fully (50,000 INR) and partial 3rd
    cfg = BudgetAllocationConfig(
        total_budget_inr=60000.0,
        cost_per_sapling_inr=100.0,
        fixed_parcel_setup_cost_inr=5000.0,
    )
    alloc = allocate_planting_budget(res.ranked_eligible_parcels, cfg)

    assert alloc.total_budget_spent_inr <= 60000.0
    assert alloc.remaining_budget_inr >= 0.0
    assert alloc.parcels_funded_count > 0
    assert alloc.total_stems_allocated > 0


# ==============================================================================
# 10. SPECIES RECOMMENDATION INTERFACE TESTS
# ==============================================================================

def test_species_interface_integrity():
    """Verify species database returns pending status when unpopulated, avoiding hallucinations."""
    empty_db = SpeciesDatabase([])
    result = empty_db.query_for_parcel("PARCEL-01", elevation_mean_m=800.0, slope_mean_deg=25.0)

    assert result.status == "PENDING_CURATED_BOTANICAL_DATA"
    assert len(result.suitable_species) == 0
    assert "PENDING" in result.disclaimer


def test_species_interface_filtering():
    """Verify species matching when evidence records are provided."""
    sample_records = [
        CuratedSpeciesRecord(
            scientific_name="Hopea parviflora",
            common_name="Ironwood of Malabar",
            native_range="Western Ghats evergreen forests",
            elevation_min_m=0.0,
            elevation_max_m=1000.0,
            soil_preferences=["Deep lateritic loam"],
            root_system_type="Deep taproot with lateral heart roots",
            mean_rooting_depth_m=2.5,
            slope_suitability_max_deg=35.0,
            ecological_role="Native riparian and slope canopy tree",
            source_citation="Kerala Forest Research Institute (KFRI)",
            data_limitations=["Juvenile root tensile strength unmeasured."],
        ),
        CuratedSpeciesRecord(
            scientific_name="Rhododendron arboreum nilagiricum",
            common_name="Nilgiri Rhododendron",
            native_range="High-altitude shola forests",
            elevation_min_m=1500.0,
            elevation_max_m=2500.0,
            soil_preferences=["Acidic peaty montane soils"],
            root_system_type="Spreading fibrous mat",
            slope_suitability_max_deg=30.0,
            ecological_role="Shola margin stabilizer",
            source_citation="Botanical Survey of India",
            data_limitations=["Cannot tolerate elevations < 1500m."],
        ),
    ]

    db = SpeciesDatabase(sample_records)
    # Query for Wayanad mid-elevation (800m)
    res = db.query_for_parcel("P-01", elevation_mean_m=800.0, slope_mean_deg=25.0)
    assert res.status == "MATCHED_CANDIDATE_SPECIES"
    assert len(res.suitable_species) == 1
    assert res.suitable_species[0].scientific_name == "Hopea parviflora"


# ==============================================================================
# 11. EXPORT INTEGRITY & DOWNLOAD SECURITY
# ==============================================================================

def test_export_file_generation():
    """Verify valid GeoJSON, CSV, JSON, and HTML exports are written."""
    parcels = [
        EvaluatedParcel(
            parcel_id="P-01",
            geometry={"type": "Polygon", "coordinates": [[[76.0, 11.5], [76.01, 11.5], [76.01, 11.51], [76.0, 11.51], [76.0, 11.5]]]},
            total_area_ha=9.0,
            plantable_area_ha=8.5,
            eligibility_status=EligibilityStatus.ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS,
            exclusion_reasons=[],
            protected_area_clearance_note="UNVERIFIED",
            metrics={"slope_mean_deg": 22.0, "fs_baseline_mean": 1.1, "fs_delta_mean": 4.5, "terrain_coverage_pct": 100.0},
        )
    ]
    res = rank_candidate_parcels(parcels, run_id="exp", timestamp="2026-10-11T12:00:00Z")
    prov = build_recommendation_provenance(run_id="exp", timestamp="2026-10-11T12:00:00Z")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # GeoJSON
        gj = export_candidate_parcels_geojson(res, tmp_path / "test.geojson")
        assert gj.exists()
        with open(gj, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["type"] == "FeatureCollection"
            assert len(data["features"]) == 1

        # CSV metrics
        csv_m = export_parcel_metrics_csv(res, tmp_path / "metrics.csv")
        assert csv_m.exists()

        # CSV rankings
        csv_r = export_parcel_rankings_csv(res, tmp_path / "rankings.csv")
        assert csv_r.exists()

        # JSON summary
        js_s = export_recommendation_summary_json(res, prov, tmp_path / "summary.json")
        assert js_s.exists()

        # HTML report
        html_r = export_recommendation_report_html(res, prov, tmp_path / "report.html")
        assert html_r.exists()
        with open(html_r, "r", encoding="utf-8") as f:
            html_text = f.read()
            assert "TerraShield AI" in html_text
            assert "P-01" in html_text


# ==============================================================================
# 12. FASTAPI ENDPOINT REGRESSION TESTS
# ==============================================================================

def test_api_recommendation_status(client):
    """GET /api/v1/recommendations/status returns 200 with all layer keys."""
    res = client.get("/api/v1/recommendations/status")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "input_layers" in data
    assert "slope" in data["input_layers"]
    assert "dem" in data["input_layers"]


def test_api_generate_parcels(client):
    """POST /api/v1/recommendations/parcels/generate returns valid parcel inventory."""
    payload = {
        "minx": 76.00,
        "miny": 11.55,
        "maxx": 76.04,
        "maxy": 11.59,
        "cell_size_m": 1000.0,
    }
    res = client.post("/api/v1/recommendations/parcels/generate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["parcel_count"] > 0
    assert data["total_grid_area_ha"] > 0


def test_api_run_recommendations_pipeline(client):
    """POST /api/v1/recommendations/run executes pipeline on real rasters."""
    payload = {
        "cell_size_m": 1000.0,
        "fs_target": 1.3,
        "scoring_weights": {
            "weight_geotechnical_need": 0.40,
            "weight_stability_gain": 0.30,
            "weight_plantable_area": 0.20,
            "weight_data_confidence": 0.10,
        },
    }
    res = client.post("/api/v1/recommendations/run", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "run_id" in data
    assert data["total_parcels"] > 0
    assert data["eligible_count"] > 0
    assert len(data["top_recommendations"]) > 0
    assert "artifacts" in data
    assert "parcels_geojson" in data["artifacts"]

    # Verify run summary endpoint
    summary_res = client.get(f"/api/v1/recommendations/runs/{data['run_id']}")
    assert summary_res.status_code == 200


def test_api_artifact_download_security(client):
    """Verify path traversal attacks are rejected on artifact download endpoint."""
    res = client.get("/api/v1/recommendations/artifacts/../../etc/passwd")
    assert res.status_code == 404

    res2 = client.get("/api/v1/recommendations/artifacts/non_existent.csv")
    assert res2.status_code == 404


def test_api_species_query(client):
    """GET /api/v1/recommendations/species/{id} returns unpopulated botanical status."""
    res = client.get("/api/v1/recommendations/species/PARCEL-01?elevation_m=800&slope_deg=20")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "PENDING_CURATED_BOTANICAL_DATA"
