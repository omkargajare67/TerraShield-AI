"""Unit and integration tests for Phase 3 Geotechnical Intelligence Engine."""

import math
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import numpy as np

from backend.app.core.config import settings
from backend.app.core.geospatial.raster_loader import inspect_geotiff
from backend.app.core.geotechnical.infinite_slope import (
    calculate_infinite_slope_array,
    calculate_infinite_slope_scalar,
)
from backend.app.core.geotechnical.models import (
    RootParameters,
    SoilParameters,
    TreeDensityCalibration,
    UnitTensileStress,
)
from backend.app.core.geotechnical.parameter_validation import (
    validate_root_parameters,
    validate_soil_parameters,
    validate_tree_density_calibration,
)
from backend.app.core.geotechnical.provenance import ParameterProvenance, ProvenanceType
from backend.app.core.geotechnical.raster_analysis import process_geotechnical_raster
from backend.app.core.geotechnical.required_cohesion import (
    calculate_required_cohesion_array,
    calculate_required_cohesion_scalar,
)
from backend.app.core.geotechnical.root_cohesion import (
    calculate_reinforced_slope_array,
    calculate_reinforced_slope_scalar,
    calculate_root_cohesion,
)
from backend.app.core.geotechnical.sensitivity import run_parameter_sensitivity
from backend.app.core.geotechnical.tree_density import estimate_tree_density
from backend.app.main import app

client = TestClient(app)


# =========================================================================
# 1. INFINITE SLOPE SOLVER TESTS
# =========================================================================

def test_1_baseline_infinite_slope_manual_test_case():
    """Verify baseline infinite slope FS against manual analytical calculation."""
    # Assumptions: beta = 30 deg, gamma = 18 kN/m3, z = 2.0 m, c' = 10 kPa, phi' = 30 deg, u = 0 kPa
    soil = SoilParameters(
        c_prime_kpa=10.0,
        gamma_kn_m3=18.0,
        z_m=2.0,
        phi_prime_deg=30.0,
        u_kpa=0.0,
    )
    res = calculate_infinite_slope_scalar(beta_deg=30.0, soil=soil)

    assert res.is_valid is True
    assert res.status == "VALID"

    # Analytical: tau = 9 * sqrt(3) ~ 15.588457 kPa
    # sigma_n = 27.0 kPa, tau_f = 10 + 27 * tan(30) = 10 + 9 * sqrt(3) ~ 25.588457 kPa
    # FS = 25.588457 / 15.588457 ~ 1.6415
    expected_fs = 1.0 + (10.0 / (9.0 * math.sqrt(3.0)))
    assert math.isclose(res.factor_of_safety, expected_fs, rel_tol=1e-3)
    assert math.isclose(res.stresses.normal_stress_kpa, 27.0, rel_tol=1e-3)
    assert math.isclose(res.stresses.effective_normal_stress_kpa, 27.0, rel_tol=1e-3)


def test_2_dry_cohesionless_limiting_case():
    """Verify FS = tan(phi') / tan(beta) for c' = 0 and u = 0."""
    soil = SoilParameters(
        c_prime_kpa=0.0,
        gamma_kn_m3=19.0,
        z_m=1.2,
        phi_prime_deg=34.0,
        u_kpa=0.0,
    )
    for beta in [15.0, 25.0, 33.0, 42.0]:
        res = calculate_infinite_slope_scalar(beta_deg=beta, soil=soil)
        expected_fs = math.tan(math.radians(34.0)) / math.tan(math.radians(beta))
        assert math.isclose(res.factor_of_safety, expected_fs, rel_tol=1e-4)


def test_3_degree_to_radian_conversion():
    """Verify trigonometric calculations correctly convert degrees to radians."""
    soil = SoilParameters(
        c_prime_kpa=5.0,
        gamma_kn_m3=18.0,
        z_m=1.0,
        phi_prime_deg=45.0,  # tan(45 deg) = 1.0
        u_kpa=0.0,
    )
    res = calculate_infinite_slope_scalar(beta_deg=45.0, soil=soil)
    assert math.isclose(res.beta_rad, math.pi / 4.0, rel_tol=1e-5)
    # At 45 deg, sin(45)*cos(45) = 0.5, cos^2(45) = 0.5
    assert math.isclose(res.stresses.shear_stress_kpa, 18.0 * 1.0 * 0.5, rel_tol=1e-4)
    assert math.isclose(res.stresses.normal_stress_kpa, 18.0 * 1.0 * 0.5, rel_tol=1e-4)


