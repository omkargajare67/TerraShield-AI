"""Infinite slope stability formulation and Factor of Safety solver."""

import math
from typing import Optional, Tuple
import numpy as np

from backend.app.core.geotechnical.models import (
    InfiniteSlopeResult,
    SoilParameters,
    StressState,
)
from backend.app.core.geotechnical.parameter_validation import validate_soil_parameters


def calculate_infinite_slope_scalar(
    beta_deg: float,
    soil: SoilParameters,
) -> InfiniteSlopeResult:
    """Calculate baseline infinite slope Factor of Safety for a single slope angle.
    
    Formulation:
        FS_0 = [c' + (gamma * z * cos(beta)^2 - u) * tan(phi')] / [gamma * z * sin(beta) * cos(beta)]
    
    Args:
        beta_deg: Slope angle in degrees.
        soil: Validated soil parameters.
        
    Returns:
        Structured InfiniteSlopeResult with stress state and validity checks.
    """
    is_valid, val_messages = validate_soil_parameters(soil)
    if not is_valid:
        return InfiniteSlopeResult(
            beta_deg=beta_deg,
            beta_rad=math.radians(max(0.0, beta_deg)),
            factor_of_safety=None,
            stresses=None,
            is_valid=False,
            status="INVALID_SOIL_PARAMETERS",
            status_label="Invalid soil parameter input",
            warnings=val_messages,
        )

    if math.isnan(beta_deg) or beta_deg < 0.0 or beta_deg >= 90.0:
        return InfiniteSlopeResult(
            beta_deg=beta_deg,
            beta_rad=0.0,
            factor_of_safety=None,
            stresses=None,
            is_valid=False,
            status="INVALID_SLOPE_ANGLE",
            status_label="Slope angle must be in [0, 90) degrees",
            warnings=["Slope angle is negative, non-finite, or 90 degrees vertical."],
        )

    beta_rad = math.radians(beta_deg)
    phi_rad = math.radians(soil.phi_prime_deg)

    # Denominator components: driving shear stress tau = gamma * z * sin(beta) * cos(beta)
    cos_beta = math.cos(beta_rad)
    sin_beta = math.sin(beta_rad)
    tan_phi = math.tan(phi_rad)

    # Flat terrain edge case (driving stress approaches 0)
    if beta_deg < 0.1:
        return InfiniteSlopeResult(
            beta_deg=beta_deg,
            beta_rad=beta_rad,
            factor_of_safety=None,
            stresses=StressState(
                normal_stress_kpa=round(soil.gamma_kn_m3 * soil.z_m * (cos_beta**2), 4),
                effective_normal_stress_kpa=round(
                    soil.gamma_kn_m3 * soil.z_m * (cos_beta**2) - soil.u_kpa, 4
                ),
                shear_stress_kpa=0.0,
                available_shear_strength_kpa=round(
                    soil.c_prime_kpa
                    + max(0.0, soil.gamma_kn_m3 * soil.z_m * (cos_beta**2) - soil.u_kpa) * tan_phi,
                    4,
                ),
            ),
            is_valid=True,
            status="FLAT_TERRAIN",
            status_label="Undefined: Flat terrain has negligible gravitational driving shear stress",
            warnings=[
                "Slope angle is near zero (<0.1°). The infinite-slope denominator is singular; "
                "gravitational downslope translational sliding is not an active failure mechanism."
            ],
        )

    # Driving shear stress tau (kPa)
    tau = soil.gamma_kn_m3 * soil.z_m * sin_beta * cos_beta

    # Total normal stress sigma_n (kPa)
    sigma_n = soil.gamma_kn_m3 * soil.z_m * (cos_beta**2)

    # Effective normal stress sigma'_n (kPa)
    sigma_prime_n = sigma_n - soil.u_kpa

    # Check for non-positive effective normal stress (excess pore pressure / liquefaction)
    warnings = list(val_messages)
    status = "VALID"
    status_label = "Calculated under infinite slope assumptions"

    if sigma_prime_n <= 0.0:
        status = "NON_POSITIVE_EFFECTIVE_STRESS"
        status_label = "Excess pore pressure: Effective normal stress is non-positive"
        warnings.append(
            f"Effective normal stress is non-positive ({sigma_prime_n:.2f} kPa) due to high pore pressure "
            f"(u = {soil.u_kpa} kPa >= sigma_n = {sigma_n:.2f} kPa). Frictional resistance cannot mobilize."
        )
        # In cohesive soil with zero effective stress, only cohesion resists
        tau_f = max(0.0, soil.c_prime_kpa)
    else:
        tau_f = soil.c_prime_kpa + (sigma_prime_n * tan_phi)

    # Factor of Safety
    fs = tau_f / tau if tau > 1e-6 else None

    stress_state = StressState(
        normal_stress_kpa=round(sigma_n, 4),
        effective_normal_stress_kpa=round(sigma_prime_n, 4),
        shear_stress_kpa=round(tau, 4),
        available_shear_strength_kpa=round(tau_f, 4),
    )

    return InfiniteSlopeResult(
        beta_deg=beta_deg,
        beta_rad=beta_rad,
        factor_of_safety=round(fs, 4) if fs is not None else None,
        stresses=stress_state,
        is_valid=True,
        status=status,
        status_label=status_label,
        warnings=warnings,
    )


