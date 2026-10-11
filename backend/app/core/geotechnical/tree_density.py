"""Tree density estimation based on explicit empirical RAR calibration."""

from typing import Optional, Tuple
import numpy as np

from backend.app.core.geotechnical.models import (
    RootParameters,
    TreeDensityCalibration,
    TreeDensityResult,
)
from backend.app.core.geotechnical.parameter_validation import validate_tree_density_calibration

TREE_DENSITY_DISCLAIMER = (
    "Tree stem density estimates assume an idealized linear relationship between stand density "
    "and root area ratio (RAR) across the failure plane. In natural vegetation communities, root "
    "morphology, stand age, competitive crown thinning, taproot vs. lateral root architecture, "
    "and bedrock depth introduce high non-linearity. This estimate is an illustrative scenario "
    "tool, not a certified silvicultural or bioengineering prescription."
)


def estimate_tree_density(
    delta_c_required_kpa: float,
    root: RootParameters,
    calibration: Optional[TreeDensityCalibration] = None,
) -> TreeDensityResult:
    """Estimate required stems per hectare only when valid empirical calibration is supplied.

    Formulation:
        RAR_required = Delta_C_required / (K * Tr)
        stems_per_ha_required = reference_stems_per_ha * (RAR_required / RAR_at_reference_density)

    If calibration is None or invalid, returns required RAR with stems_per_ha marked as unavailable.
    """
    tr_kpa = root.tensile_stress_kpa
    k = root.k_factor

    if tr_kpa <= 0.0 or k <= 0.0:
        return TreeDensityResult(
            delta_c_required_kpa=delta_c_required_kpa,
            required_rar=0.0,
            stems_per_ha_required=None,
            is_calibrated=False,
            is_feasible=False,
            max_stems_per_ha=None,
            status="INVALID_ROOT_PARAMETERS",
            status_label="Cannot compute required RAR: non-positive root tensile strength or K factor",
            warnings=["Tensile stress Tr and reinforcement factor K must both be strictly positive."],
        )

    # Required RAR
    rar_req = delta_c_required_kpa / (k * tr_kpa)

    # Check if calibration is provided
    if calibration is None:
        return TreeDensityResult(
            delta_c_required_kpa=round(delta_c_required_kpa, 4),
            required_rar=round(rar_req, 6),
            stems_per_ha_required=None,
            is_calibrated=False,
            is_feasible=True,
            max_stems_per_ha=None,
            status="CALIBRATION_UNAVAILABLE",
            status_label="Tree density unavailable (no empirical RAR calibration provided)",
            warnings=[
                "Required Root Area Ratio (RAR) computed, but tree density (stems/ha) requires explicit field calibration parameters.",
                TREE_DENSITY_DISCLAIMER,
            ],
        )

    is_cal_valid, cal_msgs = validate_tree_density_calibration(calibration)
    if not is_cal_valid:
        return TreeDensityResult(
            delta_c_required_kpa=round(delta_c_required_kpa, 4),
            required_rar=round(rar_req, 6),
            stems_per_ha_required=None,
            is_calibrated=False,
            is_feasible=False,
            max_stems_per_ha=calibration.max_stems_per_ha,
            status="INVALID_CALIBRATION",
            status_label="Supplied tree density calibration parameters are invalid",
            warnings=cal_msgs + [TREE_DENSITY_DISCLAIMER],
        )

    # Compute linear density estimate
    stems_ha = calibration.reference_stems_per_ha * (rar_req / calibration.rar_at_reference_density)

    warnings = [TREE_DENSITY_DISCLAIMER]
    if calibration.provenance_note:
        warnings.append(f"Calibration reference: {calibration.provenance_note}")

    is_feasible = True
    if calibration.max_stems_per_ha is not None and stems_ha > calibration.max_stems_per_ha:
        is_feasible = False
        warnings.append(
            f"Required density ({stems_ha:.0f} stems/ha) exceeds biological carrying capacity / "
            f"maximum planting limit ({calibration.max_stems_per_ha:.0f} stems/ha)."
        )

    status_label = (
        "Tree density estimated from calibrated scenario"
        if is_feasible
        else "Target density exceeds maximum allowable planting capacity"
    )

    return TreeDensityResult(
        delta_c_required_kpa=round(delta_c_required_kpa, 4),
        required_rar=round(rar_req, 6),
        stems_per_ha_required=round(stems_ha, 1),
        is_calibrated=True,
        is_feasible=is_feasible,
        max_stems_per_ha=calibration.max_stems_per_ha,
        status="VALID" if is_feasible else "INFEASIBLE_DENSITY",
        status_label=status_label,
        warnings=warnings,
    )