def test_4_unit_consistency():
    """Verify unit consistency: gamma (kN/m3) * z (m) yields stress in kPa."""
    gamma = 17.5
    z = 2.4
    expected_vertical_total_stress = gamma * z  # 42.0 kPa
    soil = SoilParameters(
        c_prime_kpa=8.0,
        gamma_kn_m3=gamma,
        z_m=z,
        phi_prime_deg=25.0,
        u_kpa=5.0,
    )
    res = calculate_infinite_slope_scalar(beta_deg=20.0, soil=soil)
    cos_b = math.cos(math.radians(20.0))
    expected_normal_stress = expected_vertical_total_stress * (cos_b**2)
    assert math.isclose(res.stresses.normal_stress_kpa, expected_normal_stress, rel_tol=1e-4)
    assert math.isclose(
        res.stresses.effective_normal_stress_kpa,
        expected_normal_stress - 5.0,
        rel_tol=1e-4,
    )


# =========================================================================
# 2. ROOT COHESION AND REINFORCEMENT TESTS
# =========================================================================

def test_5_mpa_to_kpa_conversion():
    """Verify 1 MPa is correctly converted to 1000 kPa for root tensile stress."""
    root_mpa = RootParameters(
        tensile_stress_input=25.0,
        tensile_stress_unit=UnitTensileStress.MPA,
        root_area_ratio=0.002,
        k_factor=1.2,
    )
    assert root_mpa.tensile_stress_kpa == 25000.0

    res = calculate_root_cohesion(root_mpa)
    # Delta_C = 1.2 * 25000 * 0.002 = 60.0 kPa
    assert math.isclose(res.delta_c_kpa, 60.0, rel_tol=1e-4)
    assert any("Converted root tensile stress from 25.0 MPa to 25000.0 kPa" in w for w in res.warnings)


def test_6_root_cohesion_wu_waldron_calculation():
    """Verify Delta_C = K * Tr * RAR under Wu-Waldron formulation."""
    root = RootParameters(
        tensile_stress_input=12000.0,
        tensile_stress_unit=UnitTensileStress.KPA,
        root_area_ratio=0.0015,
        k_factor=1.2,
        species_label="Vetiver Grass Profile",
    )
    res = calculate_root_cohesion(root, base_soil_cohesion_kpa=4.0)
    expected_delta_c = 1.2 * 12000.0 * 0.0015  # 21.6 kPa
    assert math.isclose(res.delta_c_kpa, expected_delta_c, rel_tol=1e-4)
    assert math.isclose(res.total_cohesion_kpa, 4.0 + expected_delta_c, rel_tol=1e-4)
    assert res.species_label == "Vetiver Grass Profile"


def test_7_root_reinforcement_increases_factor_of_safety():
    """Verify root reinforcement strictly increases modeled Factor of Safety."""
    soil = SoilParameters(
        c_prime_kpa=2.0,
        gamma_kn_m3=18.0,
        z_m=1.5,
        phi_prime_deg=26.0,
        u_kpa=0.0,
    )
    root = RootParameters(
        tensile_stress_input=15000.0,
        tensile_stress_unit=UnitTensileStress.KPA,
        root_area_ratio=0.001,
        k_factor=1.2,
    )
    res = calculate_reinforced_slope_scalar(beta_deg=35.0, soil=soil, root=root)
    assert res.is_valid is True
    assert res.fs_reinforced > res.fs_baseline
    assert res.delta_fs > 0.0
    assert math.isclose(res.delta_fs, res.fs_reinforced - res.fs_baseline, rel_tol=1e-4)