def calculate_infinite_slope_array(
    slope_deg_arr: np.ndarray,
    soil: SoilParameters,
    valid_mask: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Vectorized calculation of infinite slope Factor of Safety across a 2D slope raster.
    
    Returns:
        (fs_array, status_code_array)
        where status_code:
            0: VALID
            1: FLAT_TERRAIN (<0.1 deg)
            2: NON_POSITIVE_EFFECTIVE_STRESS
            -1: NODATA / INVALID
    """
    if valid_mask is None:
        valid_mask = ~np.isnan(slope_deg_arr) & (slope_deg_arr >= 0.0)

    fs_out = np.full_like(slope_deg_arr, -9999.0, dtype=np.float32)
    status_out = np.full_like(slope_deg_arr, -1, dtype=np.int16)

    # Extract valid coordinates
    flat_mask = valid_mask & (slope_deg_arr < 0.1)
    calc_mask = valid_mask & (slope_deg_arr >= 0.1) & (slope_deg_arr < 90.0)

    # Mark flat terrain as undefined status 1 (fs stays -9999.0)
    status_out[flat_mask] = 1

    if not np.any(calc_mask):
        return fs_out, status_out

    beta_rad = np.radians(slope_deg_arr[calc_mask])
    phi_rad = math.radians(soil.phi_prime_deg)
    tan_phi = math.tan(phi_rad)

    cos_b = np.cos(beta_rad)
    sin_b = np.sin(beta_rad)

    # Driving shear stress
    tau = soil.gamma_kn_m3 * soil.z_m * sin_b * cos_b

    # Normal stress
    sigma_n = soil.gamma_kn_m3 * soil.z_m * (cos_b**2)
    sigma_prime_n = sigma_n - soil.u_kpa

    # Identify non-positive effective stress
    excess_pore_mask = sigma_prime_n <= 0.0

    # Resisting shear strength
    tau_f = np.zeros_like(tau)
    tau_f[excess_pore_mask] = max(0.0, soil.c_prime_kpa)
    tau_f[~excess_pore_mask] = soil.c_prime_kpa + (sigma_prime_n[~excess_pore_mask] * tan_phi)

    # FS
    fs_calc = tau_f / np.maximum(tau, 1e-6)

    # Assign to outputs
    fs_out[calc_mask] = fs_calc.astype(np.float32)

    cell_status = np.zeros_like(tau, dtype=np.int16)
    cell_status[excess_pore_mask] = 2  # NON_POSITIVE_EFFECTIVE_STRESS
    status_out[calc_mask] = cell_status

    return fs_out, status_out
