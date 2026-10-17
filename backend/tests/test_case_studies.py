"""Automated unit and integration test suite for Real-World Landslide Case Study Library."""

import pytest
from fastapi.testclient import TestClient

from backend.app.core.case_studies.comparison import compare_observed_inventory_with_model
from backend.app.core.case_studies.models import CaseStudy
from backend.app.core.case_studies.registry import CaseStudyRegistry, CASE_STUDIES_REGISTRY
from backend.app.main import app

client = TestClient(app)


def test_registry_contains_all_initial_case_studies():
    """Verify that all initial required case studies are registered with valid configurations."""
    cases = CaseStudyRegistry.list_all()
    assert len(cases) >= 6

    ids = {c.id for c in cases}
    assert "wayanad_2024" in ids
    assert "malin_2014" in ids
    assert "himachal_2023" in ids
    assert "kedarnath_2013" in ids
    assert "nepal_gorkha_2026" in ids
    assert "cascade_demo" in ids


def test_case_studies_have_authoritative_sources_and_valid_bounds():
    """Every real-world case study must contain authoritative source citations and valid geographic bounds."""
    for case_id, case in CASE_STUDIES_REGISTRY.items():
        assert isinstance(case, CaseStudy)
        assert case.id == case_id
        assert len(case.name) > 5
        assert case.country in ["India", "Nepal", "United States"]

        # Bounds validation
        b = case.bounds
        assert b["minx"] < b["maxx"], f"Invalid longitude bounds in {case_id}"
        assert b["miny"] < b["maxy"], f"Invalid latitude bounds in {case_id}"
        assert -180 <= b["minx"] <= 180
        assert -90 <= b["miny"] <= 90

        # Disclosures & Sources
        if case.region_tag != "offline_demo":
            assert len(case.source_references) >= 1
            orgs = [s.organization for s in case.source_references]
            # Must reference authoritative geological or disaster institutions
            assert any(
                "ISRO" in o or "Geological Survey" in o or "WIHG" in o or "NDRRMA" in o or "IMD" in o
                for o in orgs
            ), f"Missing authoritative organization in {case_id}: {orgs}"
        else:
            assert case.verification_status == "OFFLINE_BENCHMARK"
            assert "synthetic" in case.short_description.lower() or "synthetic" in case.name.lower()


def test_nepal_case_study_discloses_provisional_status():
    """The recent Gorkha, Nepal case study must clearly indicate provisional status and not claim verified closure."""
    nepal = CaseStudyRegistry.get("nepal_gorkha_2026")
    assert nepal is not None
    assert nepal.verification_status == "PROVISIONAL_RECENT"
    assert nepal.readiness == "AWAITING_ADDITIONAL_DATA"
    assert any("provisional" in lim.lower() for lim in nepal.known_limitations)


def test_offline_demo_is_not_labeled_as_real_disaster():
    """Cascade Foothills must be explicitly disclosed as an offline synthetic benchmark."""
    demo = CaseStudyRegistry.get("cascade_demo")
    assert demo is not None
    assert demo.verification_status == "OFFLINE_BENCHMARK"
    assert demo.analysis_mode == "OFFLINE_TESTING"
    assert demo.region_tag == "offline_demo"
    assert "real historical" in demo.known_limitations[1].lower() or "synthetic" in demo.known_limitations[0].lower()


def test_api_list_case_studies():
    """Test GET /api/v1/case-studies with and without filtering."""
    res = client.get("/api/v1/case-studies")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 6

    # Test region filtering
    res_wg = client.get("/api/v1/case-studies?region=western_ghats")
    assert res_wg.status_code == 200
    wg_ids = {c["id"] for c in res_wg.json()}
    assert "wayanad_2024" in wg_ids
    assert "malin_2014" in wg_ids
    assert "kedarnath_2013" not in wg_ids

    # Test himalayas
    res_him = client.get("/api/v1/case-studies?region=himalayas")
    assert res_him.status_code == 200
    him_ids = {c["id"] for c in res_him.json()}
    assert "himachal_2023" in him_ids
    assert "kedarnath_2013" in him_ids


def test_api_get_single_case_study():
    """Test GET /api/v1/case-studies/{case_id}."""
    res = client.get("/api/v1/case-studies/wayanad_2024")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "wayanad_2024"
    assert len(data["source_references"]) >= 3
    assert data["bounds"]["minx"] == 76.08

    # Nonexistent
    res_404 = client.get("/api/v1/case-studies/nonexistent_case")
    assert res_404.status_code == 404


def test_api_get_observed_inventory():
    """Test GET /api/v1/case-studies/{case_id}/observed-inventory."""
    res = client.get("/api/v1/case-studies/wayanad_2024/observed-inventory")
    assert res.status_code == 200
    geo = res.json()
    assert geo["type"] == "FeatureCollection"
    assert len(geo["features"]) >= 3

    # Check feature types
    feature_types = {f["properties"]["feature_type"] for f in geo["features"]}
    assert "Initiation Scarp" in feature_types
    assert "Deposition Fan" in feature_types