def test_8_zero_root_area_ratio_yields_zero_additional_cohesion():
    """Verify zero RAR produces Delta_C = 0 and identical baseline FS."""
    root_zero = RootParameters(
        tensile_stress_input=20000.0,
        tensile_stress_unit=UnitTensileStress.KPA,
        root_area_ratio=0.0,
        k_factor=1.2,
    )
    res_cohesion = calculate_root_cohesion(root_zero)
    assert res_cohesion.delta_c_kpa == 0.0

    soil = SoilParameters(
        c_prime_kpa=6.0,
        gamma_kn_m3=18.0,
        z_m=1.0,
        phi_prime_deg=30.0,
        u_kpa=0.0,
    )
    res_slope = calculate_reinforced_slope_scalar(beta_deg=30.0, soil=soil, root=root_zero)
    assert math.isclose(res_slope.fs_reinforced, res_slope.fs_baseline, rel_tol=1e-4)
    assert res_slope.delta_fs == 0.0


# =========================================================================
# 3. TARGET COHESION SOLVER AND TREE DENSITY TESTS
# =========================================================================

def test_9_required_root_cohesion_is_never_negative():
    """Verify required additional cohesion is >= 0 (returns 0 when baseline >= target)."""
    # Strong soil already exceeding target FS = 1.3
    soil = SoilParameters(
        c_prime_kpa=25.0,
        gamma_kn_m3=18.0,
        z_m=1.0,
        phi_prime_deg=35.0,
        u_kpa=0.0,
    )
    res = calculate_required_cohesion_scalar(beta_deg=20.0, soil=soil, fs_target=1.3)
    assert res.delta_c_required_kpa == 0.0
    assert res.no_reinforcement_needed is True
    assert res.fs_baseline >= 1.3


def test_10_target_solver_substitution_verification():
    """Verify re-substituting calculated required cohesion reaches target FS within tolerance."""
    soil = SoilParameters(
        c_prime_kpa=3.0,
        gamma_kn_m3=18.5,
        z_m=1.8,
        phi_prime_deg=25.0,
        u_kpa=2.0,
    )
    root = RootParameters(
        tensile_stress_input=20.0,
        tensile_stress_unit=UnitTensileStress.MPA,
        root_area_ratio=0.001,
        k_factor=1.2,
    )
    target = 1.35
    res = calculate_required_cohesion_scalar(beta_deg=32.0, soil=soil, fs_target=target, root=root)

    assert res.delta_c_required_kpa > 0.0
    assert math.isclose(res.verification_fs, target, abs_tol=1e-4)


def test_11_invalid_friction_angles_rejected():
    """Verify friction angles >= 90 deg or < 0 deg are rejected by validation."""
    with pytest.raises(Exception):
        SoilParameters(
            c_prime_kpa=5.0,
            gamma_kn_m3=18.0,
            z_m=1.0,
            phi_prime_deg=92.0,
        )

    with pytest.raises(Exception):
        SoilParameters(
            c_prime_kpa=5.0,
            gamma_kn_m3=18.0,
            z_m=1.0,
            phi_prime_deg=-5.0,
        )


def test_12_negative_or_non_finite_soil_parameters_handled():
    """Verify negative unit weight and failure depth are blocked."""
    with pytest.raises(Exception):
        SoilParameters(
            c_prime_kpa=5.0,
            gamma_kn_m3=-18.0,
            z_m=1.0,
            phi_prime_deg=30.0,
        )

    with pytest.raises(Exception):
        SoilParameters(
            c_prime_kpa=5.0,
            gamma_kn_m3=18.0,
            z_m=-1.0,
            phi_prime_deg=30.0,
        )


def test_13_zero_or_near_zero_denominators_handled_safely():
    """Verify flat slopes (beta < 0.1 deg) return undefined status, not infinity."""
    soil = SoilParameters(
        c_prime_kpa=5.0,
        gamma_kn_m3=18.0,
        z_m=1.0,
        phi_prime_deg=30.0,
    )
    res_zero = calculate_infinite_slope_scalar(beta_deg=0.0, soil=soil)
    assert res_zero.factor_of_safety is None
    assert res_zero.status == "FLAT_TERRAIN"

    res_flat = calculate_infinite_slope_scalar(beta_deg=0.05, soil=soil)
    assert res_flat.factor_of_safety is None
    assert res_flat.status == "FLAT_TERRAIN"


def test_14_non_positive_effective_normal_stress_handling():
    """Verify excess pore pressure causing sigma'_n <= 0 returns explicit warning."""
    # Pore pressure (40 kPa) exceeds normal stress
    soil = SoilParameters(
        c_prime_kpa=5.0,
        gamma_kn_m3=18.0,
        z_m=1.0,
        phi_prime_deg=30.0,
        u_kpa=40.0,
    )
    res = calculate_infinite_slope_scalar(beta_deg=30.0, soil=soil)
    assert res.status == "NON_POSITIVE_EFFECTIVE_STRESS"
    assert any("Effective normal stress is non-positive" in w for w in res.warnings)


