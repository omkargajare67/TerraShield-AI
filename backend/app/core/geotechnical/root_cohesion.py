"""Wu-Waldron vegetative root cohesion and reinforced slope stability solver."""

import math
from typing import Optional, Tuple
import numpy as np

from backend.app.core.geotechnical.infinite_slope import calculate_infinite_slope_scalar
from backend.app.core.geotechnical.models import (
    ReinforcedSlopeResult,
    RootCohesionResult,
    RootParameters,
    SoilParameters,
    StressState,
)
from backend.app.core.geotechnical.parameter_validation import (
    validate_root_parameters,
    validate_soil_parameters,
)

WU_WALDRON_DISCLAIMER = (
    "The Wu-Waldron model (Wu et al. 1979; Waldron 1977) assumes full simultaneous root tensile "
    "mobilization and perpendicular shear orientation across the failure plane. In natural hillslopes, "
    "progressive root pullout, branching angles, biological decay, and soil moisture variations "
    "cause real mobilized reinforcement to differ from this simplified upper-bound estimate."
)


def calculate_root_cohesion(
    root: RootParameters,
    base_soil_cohesion_kpa: float = 0.0,
) -> RootCohesionResult:
    """Calculate additional root cohesion Delta_C = K * Tr * RAR under Wu-Waldron formulation.
    
    Args:
        root: Validated root reinforcement parameters.
        base_soil_cohesion_kpa: Existing soil cohesion c' in kPa.
        
    Returns:
        RootCohesionResult with Delta_C and total cohesion.
    """
    is_valid, messages = validate_root_parameters(root)
    if not is_valid:
        raise ValueError(f"Invalid root parameters: {'; '.join(messages)}")

    tr_kpa = root.tensile_stress_kpa
    rar = root.root_area_ratio
    k = root.k_factor

    # Delta_C in kPa
    delta_c = k * tr_kpa * rar
    total_c = base_soil_cohesion_kpa + delta_c

    warnings = [WU_WALDRON_DISCLAIMER]
    if root.tensile_stress_unit.value == "MPa":
        warnings.append(
            f"Converted root tensile stress from {root.tensile_stress_input} MPa to {tr_kpa} kPa."
        )

    return RootCohesionResult(
        delta_c_kpa=round(delta_c, 4),
        tr_kpa=round(tr_kpa, 2),
        rar=round(rar, 6),
        k_factor=round(k, 3),
        total_cohesion_kpa=round(total_c, 4),
        species_label=root.species_label,
        warnings=warnings,
    )


