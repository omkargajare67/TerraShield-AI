"""Phase 5 Comprehensive Integration, End-to-End, and Security Regression Test Suite.

Exercises complete application data flows across:
- TEST A: Application Health and Error Handling Contracts
- TEST B: Geospatial Data Flow & Dimension/CRS Consistency
- TEST C: Geotechnical Data Flow & Illustrative Disclosures
- TEST D: Complete Recommendation Flow (End-to-End Pipeline)
- TEST E: Missing-Data Policies (RENORMALIZE_AVAILABLE, ZERO_FILL, BLOCK_UNAVAILABLE)
- TEST F: Non-Discriminative Ranking Suppression vs Discriminative Differentiation
- TEST G: Export Consistency across CSV, GeoJSON, JSON, and HTML
- TEST H: Frontend Data Structures & Schema Contract Alignment
- SECURITY & CONTRACT: Path Traversal, HTML Escaping / XSS, Invalid Parameter Rejections
"""

import html
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Polygon, box, mapping

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.recommendations.spatial_reference import (
    WGS84Ellipsoid,
    calculate_polygon_geodesic_area,
)
from backend.app.core.recommendations.parcel_generation import (
    CandidateParcel,
    generate_candidate_parcels,
)
from backend.app.core.recommendations.zonal_statistics import (
    RasterLayerContext,
    extract_parcel_zonal_statistics,
)
from backend.app.core.recommendations.eligibility import (
    EligibilityConfig,
    EligibilityStatus,
    ExclusionReason,
    evaluate_parcel_eligibility,
)
from backend.app.core.recommendations.scoring import (
    MissingDataPolicy,
    NormalizationConfig,
    ScoringWeights,
    calculate_parcel_score,
)
from backend.app.core.recommendations.ranking import (
    EvaluatedParcel,
    RankingResult,
    rank_candidate_parcels,
)
from backend.app.core.recommendations.provenance import (
    RecommendationProvenance,
    build_recommendation_provenance,
)
from backend.app.core.recommendations.report_generation import (
    export_candidate_parcels_geojson,
    export_parcel_metrics_csv,
    export_parcel_rankings_csv,
    export_recommendation_summary_json,
    export_recommendation_report_html,
)
from backend.app.core.recommendations.explainability import (
    generate_parcel_explanation,
)
from backend.app.core.geotechnical.infinite_slope import calculate_infinite_slope_scalar
from backend.app.core.geotechnical.models import (
    SoilParameters,
    RootParameters,
    UnitTensileStress,
)
from backend.app.core.geotechnical.root_cohesion import (
    calculate_root_cohesion,
    calculate_reinforced_slope_scalar,
)
from backend.app.core.geospatial.terrain import (
    calculate_slope_and_aspect,
    compute_elevation_stats,
)
from backend.app.core.geospatial.ndvi import calculate_ndvi_array
from backend.app.schemas.geospatial import RasterMetadata

client = TestClient(app)


# ==============================================================================
# TEST A: APPLICATION HEALTH & CONTRACT
# ==============================================================================