def test_15_missing_soil_parameters_blocks_analysis():
    """Verify API rejects requests missing required soil parameters."""
    bad_payload = {
        "beta_deg": 30.0,
        "soil": {
            "gamma_kn_m3": 18.0,
            # missing c_prime_kpa, z_m, phi_prime_deg
        },
    }
    resp = client.post("/api/v1/geotechnical/analysis", json=bad_payload)
    assert resp.status_code == 422


def test_16_missing_root_parameters_prevents_reinforcement():
    """Verify analysis without root parameters returns baseline only."""
    payload = {
        "beta_deg": 30.0,
        "soil": {
            "c_prime_kpa": 5.0,
            "gamma_kn_m3": 18.0,
            "z_m": 1.5,
            "phi_prime_deg": 28.0,
            "u_kpa": 0.0,
        },
    }
    resp = client.post("/api/v1/geotechnical/analysis", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["baseline"]["factor_of_safety"] is not None
    assert data["root_reinforcement"] is None
    assert data["reinforced"] is None


def test_17_missing_planting_density_calibration_prevents_stems_estimate():
    """Verify tree density calculation is marked unavailable if calibration is omitted."""
    root = RootParameters(
        tensile_stress_input=15.0,
        tensile_stress_unit=UnitTensileStress.MPA,
        root_area_ratio=0.001,
        k_factor=1.2,
    )
    res = estimate_tree_density(delta_c_required_kpa=10.0, root=root, calibration=None)
    assert res.is_calibrated is False
    assert res.stems_per_ha_required is None
    assert res.status == "CALIBRATION_UNAVAILABLE"


# =========================================================================
# 4. RASTER ANALYSIS AND GEOSPATIAL PRESERVATION TESTS
# =========================================================================

def test_18_and_19_raster_analysis_metadata_and_nodata_preservation():
    """Verify geotechnical output rasters preserve spatial metadata and NoData mask."""
    real_slope_path = Path("data/processed/real/wayanad_slope.tif")
    if not real_slope_path.exists():
        pytest.skip("Real Wayanad slope raster not present in test environment")

    soil = SoilParameters(
        c_prime_kpa=5.0,
        gamma_kn_m3=18.0,
        z_m=1.5,
        phi_prime_deg=28.0,
        u_kpa=0.0,
    )
    root = RootParameters(
        tensile_stress_input=15.0,
        tensile_stress_unit=UnitTensileStress.MPA,
        root_area_ratio=0.001,
        k_factor=1.2,
    )
    cal = TreeDensityCalibration(
        reference_stems_per_ha=1200.0,
        rar_at_reference_density=0.002,
        provenance_note="Test calibration benchmark",
    )

    summary = process_geotechnical_raster(
        slope_path=real_slope_path,
        soil=soil,
        root=root,
        fs_target=1.3,
        calibration=cal,
    )

    # 18. Check NoData preservation and slope statistics audit
    assert summary["valid_pixels"] == 129600
    assert summary["crs"] == "EPSG:4326 (WGS 84)"
    assert summary["scenario_assumptions"]["is_illustrative_scenario"] is True
    assert summary["scenario_assumptions"]["scenario_type"] == "ILLUSTRATIVE_EXPLORATORY_BENCHMARK"

    # Verify measured terrain slope statistics
    slope_stats = summary["statistics"]["slope_degrees"]
    assert slope_stats["min"] == 0.0
    assert slope_stats["max"] == 58.07
    assert slope_stats["mean"] == 9.49
    assert slope_stats["median"] == 8.6
    assert slope_stats["flat_pixels_below_0_1_deg"] == 721

    # 19. Check metadata on generated GeoTIFF
    out_fs_path = settings.PROCESSED_DIR / "geotechnical" / "wayanad_fs_baseline.tif"
    assert out_fs_path.exists()
    arr, meta = inspect_geotiff(out_fs_path)
    assert meta.width == 360
    assert meta.height == 360
    assert meta.crs == "EPSG:4326 (WGS 84)"
    assert meta.is_geographic is True
    assert math.isclose(meta.bounds["minx"], 76.0, abs_tol=1e-5)
    assert math.isclose(meta.bounds["maxx"], 76.1, abs_tol=1e-5)
    assert math.isclose(meta.bounds["miny"], 11.55, abs_tol=1e-5)
    assert math.isclose(meta.bounds["maxy"], 11.65, abs_tol=1e-5)
    assert meta.nodata_value == -9999.0


def test_24_crs_alignment_between_real_dem_slope_and_geotech_outputs():
    """Verify exact coordinate alignment and CRS match across DEM, Slope, and Geotech outputs."""
    dem_path = Path("data/raw/real/wayanad_dem.tif")
    slope_path = Path("data/processed/real/wayanad_slope.tif")
    geotech_path = Path("data/processed/geotechnical/wayanad_fs_baseline.tif")

    if not (dem_path.exists() and slope_path.exists() and geotech_path.exists()):
        pytest.skip("Wayanad raster products not found on disk")

    _, dem_meta = inspect_geotiff(dem_path)
    _, slope_meta = inspect_geotiff(slope_path)
    _, geo_meta = inspect_geotiff(geotech_path)

    # All must share EPSG:4326 WGS 84
    assert dem_meta.crs == "EPSG:4326 (WGS 84)"
    assert slope_meta.crs == "EPSG:4326 (WGS 84)"
    assert geo_meta.crs == "EPSG:4326 (WGS 84)"

    # All must share identical pixel scale and bounds
    assert math.isclose(dem_meta.pixel_size_x, slope_meta.pixel_size_x, rel_tol=1e-6)
    assert math.isclose(slope_meta.pixel_size_x, geo_meta.pixel_size_x, rel_tol=1e-6)
    assert math.isclose(dem_meta.bounds["minx"], geo_meta.bounds["minx"], abs_tol=1e-6)
    assert math.isclose(dem_meta.bounds["maxy"], geo_meta.bounds["maxy"], abs_tol=1e-6)


def test_20_secure_artifact_retrieval_prevents_traversal():
    """Verify artifact endpoint blocks directory traversal attempts."""
    resp = client.get("/api/v1/geospatial/artifacts/../../etc/passwd")
    assert resp.status_code in [404, 400]

    resp = client.get("/api/v1/geospatial/artifacts/nonexistent_file_12345.tif")
    assert resp.status_code == 404


def test_21_api_validation_and_error_handling():
    """Verify parameter validation endpoint works correctly."""
    valid_payload = {
        "soil": {
            "c_prime_kpa": 6.0,
            "gamma_kn_m3": 18.0,
            "z_m": 1.5,
            "phi_prime_deg": 28.0,
            "u_kpa": 0.0,
        },
        "root": {
            "tensile_stress_input": 15.0,
            "tensile_stress_unit": "MPa",
            "root_area_ratio": 0.002,
            "k_factor": 1.2,
        },
    }
    resp = client.post("/api/v1/geotechnical/parameters/validate", json=valid_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["soil_valid"] is True
    assert data["root_valid"] is True


def test_22_phase1_demonstration_endpoints_still_work():
    """Verify Phase 1 demonstration endpoints remain fully functional."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

    resp = client.get("/api/v1/parcels")
    assert resp.status_code == 200
    parcels_data = resp.json()
    assert parcels_data["type"] == "FeatureCollection"
    assert len(parcels_data["features"]) == 5

    analysis_req = {
        "scenario": "landslide_mitigation",
        "min_risk_threshold": 0.0,
    }
    resp = client.post("/api/v1/analysis", json=analysis_req)
    assert resp.status_code == 200
    assert "parcels" in resp.json()


def test_23_phase2_terrain_and_ndvi_endpoints_still_work():
    """Verify Phase 2 geospatial terrain, NDVI, and status endpoints remain functional."""
    resp = client.get("/api/v1/geospatial/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"

    # Soil metadata validation
    soil_meta = {
        "source": "ISRIC SoilGrids 250m",
        "property_name": "clay",
        "depth_interval": "0-30cm",
        "units": "g/kg",
    }
    resp = client.post("/api/v1/geospatial/soil/validate", json=soil_meta)
    assert resp.status_code == 200
    assert resp.json()["is_valid"] is True