def calculate_reinforced_slope_scalar(
    beta_deg: float,
    soil: SoilParameters,
    root: RootParameters,
    fs_target: float = 1.3,
) -> ReinforcedSlopeResult:
    """Calculate root-reinforced infinite slope Factor of Safety and target attainment.
    
    Formulation:
        FS_root = [c' + Delta_C + (gamma * z * cos(beta)^2 - u) * tan(phi')] / [gamma * z * sin(beta) * cos(beta)]
    """
    # 1. Baseline evaluation
    base_res = calculate_infinite_slope_scalar(beta_deg, soil)
    if not base_res.is_valid or base_res.factor_of_safety is None:
        return ReinforcedSlopeResult(
            beta_deg=beta_deg,
            fs_baseline=None,
            delta_c_kpa=0.0,
            fs_reinforced=None,
            delta_fs=None,
            fs_target=fs_target,
            target_reached=False,
            is_valid=base_res.is_valid,
            status=base_res.status,
            status_label=base_res.status_label,
            stresses=base_res.stresses,
            warnings=base_res.warnings,
        )

    # 2. Compute root cohesion
    root_res = calculate_root_cohesion(root, base_soil_cohesion_kpa=soil.c_prime_kpa)
    delta_c = root_res.delta_c_kpa

    # 3. Compute reinforced Factor of Safety using identical geometry
    beta_rad = math.radians(beta_deg)
    cos_b = math.cos(beta_rad)
    sin_b = math.sin(beta_rad)
    tau = soil.gamma_kn_m3 * soil.z_m * sin_b * cos_b
    sigma_prime_n = (soil.gamma_kn_m3 * soil.z_m * (cos_b**2)) - soil.u_kpa
    tan_phi = math.tan(math.radians(soil.phi_prime_deg))

    # Available shear resistance with root reinforcement
    if sigma_prime_n <= 0.0:
        tau_f_root = max(0.0, soil.c_prime_kpa + delta_c)
    else:
        tau_f_root = soil.c_prime_kpa + delta_c + (sigma_prime_n * tan_phi)

    fs_root = tau_f_root / tau if tau > 1e-6 else None
    delta_fs = (fs_root - base_res.factor_of_safety) if fs_root is not None else None

    target_reached = (fs_root >= fs_target) if fs_root is not None else False

    status_label = (
        "Target reached under the supplied assumptions"
        if target_reached
        else "Target not reached in the modeled scenario"
    )

    warnings = list(base_res.warnings) + root_res.warnings
    if not target_reached and fs_root is not None:
        warnings.append(
            f"Modeled root reinforcement ({delta_c:.2f} kPa) increased FS from {base_res.factor_of_safety:.3f} "
            f"to {fs_root:.3f}, but remains below project benchmark target of {fs_target:.2f}."
        )

    stresses_root = StressState(
        normal_stress_kpa=base_res.stresses.normal_stress_kpa,
        effective_normal_stress_kpa=base_res.stresses.effective_normal_stress_kpa,
        shear_stress_kpa=base_res.stresses.shear_stress_kpa,
        available_shear_strength_kpa=round(tau_f_root, 4),
    )

    return ReinforcedSlopeResult(
        beta_deg=beta_deg,
        fs_baseline=base_res.factor_of_safety,
        delta_c_kpa=round(delta_c, 4),
        fs_reinforced=round(fs_root, 4) if fs_root is not None else None,
        delta_fs=round(delta_fs, 4) if delta_fs is not None else None,
        fs_target=fs_target,
        target_reached=target_reached,
        is_valid=True,
        status="VALID",
        status_label=status_label,
        stresses=stresses_root,
        warnings=warnings,
    )


def calculate_reinforced_slope_array(
    slope_deg_arr: np.ndarray,
    soil: SoilParameters,
    delta_c_kpa: float,
    valid_mask: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Vectorized calculation of root-reinforced Factor of Safety across a slope raster."""
    if valid_mask is None:
        valid_mask = ~np.isnan(slope_deg_arr) & (slope_deg_arr >= 0.0)

    fs_out = np.full_like(slope_deg_arr, -9999.0, dtype=np.float32)
    calc_mask = valid_mask & (slope_deg_arr >= 0.1) & (slope_deg_arr < 90.0)

    if not np.any(calc_mask):
        return fs_out

    beta_rad = np.radians(slope_deg_arr[calc_mask])
    phi_rad = math.radians(soil.phi_prime_deg)
    tan_phi = math.tan(phi_rad)

    cos_b = np.cos(beta_rad)
    sin_b = np.sin(beta_rad)

    tau = soil.gamma_kn_m3 * soil.z_m * sin_b * cos_b
    sigma_prime_n = (soil.gamma_kn_m3 * soil.z_m * (cos_b**2)) - soil.u_kpa

    excess_pore_mask = sigma_prime_n <= 0.0
    tau_f_root = np.zeros_like(tau)
    tau_f_root[excess_pore_mask] = max(0.0, soil.c_prime_kpa + delta_c_kpa)
    tau_f_root[~excess_pore_mask] = (
        soil.c_prime_kpa + delta_c_kpa + (sigma_prime_n[~excess_pore_mask] * tan_phi)
    )

    fs_calc = tau_f_root / np.maximum(tau, 1e-6)
    fs_out[calc_mask] = fs_calc.astype(np.float32)

    return fs_out