class TestApplicationHealthAndContract:
    """Validate FastAPI initialization, health check, and error response contracts."""

    def test_health_endpoint_contract(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app_name"] == "TerraShield AI"
        assert data["version"] == "0.1.0"
        assert data["mode"] in ["demo", "production", "testing"]
        assert "timestamp" in data
        assert "message" in data

    def test_unhandled_route_returns_clean_404_without_path_disclosure(self):
        response = client.get("/api/v1/non_existent_endpoint")
        assert response.status_code == 404
        # Response should be standard JSON error, not leaking raw tracebacks
        data = response.json()
        assert "detail" in data
        assert "Traceback" not in str(data)

    def test_recommendations_status_disclosures(self):
        response = client.get("/api/v1/recommendations/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ready", "active"]
        assert "NASADEM" in data["dem_verified_source"]
        assert any(k in data["geotechnical_scenario_status"].lower() for k in ["benchmark", "exploratory", "illustrative"])
        assert "unverified" in data["protected_area_data_status"].lower()
        assert "pending" in data["species_database_status"].lower()


# ==============================================================================
# TEST B: GEOSPATIAL DATA FLOW & INTEGRATION
# ==============================================================================

class TestGeospatialDataFlow:
    """Validate raster ingestion, slope/aspect, NDVI, and spatial bounds consistency."""

    def test_terrain_derivation_from_synthetic_raster(self):
        # Create a synthetic 10x10 elevation ramp (0 to 100m)
        elev = np.linspace(0, 100, 100, dtype=np.float32).reshape(10, 10)
        meta = RasterMetadata(
            filename="synthetic_elev.tif",
            width=10,
            height=10,
            bands=1,
            bounds={"minx": 76.0, "miny": 11.5, "maxx": 76.1, "maxy": 11.6},
            crs="EPSG:4326",
            pixel_size_x=0.01,
            pixel_size_y=0.01,
            nodata_value=-9999.0,
            dtype="float32",
            valid_pixel_count=100,
            nodata_pixel_count=0,
            is_geographic=True,
        )
        _, valid_mask = compute_elevation_stats(elev, nodata_val=-9999.0)
        slope, aspect, slope_stats, aspect_stats = calculate_slope_and_aspect(elev, meta, valid_mask)

        assert slope.shape == (10, 10)
        assert aspect.shape == (10, 10)
        assert np.all(slope >= 0.0)
        assert np.all(slope <= 90.0)
        assert not np.isnan(slope).any()

    def test_ndvi_derivation_from_bands(self):
        red = np.full((10, 10), 1000, dtype=np.float32)
        nir = np.full((10, 10), 4000, dtype=np.float32)
        ndvi, stats = calculate_ndvi_array(red, nir)

        assert ndvi.shape == (10, 10)
        expected_val = (4000 - 1000) / (4000 + 1000)  # 3000 / 5000 = 0.6
        assert np.isclose(ndvi[5, 5], expected_val, atol=1e-3)
        assert np.all(ndvi >= -1.0) and np.all(ndvi <= 1.0)
        assert np.isclose(stats.mean_ndvi, 0.6, atol=1e-2)

    def test_real_wayanad_dem_checksum_and_dimensions(self):
        dem_path = settings.BASE_DIR / "data" / "raw" / "real" / "wayanad_dem.tif"
        if dem_path.exists():
            import hashlib
            with open(dem_path, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()
            # Verified checksum
            assert h == "680aa3cb46f4b7d148b2d62224ff8f8daa9591dcee5921d46c0f8c4c8a5ca2b6"


# ==============================================================================
# TEST C: GEOTECHNICAL DATA FLOW & PROVENANCE
# ==============================================================================

class TestGeotechnicalDataFlow:
    """Validate geotechnical limit-equilibrium formulas and illustrative provenance."""

    def test_infinite_slope_fs_and_reinforcement_pipeline(self):
        soil = SoilParameters(
            c_prime_kpa=8.0,
            phi_prime_deg=26.0,
            gamma_kn_m3=18.5,
            z_m=1.8,
            m_fraction=0.5,
        )
        res_base = calculate_infinite_slope_scalar(beta_deg=28.0, soil=soil)
        assert res_base.is_valid is True
        assert res_base.factor_of_safety is not None
        assert res_base.factor_of_safety > 0.0

        root = RootParameters(
            tensile_stress_input=25.0,
            tensile_stress_unit=UnitTensileStress.MPA,
            root_area_ratio=0.002,
            k_factor=1.2,
        )
        res_root = calculate_root_cohesion(root, base_soil_cohesion_kpa=soil.c_prime_kpa)
        assert res_root.delta_c_kpa > 0.0

        res_reinf = calculate_reinforced_slope_scalar(
            beta_deg=28.0,
            soil=soil,
            root=root,
            fs_target=1.3,
        )
        assert res_reinf.is_valid is True
        assert res_reinf.fs_reinforced is not None
        assert res_reinf.fs_reinforced > res_base.factor_of_safety
        assert res_reinf.delta_fs is not None
        assert res_reinf.delta_fs > 0.0

    def test_geotechnical_api_illustrative_flag(self):
        payload = {
            "beta_deg": 28.0,
            "soil": {
                "c_prime_kpa": 8.0,
                "phi_prime_deg": 26.0,
                "gamma_kn_m3": 18.5,
                "z_m": 1.8,
                "m_fraction": 0.5,
            },
            "root": {
                "tensile_stress_input": 25.0,
                "tensile_stress_unit": "MPa",
                "root_area_ratio": 0.002,
                "k_factor": 1.2,
            },
            "fs_target": 1.3,
        }
        response = client.post("/api/v1/geotechnical/analysis", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["baseline"]["factor_of_safety"] is not None
        assert data["reinforced"]["fs_reinforced"] is not None
        assert data["reinforced"]["delta_fs"] > 0.0
        warn_str = " ".join(data["warnings"]).lower()
        assert "wu-waldron" in warn_str


# ==============================================================================
# TEST D & G: COMPLETE RECOMMENDATION PIPELINE & EXPORT CONSISTENCY
# ==============================================================================

class TestCompleteRecommendationPipelineAndExports:
    """Validate full flow from parcel creation to multi-format report exports."""

    @pytest.fixture
    def synthetic_pipeline_setup(self, tmp_path):
        # Build 3 evaluated parcels: 2 eligible, 1 excluded
        p1 = EvaluatedParcel(
            parcel_id="E2E-P1",
            geometry={"type": "Polygon", "coordinates": [[[76.0, 11.55], [76.01, 11.55], [76.01, 11.56], [76.0, 11.56], [76.0, 11.55]]]},
            total_area_ha=10.0,
            plantable_area_ha=8.0,
            eligibility_status=EligibilityStatus.ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS,
            exclusion_reasons=[],
            protected_area_clearance_note="UNVERIFIED",
            metrics={
                "terrain_coverage_pct": 100.0,
                "slope_mean_deg": 28.0,
                "slope_max_deg": 34.0,
                "elevation_mean_m": 900.0,
                "fs_baseline_mean": 0.95,
                "fs_reinforced_mean": 1.45,
                "fs_delta_mean": 0.50,
                "required_cohesion_mean_kpa": 12.0,
                "tree_density_mean_stems_ha": 350.0,
                "ndvi_mean": 0.45,
                "ndvi_coverage_pct": 100.0,
                "fraction_steep_slope": 0.35,
                "fraction_unstable_fs": 0.60,
                "fraction_subtarget_fs": 0.85,
            },
        )
        p2 = EvaluatedParcel(
            parcel_id="E2E-P2",
            geometry={"type": "Polygon", "coordinates": [[[76.02, 11.55], [76.03, 11.55], [76.03, 11.56], [76.02, 11.56], [76.02, 11.55]]]},
            total_area_ha=8.0,
            plantable_area_ha=6.0,
            eligibility_status=EligibilityStatus.ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS,
            exclusion_reasons=[],
            protected_area_clearance_note="UNVERIFIED",
            metrics={
                "terrain_coverage_pct": 100.0,
                "slope_mean_deg": 22.0,
                "slope_max_deg": 27.0,
                "elevation_mean_m": 850.0,
                "fs_baseline_mean": 1.15,
                "fs_reinforced_mean": 1.40,
                "fs_delta_mean": 0.25,
                "required_cohesion_mean_kpa": 6.0,
                "tree_density_mean_stems_ha": 250.0,
                "ndvi_mean": 0.55,
                "ndvi_coverage_pct": 100.0,
                "fraction_steep_slope": 0.15,
                "fraction_unstable_fs": 0.10,
                "fraction_subtarget_fs": 0.40,
            },
        )
        p3 = EvaluatedParcel(
            parcel_id="E2E-P3",
            geometry={"type": "Polygon", "coordinates": [[[76.04, 11.55], [76.05, 11.55], [76.05, 11.56], [76.04, 11.56], [76.04, 11.55]]]},
            total_area_ha=5.0,
            plantable_area_ha=0.1,
            eligibility_status=EligibilityStatus.EXCLUDED,
            exclusion_reasons=[ExclusionReason.NEGLIGIBLE_PLANTABLE_AREA.value],
            protected_area_clearance_note="UNVERIFIED",
            metrics={"terrain_coverage_pct": 100.0, "slope_mean_deg": 12.0},
        )
        return [p1, p2, p3], tmp_path

    def test_ranking_and_export_consistency(self, synthetic_pipeline_setup):
        parcels, out_dir = synthetic_pipeline_setup
        run_id = "test_run_e2e"
        ts = "2026-10-11T12:00:00Z"

        res = rank_candidate_parcels(
            evaluated_parcels=parcels,
            run_id=run_id,
            timestamp=ts,
            scoring_weights=ScoringWeights(),
            normalization_config=NormalizationConfig(),
            missing_data_policy=MissingDataPolicy.RENORMALIZE_AVAILABLE,
        )

        assert res.total_parcels_evaluated == 3
        assert res.eligible_count == 2
        assert res.excluded_count == 1
        assert res.is_discriminative is True

        # Check rankings
        ranked = res.ranked_eligible_parcels
        assert ranked[0].parcel_id == "E2E-P1"
        assert ranked[0].rank == 1
        assert ranked[1].parcel_id == "E2E-P2"
        assert ranked[1].rank == 2

        # Build Provenance
        prov = build_recommendation_provenance(
            run_id=run_id,
            timestamp=ts,
            geotech_summary_path=None,
            has_official_protected_areas=False,
        )
        assert "UNVERIFIED" in prov.protected_area_verification_status

        # 1. GeoJSON Export
        geojson_f = export_candidate_parcels_geojson(res, out_dir / "parcels.geojson")
        assert geojson_f.exists()
        with open(geojson_f, "r", encoding="utf-8") as f:
            gj = json.load(f)
        assert gj["type"] == "FeatureCollection"
        assert len(gj["features"]) == 3
        # Excluded parcel should have rank None / null
        p3_feat = [f for f in gj["features"] if f["id"] == "E2E-P3"][0]
        assert p3_feat["properties"]["rank"] is None
        assert p3_feat["properties"]["eligibility_status"] == "EXCLUDED"

        # 2. CSV Metrics Export
        csv_m = export_parcel_metrics_csv(res, out_dir / "metrics.csv")
        assert csv_m.exists()
        with open(csv_m, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 4  # Header + 3 parcels
        assert "E2E-P1" in lines[1]
        assert "E2E-P3" in lines[3]

        # 3. CSV Rankings Export
        csv_r = export_parcel_rankings_csv(res, out_dir / "rankings.csv")
        assert csv_r.exists()
        with open(csv_r, "r", encoding="utf-8") as f:
            r_lines = f.readlines()
        assert len(r_lines) == 3  # Header + 2 eligible parcels only!
        assert "E2E-P3" not in "".join(r_lines)

        # 4. JSON Summary Export
        json_s = export_recommendation_summary_json(res, prov, out_dir / "summary.json")
        assert json_s.exists()
        with open(json_s, "r", encoding="utf-8") as f:
            sj = json.load(f)
        assert sj["run_id"] == run_id
        assert sj["parcel_inventory"]["eligible_count"] == 2
        assert sj["parcel_inventory"]["excluded_count"] == 1

        # 5. HTML Audit Report Export
        html_r = export_recommendation_report_html(res, prov, out_dir / "report.html")
        assert html_r.exists()
        with open(html_r, "r", encoding="utf-8") as f:
            content = f.read()
        assert "<!DOCTYPE html>" in content
        assert "TerraShield AI" in content
        assert "E2E-P1" in content
        assert "E2E-P2" in content
        assert prov.geotechnical_scenario_note in content


# ==============================================================================
# TEST E: MISSING-DATA POLICIES
# ==============================================================================

class TestMissingDataPolicies:
    """Validate behavior of RENORMALIZE_AVAILABLE, ZERO_FILL, and BLOCK_UNAVAILABLE."""

    @pytest.fixture
    def parcel_with_missing_ndvi(self):
        return EvaluatedParcel(
            parcel_id="P-MISSING-NDVI",
            geometry={"type": "Polygon", "coordinates": [[[76.0, 11.55], [76.01, 11.55], [76.01, 11.56], [76.0, 11.56], [76.0, 11.55]]]},
            total_area_ha=5.0,
            plantable_area_ha=5.0,
            eligibility_status=EligibilityStatus.ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS,
            exclusion_reasons=[],
            metrics={
                "terrain_coverage_pct": 100.0,
                "slope_mean_deg": 25.0,
                "elevation_mean_m": 800.0,
                "fs_baseline_mean": 1.0,
                "fs_delta_mean": 0.3,
                "ndvi_mean": None,  # Missing NDVI layer
                "ndvi_coverage_pct": 0.0,
            },
        )

    def test_renormalize_available_policy(self, parcel_with_missing_ndvi):
        weights = ScoringWeights(
            weight_geotechnical_need=0.35,
            weight_stability_gain=0.30,
            weight_plantable_area=0.20,
            weight_data_confidence=0.15,
        )
        norm_cfg = NormalizationConfig()
        breakdown = calculate_parcel_score(
            metrics=parcel_with_missing_ndvi.metrics,
            plantable_area_ha=5.0,
            weights=weights,
            normalization_config=norm_cfg,
            missing_data_policy=MissingDataPolicy.RENORMALIZE_AVAILABLE,
        )
        # Score is valid and positive
        assert breakdown.priority_score_index > 0.0
        # Data confidence explicitly reflects missing NDVI (coverage < 100%)
        assert breakdown.data_confidence_score < 1.0

    def test_zero_fill_policy(self, parcel_with_missing_ndvi):
        breakdown = calculate_parcel_score(
            metrics=parcel_with_missing_ndvi.metrics,
            plantable_area_ha=5.0,
            weights=ScoringWeights(),
            normalization_config=NormalizationConfig(),
            missing_data_policy=MissingDataPolicy.ZERO_FILL,
        )
        assert breakdown.priority_score_index >= 0.0

    def test_block_unavailable_policy(self):
        m_no_geotech = {
            "terrain_coverage_pct": 100.0,
            "slope_mean_deg": 25.0,
            "elevation_mean_m": 800.0,
            "fs_baseline_mean": None,
            "fs_delta_mean": None,
        }
        breakdown = calculate_parcel_score(
            metrics=m_no_geotech,
            plantable_area_ha=5.0,
            weights=ScoringWeights(),
            normalization_config=NormalizationConfig(),
            missing_data_policy=MissingDataPolicy.BLOCK_UNAVAILABLE,
        )
        assert breakdown.composite_score_normalized == 0.0
        assert breakdown.priority_score_index == 0.0
        assert "geotechnical_need" in breakdown.missing_components
        assert "stability_gain" in breakdown.missing_components

    def test_missing_terrain_disqualifies_parcel_at_eligibility(self):
        s_geom = box(76.0, 11.55, 76.01, 11.56)
        # Incomplete terrain coverage (e.g. 40% vs min 80%)
        metrics = {"terrain_coverage_pct": 40.0}
        cfg = EligibilityConfig(min_terrain_coverage_pct=80.0)
        status, reasons, _, _ = evaluate_parcel_eligibility(
            parcel_poly=s_geom,
            parcel_total_area_ha=5.0,
            metrics=metrics,
            config=cfg,
        )
        assert status == EligibilityStatus.INSUFFICIENT_DATA
        assert any("Insufficient terrain data coverage" in r for r in reasons)


# ==============================================================================
# TEST F: NON-DISCRIMINATIVE RANKING SUPPRESSION
# ==============================================================================

class TestNonDiscriminativeRankingSuppression:
    """Confirm ordinal ranking suppression when metrics are uniform."""

    def test_uniform_metrics_suppresses_ordinal_ranks(self, tmp_path):
        # 3 parcels with identical metrics
        p1 = EvaluatedParcel(
            parcel_id="TIE-01",
            geometry={"type": "Polygon", "coordinates": [[[76.0, 11.55], [76.01, 11.55], [76.01, 11.56], [76.0, 11.56], [76.0, 11.55]]]},
            total_area_ha=5.0,
            plantable_area_ha=4.0,
            eligibility_status=EligibilityStatus.ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS,
            exclusion_reasons=[],
            metrics={"slope_mean_deg": 20.0, "fs_baseline_mean": 1.2, "fs_delta_mean": 0.2, "terrain_coverage_pct": 100.0},
        )
        p2 = EvaluatedParcel(
            parcel_id="TIE-02",
            geometry={"type": "Polygon", "coordinates": [[[76.02, 11.55], [76.03, 11.55], [76.03, 11.56], [76.02, 11.56], [76.02, 11.55]]]},
            total_area_ha=5.0,
            plantable_area_ha=4.0,
            eligibility_status=EligibilityStatus.ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS,
            exclusion_reasons=[],
            metrics={"slope_mean_deg": 20.0, "fs_baseline_mean": 1.2, "fs_delta_mean": 0.2, "terrain_coverage_pct": 100.0},
        )
        res = rank_candidate_parcels(
            evaluated_parcels=[p1, p2],
            run_id="run_ties",
            timestamp="2026-10-11T12:00:00Z",
            scoring_weights=ScoringWeights(),
            normalization_config=NormalizationConfig(),
            missing_data_policy=MissingDataPolicy.RENORMALIZE_AVAILABLE,
        )
        assert res.is_discriminative is False
        assert "Suppressed" in res.differentiation_warning or "uniform" in res.differentiation_warning.lower()
        for p in res.ranked_eligible_parcels:
            assert p.rank is None  # Ordinal ranks are suppressed to None

        prov = build_recommendation_provenance("run_ties", "2026-10-11T12:00:00Z")
        html_f = export_recommendation_report_html(res, prov, tmp_path / "report_tie.html")
        with open(html_f, "r", encoding="utf-8") as f:
            html_text = f.read()
        assert "Non-Discriminative Ranking Notice" in html_text
        assert "Tied" in html_text


# ==============================================================================
# TEST H: FRONTEND INTEGRATION & HELPER CONTRACTS
# ==============================================================================

class TestFrontendIntegrationContracts:
    """Validate frontend data models and helper functions without headless browser."""

    def test_build_analysis_dataframe_contract(self):
        from frontend.components.metrics_view import build_analysis_dataframe
        raw_parcels = [
            {
                "parcel_id": "P-101",
                "area_hectares": 4.2,
                "demo_baseline_risk": 0.85,
                "demo_delta_risk": 0.45,
                "demo_tree_count": 800,
                "is_excluded": False,
                "demo_leverage_score": 0.00056,
                "rank": 1,
            },
            {
                "parcel_id": "P-102",
                "area_hectares": 3.1,
                "demo_baseline_risk": 0.90,
                "demo_delta_risk": 0.0,
                "demo_tree_count": 0,
                "is_excluded": True,
                "exclusion_reason": "Zero tree planting capacity",
                "demo_leverage_score": None,
                "rank": None,
            },
        ]
        df = build_analysis_dataframe(raw_parcels)
        assert len(df) == 2
        assert "Priority Rank" in df.columns
        assert df.iloc[0]["Priority Rank"] == "#1"
        assert df.iloc[1]["Priority Rank"] == "Excluded"

    def test_frontend_geotechnical_and_recommendation_imports(self):
        from frontend.components.recommendation_view import render_recommendation_tab
        from frontend.components.geotechnical_view import render_geotechnical_tab
        from frontend.components.terrain_view import render_dem_section, render_ndvi_section
        assert callable(render_recommendation_tab)
        assert callable(render_geotechnical_tab)
        assert callable(render_dem_section)
        assert callable(render_ndvi_section)


# ==============================================================================
# API CONTRACT & SECURITY REVIEWS
# ==============================================================================

class TestSecurityAndErrorHandling:
    """Validate path traversal protection, XSS escaping, and input validation."""

    def test_artifact_path_traversal_prevention(self):
        # Path traversal payload in artifact_id
        response = client.get("/api/v1/recommendations/artifacts/../../backend/app/main.py")
        # Should be rejected with 404 or 400, never returning main.py
        assert response.status_code in [400, 404]

    def test_invalid_scoring_weights_rejected_with_400(self):
        # Weights summing to 0
        payload = {
            "cell_size_m": 300.0,
            "scoring_weights": {
                "weight_geotechnical_need": 0.0,
                "weight_stability_gain": 0.0,
                "weight_plantable_area": 0.0,
                "weight_data_confidence": 0.0,
            },
        }
        response = client.post("/api/v1/recommendations/run", json=payload)
        assert response.status_code == 400
        assert "strictly positive" in response.json()["detail"].lower()

    def test_unsupported_missing_data_policy_rejected_with_400(self):
        payload = {
            "cell_size_m": 300.0,
            "missing_data_policy": "NON_EXISTENT_POLICY_NAME",
        }
        response = client.post("/api/v1/recommendations/run", json=payload)
        assert response.status_code == 400
        assert "unsupported missing_data_policy" in response.json()["detail"].lower()

    def test_html_report_xss_escaping(self, tmp_path):
        """Confirm that malicious script tags in parcel identifiers or warnings are escaped."""
        xss_parcel_id = '<script>alert("XSS")</script>'
        xss_warning = '<img src=x onerror="alert(1)">'

        p = EvaluatedParcel(
            parcel_id=xss_parcel_id,
            geometry={"type": "Polygon", "coordinates": [[[76.0, 11.55], [76.01, 11.55], [76.01, 11.56], [76.0, 11.56], [76.0, 11.55]]]},
            total_area_ha=5.0,
            plantable_area_ha=4.0,
            eligibility_status=EligibilityStatus.ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS,
            exclusion_reasons=[],
            metrics={"slope_mean_deg": 25.0, "fs_baseline_mean": 1.1, "fs_delta_mean": 0.3},
        )
        res = rank_candidate_parcels(
            evaluated_parcels=[p],
            run_id="run_xss",
            timestamp="2026-10-11T12:00:00Z",
            scoring_weights=ScoringWeights(),
            normalization_config=NormalizationConfig(),
            missing_data_policy=MissingDataPolicy.RENORMALIZE_AVAILABLE,
        )
        res.differentiation_warning = xss_warning
        res.is_discriminative = False

        prov = build_recommendation_provenance("run_xss", "2026-10-11T12:00:00Z")
        html_f = export_recommendation_report_html(res, prov, tmp_path / "xss_test.html")
        with open(html_f, "r", encoding="utf-8") as f:
            content = f.read()

        # Malicious tags must be strictly escaped
        assert '<script>alert("XSS")</script>' not in content
        assert '&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;' in content
        assert '<img src=x onerror="alert(1)">' not in content
        assert '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;' in content
