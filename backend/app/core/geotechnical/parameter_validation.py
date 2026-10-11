"""Validation and physical bounds checking for geotechnical input parameters."""

import math
from typing import List, Tuple
from backend.app.core.geotechnical.models import (
    SoilParameters,
    RootParameters,
    TreeDensityCalibration,
)


def validate_soil_parameters(soil: SoilParameters) -> Tuple[bool, List[str]]:
    """Validate soil parameter ranges and physical sanity."""
    messages = []
    is_valid = True

    if soil.c_prime_kpa < 0.0:
        messages.append("Effective cohesion c' cannot be negative.")
        is_valid = False

    if soil.gamma_kn_m3 <= 0.0:
        messages.append("Soil unit weight gamma must be strictly positive.")
        is_valid = False
    elif soil.gamma_kn_m3 < 5.0 or soil.gamma_kn_m3 > 30.0:
        messages.append(
            f"Soil unit weight gamma ({soil.gamma_kn_m3} kN/m³) is outside standard terrestrial soil ranges (5-30 kN/m³)."
        )

    if soil.z_m <= 0.0:
        messages.append("Failure depth z must be strictly positive.")
        is_valid = False
    elif soil.z_m > 20.0:
        messages.append(
            f"Failure depth z ({soil.z_m} m) exceeds typical shallow translational landslide depths (<20 m)."
        )

    if soil.phi_prime_deg < 0.0 or soil.phi_prime_deg >= 90.0:
        messages.append("Friction angle phi' must be within [0, 90) degrees.")
        is_valid = False
    elif soil.phi_prime_deg > 55.0:
        messages.append(
            f"Friction angle phi' ({soil.phi_prime_deg}°) is unusually high for natural soils (>55°)."
        )

    if soil.u_kpa < 0.0:
        messages.append("Pore-water pressure u cannot be negative in this formulation.")
        is_valid = False

    return is_valid, messages


def validate_root_parameters(root: RootParameters) -> Tuple[bool, List[str]]:
    """Validate root reinforcement parameters."""
    messages = []
    is_valid = True

    if root.tensile_stress_input <= 0.0:
        messages.append("Root tensile stress must be strictly positive.")
        is_valid = False

    if root.root_area_ratio < 0.0 or root.root_area_ratio > 1.0:
        messages.append("Root Area Ratio (RAR) must be between 0.0 and 1.0.")
        is_valid = False
    elif root.root_area_ratio > 0.10:
        messages.append(
            f"Root Area Ratio ({root.root_area_ratio:.4f}) is exceptionally high (>10% cross-sectional root area)."
        )

    if root.k_factor <= 0.0:
        messages.append("Reinforcement coefficient K must be strictly positive.")
        is_valid = False

    return is_valid, messages


def validate_tree_density_calibration(
    calibration: TreeDensityCalibration,
) -> Tuple[bool, List[str]]:
    """Validate tree density calibration parameters."""
    messages = []
    is_valid = True

    if calibration.reference_stems_per_ha <= 0.0:
        messages.append("Reference stem density must be strictly positive.")
        is_valid = False

    if calibration.rar_at_reference_density <= 0.0 or calibration.rar_at_reference_density > 1.0:
        messages.append("RAR at reference density must be in (0.0, 1.0].")
        is_valid = False

    if calibration.max_stems_per_ha is not None:
        if calibration.max_stems_per_ha <= 0.0:
            messages.append("Maximum stem density must be strictly positive.")
            is_valid = False
        elif calibration.max_stems_per_ha < calibration.reference_stems_per_ha:
            messages.append("Maximum stem density cannot be less than the reference density.")
            is_valid = False

    return is_valid, messages
