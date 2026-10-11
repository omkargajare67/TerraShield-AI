"""Deterministic sensitivity analysis for geotechnical infinite slope stability."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.core.geotechnical.infinite_slope import calculate_infinite_slope_scalar
from backend.app.core.geotechnical.models import (
    ReinforcedSlopeResult,
    RootParameters,
    SoilParameters,
)
from backend.app.core.geotechnical.root_cohesion import calculate_reinforced_slope_scalar


class SensitivityPoint(BaseModel):
    """A single evaluation point in a parameter sensitivity sweep."""
    parameter_name: str
    parameter_value: float
    parameter_unit: str
    fs_baseline: Optional[float] = None
    delta_c_kpa: float = 0.0
    fs_reinforced: Optional[float] = None
    delta_fs: Optional[float] = None
    target_reached: bool = False
    status: str = "VALID"
    note: Optional[str] = None


class ParameterSensitivitySeries(BaseModel):
    """Sensitivity results for varying a single parameter while holding others constant."""
    parameter_name: str
    parameter_label: str
    unit: str
    baseline_value: float
    points: List[SensitivityPoint]
    fs_range_reinforced: List[float] = Field(default_factory=list)


class SensitivityAnalysisResult(BaseModel):
    """Complete multi-parameter sensitivity analysis output."""
    beta_deg: float
    fs_target: float
    baseline_fs_unreinforced: Optional[float] = None
    baseline_fs_reinforced: Optional[float] = None
    series: Dict[str, ParameterSensitivitySeries]
    methodology_note: str = (
        "Deterministic local sensitivity analysis evaluating one-at-a-time (OAT) parameter "
        "variations. This analysis is deterministic and does NOT represent a probabilistic "
        "Monte Carlo simulation or empirical probability of failure."
    )
    warnings: List[str] = Field(default_factory=list)


def run_parameter_sensitivity(
    beta_deg: float,
    soil: SoilParameters,
    root: RootParameters,
    fs_target: float = 1.3,
    custom_sweeps: Optional[Dict[str, List[float]]] = None,
) -> SensitivityAnalysisResult:
    """Run deterministic one-at-a-time sensitivity sweeps across key geotechnical parameters.

    Supported parameters for sweep:
        - c_prime_kpa (Effective cohesion, kPa)
        - phi_prime_deg (Friction angle, deg)
        - z_m (Failure plane depth, m)
        - u_kpa (Pore pressure, kPa)
        - tensile_stress_input (Root tensile strength, kPa or user unit)
        - root_area_ratio (Root Area Ratio, dimensionless)
    """
    # 1. Compute baseline point
    base_res = calculate_reinforced_slope_scalar(
        beta_deg=beta_deg,
        soil=soil,
        root=root,
        fs_target=fs_target,
    )

    series_dict: Dict[str, ParameterSensitivitySeries] = {}

    # Define parameters to sweep and their default test variations if custom not supplied
    # Default variations are relative multiplier [0.5, 0.75, 1.0, 1.25, 1.5] on base values
    param_configs = {
        "c_prime_kpa": {
            "label": "Effective Soil Cohesion",
            "unit": "kPa",
            "base": soil.c_prime_kpa,
            "min": 0.0,
            "max": 100.0,
        },
        "phi_prime_deg": {
            "label": "Internal Friction Angle",
            "unit": "deg",
            "base": soil.phi_prime_deg,
            "min": 5.0,
            "max": 50.0,
        },
        "z_m": {
            "label": "Failure Plane Depth",
            "unit": "m",
            "base": soil.z_m,
            "min": 0.3,
            "max": 5.0,
        },
        "u_kpa": {
            "label": "Pore-Water Pressure",
            "unit": "kPa",
            "base": soil.u_kpa,
            "min": 0.0,
            "max": max(20.0, soil.gamma_kn_m3 * soil.z_m),
        },
        "tensile_stress_input": {
            "label": "Root Tensile Stress",
            "unit": root.tensile_stress_unit.value,
            "base": root.tensile_stress_input,
            "min": 100.0,
            "max": 100000.0,
        },
        "root_area_ratio": {
            "label": "Root Area Ratio (RAR)",
            "unit": "dimensionless",
            "base": root.root_area_ratio,
            "min": 0.0001,
            "max": 0.05,
        },
    }

    warnings: List[str] = []

    for param_key, config in param_configs.items():
        base_val = config["base"]

        if custom_sweeps and param_key in custom_sweeps:
            values_to_test = custom_sweeps[param_key]
        else:
            # Deterministic ±50% range
            multipliers = [0.5, 0.75, 1.0, 1.25, 1.5]
            if base_val == 0.0 and param_key == "u_kpa":
                values_to_test = [0.0, 2.0, 5.0, 10.0, 15.0]
            elif base_val == 0.0 and param_key == "c_prime_kpa":
                values_to_test = [0.0, 2.0, 5.0, 10.0, 15.0]
            else:
                values_to_test = [round(base_val * m, 4) for m in multipliers]

        points: List[SensitivityPoint] = []
        fs_reinf_vals: List[float] = []

        for val in sorted(values_to_test):
            if val < config["min"] or val > config["max"]:
                continue

            # Copy and modify soil or root
            s_test = soil.model_copy()
            r_test = root.model_copy()

            if param_key in ["c_prime_kpa", "phi_prime_deg", "z_m", "u_kpa"]:
                setattr(s_test, param_key, val)
            elif param_key in ["tensile_stress_input", "root_area_ratio"]:
                setattr(r_test, param_key, val)

            pt_res = calculate_reinforced_slope_scalar(
                beta_deg=beta_deg,
                soil=s_test,
                root=r_test,
                fs_target=fs_target,
            )

            point = SensitivityPoint(
                parameter_name=param_key,
                parameter_value=val,
                parameter_unit=config["unit"],
                fs_baseline=pt_res.fs_baseline,
                delta_c_kpa=pt_res.delta_c_kpa,
                fs_reinforced=pt_res.fs_reinforced,
                delta_fs=pt_res.delta_fs,
                target_reached=pt_res.target_reached,
                status=pt_res.status,
                note=pt_res.status_label,
            )
            points.append(point)
            if pt_res.fs_reinforced is not None:
                fs_reinf_vals.append(pt_res.fs_reinforced)

        series_dict[param_key] = ParameterSensitivitySeries(
            parameter_name=param_key,
            parameter_label=config["label"],
            unit=config["unit"],
            baseline_value=base_val,
            points=points,
            fs_range_reinforced=[min(fs_reinf_vals), max(fs_reinf_vals)] if fs_reinf_vals else [],
        )

    return SensitivityAnalysisResult(
        beta_deg=beta_deg,
        fs_target=fs_target,
        baseline_fs_unreinforced=base_res.fs_baseline,
        baseline_fs_reinforced=base_res.fs_reinforced,
        series=series_dict,
        warnings=warnings,
    )
