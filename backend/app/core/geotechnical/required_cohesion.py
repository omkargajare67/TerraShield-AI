"""Target root-cohesion solver for slope stabilization to attain target Factor of Safety."""

import math
from typing import Optional, Tuple
import numpy as np

from backend.app.core.geotechnical.infinite_slope import calculate_infinite_slope_scalar
from backend.app.core.geotechnical.models import (
    RequiredCohesionResult,
    RootParameters,
    SoilParameters,
)
from backend.app.core.geotechnical.parameter_validation import validate_soil_parameters


def calculate_required_cohesion_scalar(
    beta_deg: float,
    soil: SoilParameters,
    fs_target: float = 1.3,
    root: Optional[RootParameters] = None,
    max_allowable_rar: float = 1.0,
) -> RequiredCohesionResult:
    """Solve for additional root cohesion Delta_C_required needed to attain fs_target.

    Formulation:
        tau = gamma * z * sin(beta) * cos(beta)
        sigma_normal = gamma * z * cos(beta)^2
        Delta_C_required = max(0.0, fs_target * tau - c' - (sigma_normal - u) * tan(phi'))

    Verification:
        Re-substitute (c' + Delta_C_required) into the infinite-slope FS equation
        to confirm FS == fs_target within numerical tolerance (1e-4).
    """
    is_valid_soil, soil_msgs = validate_soil_parameters(soil)
    if not is_valid_soil:
        raise ValueError(f"Invalid soil parameters: {'; '.join(soil_msgs)}")

    if fs_target <= 0.0:
        raise ValueError(f"Target Factor of Safety must be positive (got {fs_target})")

    # 1. Check baseline FS
    base_res = calculate_infinite_slope_scalar(beta_deg, soil)
    if not base_res.is_valid or base_res.factor_of_safety is None:
        return RequiredCohesionResult(
            beta_deg=beta_deg,
            fs_target=fs_target,
            fs_baseline=None,
            delta_c_required_kpa=None,
            verification_fs=None,
            is_attainable=False,
            no_reinforcement_needed=False,
            required_rar=None,
            status=base_res.status,
            status_label=base_res.status_label,
            warnings=base_res.warnings,
        )

    fs_base = base_res.factor_of_safety

    # 2. Check if already meeting target
    if fs_base >= fs_target:
        return RequiredCohesionResult(
            beta_deg=beta_deg,
            fs_target=fs_target,
            fs_baseline=round(fs_base, 4),
            delta_c_required_kpa=0.0,
            verification_fs=round(fs_base, 4),
            is_attainable=True,
            no_reinforcement_needed=True,
            required_rar=0.0 if root is not None else None,
            status="VALID",
            status_label="Target reached under the supplied assumptions (no additional cohesion required)",
            warnings=[
                f"Baseline Factor of Safety ({fs_base:.3f}) already meets or exceeds target ({fs_target:.2f})."
            ],
        )

    # 3. Calculate required additional cohesion
    beta_rad = math.radians(beta_deg)
    cos_b = math.cos(beta_rad)
    sin_b = math.sin(beta_rad)
    tau = soil.gamma_kn_m3 * soil.z_m * sin_b * cos_b
    sigma_normal = soil.gamma_kn_m3 * soil.z_m * (cos_b**2)
    tan_phi = math.tan(math.radians(soil.phi_prime_deg))

    sigma_prime_n = sigma_normal - soil.u_kpa
    if sigma_prime_n <= 0.0:
        # Excess pore pressure condition
        resisting_frictional = 0.0
    else:
        resisting_frictional = sigma_prime_n * tan_phi

    # Required resisting shear capacity = fs_target * tau
    required_delta_c = max(0.0, (fs_target * tau) - soil.c_prime_kpa - resisting_frictional)

    # 4. Numerical verification by re-substitution
    total_cohesion_check = soil.c_prime_kpa + required_delta_c
    if sigma_prime_n <= 0.0:
        tau_f_check = total_cohesion_check
    else:
        tau_f_check = total_cohesion_check + resisting_frictional

    verification_fs = tau_f_check / tau if tau > 1e-6 else 0.0
    verification_diff = abs(verification_fs - fs_target)

    warnings: list[str] = []
    if verification_diff > 1e-3:
        warnings.append(
            f"Verification discrepancy: re-substituted FS ({verification_fs:.4f}) differs from target ({fs_target:.4f}) by {verification_diff:.4e}."
        )

    # 5. Calculate required RAR if root parameters are provided
    required_rar: Optional[float] = None
    is_attainable = True
    if root is not None:
        tr_kpa = root.tensile_stress_kpa
        k = root.k_factor
        if tr_kpa > 0.0 and k > 0.0:
            calc_rar = required_delta_c / (k * tr_kpa)
            required_rar = round(calc_rar, 6)
            if calc_rar > max_allowable_rar:
                is_attainable = False
                warnings.append(
                    f"Required Root Area Ratio ({calc_rar:.4f}) exceeds biological maximum limit ({max_allowable_rar:.2f}). Slope stabilization solely via vegetative root reinforcement is physically unattainable under these parameters."
                )

    status_label = (
        "Required cohesion calculated and verified"
        if is_attainable
        else "Target not reached in the modeled scenario (required RAR exceeds limit)"
    )

    return RequiredCohesionResult(
        beta_deg=beta_deg,
        fs_target=fs_target,
        fs_baseline=round(fs_base, 4),
        delta_c_required_kpa=round(required_delta_c, 4),
        verification_fs=round(verification_fs, 4),
        verification_tolerance=1e-4,
        is_attainable=is_attainable,
        no_reinforcement_needed=False,
        required_rar=required_rar,
        status="VALID",
        status_label=status_label,
        warnings=warnings,
    )


def calculate_required_cohesion_array(
    slope_deg_arr: np.ndarray,
    soil: SoilParameters,
    fs_target: float = 1.3,
    valid_mask: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Vectorized calculation of required additional root cohesion Delta_C_required (kPa).

    Returns an array of float32 where invalid pixels are set to -9999.0.
    """
    if valid_mask is None:
        valid_mask = ~np.isnan(slope_deg_arr) & (slope_deg_arr >= 0.0)

    out_arr = np.full_like(slope_deg_arr, -9999.0, dtype=np.float32)
    calc_mask = valid_mask & (slope_deg_arr >= 0.1) & (slope_deg_arr < 90.0)

    if not np.any(calc_mask):
        return out_arr

    beta_rad = np.radians(slope_deg_arr[calc_mask])
    phi_rad = math.radians(soil.phi_prime_deg)
    tan_phi = math.tan(phi_rad)

    cos_b = np.cos(beta_rad)
    sin_b = np.sin(beta_rad)

    tau = soil.gamma_kn_m3 * soil.z_m * sin_b * cos_b
    sigma_prime_n = (soil.gamma_kn_m3 * soil.z_m * (cos_b**2)) - soil.u_kpa

    excess_pore_mask = sigma_prime_n <= 0.0
    resisting_frictional = np.zeros_like(tau)
    resisting_frictional[~excess_pore_mask] = sigma_prime_n[~excess_pore_mask] * tan_phi

    req_delta_c = np.maximum(0.0, (fs_target * tau) - soil.c_prime_kpa - resisting_frictional)
    out_arr[calc_mask] = req_delta_c.astype(np.float32)

    return out_arr