def test_api_launch_workspace_isolation():
    """Test POST /api/v1/case-studies/{case_id}/launch-workspace creates or links without corrupting user projects."""
    res = client.get("/api/v1/projects")
    initial_project_count = len(res.json())

    # Launching Wayanad should connect to pre-existing verified workspace
    res_wy = client.post("/api/v1/case-studies/wayanad_2024/launch-workspace")
    assert res_wy.status_code == 200
    data_wy = res_wy.json()
    assert data_wy["is_existing"] is True
    assert data_wy["project_id"] == "wayanad_pilot"

    # Launching Malin should create an isolated workspace with correct bounds
    res_mln = client.post("/api/v1/case-studies/malin_2014/launch-workspace")
    assert res_mln.status_code == 200
    data_mln = res_mln.json()
    assert data_mln["case_id"] == "malin_2014"
    assert data_mln["project"]["bounds"]["minx"] == 73.65
    assert data_mln["project"]["geotechnical_parameters"]["name"] is not None


def test_spatial_comparison_logic():
    """Test spatial comparison between observed inventory and mock/real model parcels."""
    mock_obs = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [76.10, 11.50]},
                "properties": {"name": "Test Scarp", "feature_type": "Initiation Scarp"},
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [76.50, 11.90]},
                "properties": {"name": "Far Scarp", "feature_type": "Initiation Scarp"},
            },
        ],
    }
    mock_parcels = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "PARCEL-1",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[76.05, 11.45], [76.15, 11.45], [76.15, 11.55], [76.05, 11.55], [76.05, 11.45]]],
                },
                "properties": {"parcel_id": "PARCEL-1", "fs_baseline_mean": 0.85},
            }
        ],
    }

    comp = compare_observed_inventory_with_model(mock_obs, mock_parcels, concern_fs_threshold=1.3)
    assert comp["is_valid_comparison"] is True
    assert comp["total_observed_features"] == 2
    assert comp["features_intersecting_grid"] == 1
    assert comp["features_in_modeled_concern_zone"] == 1
    assert comp["grid_intersection_percentage"] == 50.0
    assert "SCIENTIFIC SAFEGUARD" in comp["scientific_integrity_notice"]


def test_case_study_deterministic_project_id():
    """Launching workspace for the same case study multiple times reuses the deterministic workspace without duplication."""
    res1 = client.post("/api/v1/case-studies/himachal_2023/launch-workspace")
    assert res1.status_code == 200
    data1 = res1.json()
    p_id_1 = data1["project_id"]
    assert p_id_1 == "proj_case_himachal_2023"

    # Second launch must find and reuse existing project
    res2 = client.post("/api/v1/case-studies/himachal_2023/launch-workspace")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["project_id"] == p_id_1
    assert data2["is_existing"] is True


def test_case_studies_do_not_use_other_project_datasets():
    """Real case studies must never reference another project's raster files or synthetic fixtures."""
    from backend.app.core.projects.project_service import ProjectService
    malin_proj = ProjectService.get_project("proj_case_malin_2014")
    if malin_proj:
        for layer_name, layer_info in malin_proj.layers.items():
            path_str = str(layer_info.get("path", "")).lower()
            assert "wayanad" not in path_str, f"Malin project referenced Wayanad raster in layer {layer_name}"
            assert "sample_dem" not in path_str, f"Malin project referenced Cascade sample_dem in layer {layer_name}"

    demo_proj = ProjectService.get_project("cascade_demo")
    assert demo_proj is not None
    assert demo_proj.geotechnical_parameters.get("is_demo_parameters") is True


def test_provenance_and_licensing_integrity():
    """Verify that every real-world case has documented data licensing and data-acquisition requirements."""
    for case_id, case in CASE_STUDIES_REGISTRY.items():
        assert len(case.data_acquisition_requirements) > 5, f"Missing acquisition requirements for {case_id}"
        assert len(case.licensing_and_attribution) > 5, f"Missing licensing details for {case_id}"
        assert len(case.known_limitations) >= 1, f"Missing limitations disclosure for {case_id}"


def test_api_compare_endpoint():
    """Test POST /api/v1/case-studies/{case_id}/compare endpoint with valid parcels GeoJSON."""
    test_parcels = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "PARCEL-WY-01",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[76.15, 11.53], [76.16, 11.53], [76.16, 11.55], [76.15, 11.55], [76.15, 11.53]]],
                },
                "properties": {
                    "parcel_id": "PARCEL-WY-01",
                    "fs_baseline_mean": 0.92,
                    "eligibility_status": "ELIGIBLE",
                },
            }
        ],
    }

    res = client.post(
        "/api/v1/case-studies/wayanad_2024/compare",
        json={"parcels_geojson": test_parcels, "concern_fs_threshold": 1.3},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid_comparison"] is True
    assert data["case_id"] == "wayanad_2024"
    assert data["total_observed_features"] >= 3
    assert "scientific_integrity_notice" in data
    assert "SCIENTIFIC SAFEGUARD" in data["scientific_integrity_notice"]

