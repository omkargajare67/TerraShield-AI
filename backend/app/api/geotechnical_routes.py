"""FastAPI endpoints for Phase 3 Geotechnical Intelligence Engine."""

from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status

from backend.app.core.config import settings
from backend.app.core.geospatial.artifacts import get_safe_artifact_path
from backend.app.core.geospatial.raster_loader import inspect_geotiff
from backend.app.core.geotechnical.infinite_slope import calculate_infinite_slope_scalar
from backend.app.core.geotechnical.models import (
    InfiniteSlopeResult,
    ReinforcedSlopeResult,
    RequiredCohesionResult,
    RootCohesionResult,
    TreeDensityResult,
)
from backend.app.core.geotechnical.parameter_validation import (
    validate_root_parameters,
    validate_soil_parameters,
    validate_tree_density_calibration,
)
from backend.app.core.geotechnical.raster_analysis import (
    GEOTECHNICAL_DIR,
    process_geotechnical_raster,
)
from backend.app.core.geotechnical.required_cohesion import calculate_required_cohesion_scalar
from backend.app.core.geotechnical.root_cohesion import (
    calculate_reinforced_slope_scalar,
    calculate_root_cohesion,
)
from backend.app.core.geotechnical.sensitivity import run_parameter_sensitivity
from backend.app.core.geotechnical.tree_density import estimate_tree_density
from backend.app.schemas.geotechnical import (
    GeotechnicalStatusResponse,
    ParameterValidationRequest,
    ParameterValidationResponse,
    RasterAnalysisRequest,
    RasterAnalysisResponse,
    RootCohesionRequest,
    SensitivityRequest,
    SensitivityResponse,
    SlopeStabilityAnalysisRequest,
    SlopeStabilityAnalysisResponse,
    TargetCohesionRequest,
)

router = APIRouter(prefix="/geotechnical", tags=["Geotechnical Intelligence"])

DEFAULT_REAL_SLOPE = settings.BASE_DIR / "data" / "processed" / "real" / "wayanad_slope.tif"


@router.get(
    "/status",
    response_model=GeotechnicalStatusResponse,
    summary="Geotechnical Engine and Terrain Data Status",
)
def get_geotechnical_status() -> GeotechnicalStatusResponse:
    """Check availability of real Wayanad slope inputs and existing geotechnical products."""
    slope_exists = DEFAULT_REAL_SLOPE.exists()
    metadata = None
    if slope_exists:
        try:
            _, metadata = inspect_geotiff(DEFAULT_REAL_SLOPE)
        except Exception:
            metadata = None

    existing_products: List[str] = []
    if GEOTECHNICAL_DIR.exists():
        existing_products = [f.name for f in GEOTECHNICAL_DIR.glob("*.*") if f.is_file()]

    return GeotechnicalStatusResponse(
        real_slope_available=slope_exists,
        slope_file=str(DEFAULT_REAL_SLOPE),
        slope_metadata=metadata,
        geotechnical_products_available=existing_products,
    )


@router.post(
    "/parameters/validate",
    response_model=ParameterValidationResponse,
    summary="Validate Geotechnical and Root Parameters",
)
def validate_parameters(req: ParameterValidationRequest) -> ParameterValidationResponse:
    """Validate physical plausibility, unit consistency, and provenance records."""
    all_msgs: List[str] = []
    soil_valid, soil_msgs = validate_soil_parameters(req.soil)
    all_msgs.extend(soil_msgs)

    root_valid = True
    if req.root is not None:
        root_valid, root_msgs = validate_root_parameters(req.root)
        all_msgs.extend(root_msgs)

    cal_valid = None
    if req.calibration is not None:
        cal_valid, cal_msgs = validate_tree_density_calibration(req.calibration)
        all_msgs.extend(cal_msgs)

    # Collect provenance records
    provenance_summary: Dict[str, Any] = {}
    if req.soil.provenance:
        provenance_summary["soil"] = {
            k: v.model_dump() for k, v in req.soil.provenance.items()
        }
    if req.root and req.root.provenance:
        provenance_summary["root"] = {
            k: v.model_dump() for k, v in req.root.provenance.items()
        }
    if req.calibration and req.calibration.provenance_note:
        provenance_summary["calibration"] = req.calibration.provenance_note

    is_overall_valid = soil_valid and root_valid and (cal_valid is None or cal_valid)

    return ParameterValidationResponse(
        is_valid=is_overall_valid,
        soil_valid=soil_valid,
        root_valid=root_valid,
        calibration_valid=cal_valid,
        messages=all_msgs,
        provenance_summary=provenance_summary,
    )


@router.post(
    "/root-cohesion",
    response_model=RootCohesionResult,
    summary="Calculate Additional Root Cohesion",
)
def compute_root_cohesion_endpoint(req: RootCohesionRequest) -> RootCohesionResult:
    """Compute Delta_C = K * Tr * RAR and total cohesion."""
    try:
        return calculate_root_cohesion(
            root=req.root,
            base_soil_cohesion_kpa=req.base_soil_cohesion_kpa,
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        )


@router.post(
    "/analysis",
    response_model=SlopeStabilityAnalysisResponse,
    summary="Single-Point Slope Stability and Reinforcement Analysis",
)
def analyze_slope_stability(req: SlopeStabilityAnalysisRequest) -> SlopeStabilityAnalysisResponse:
    """Run baseline, root-reinforced, target solver, and calibrated tree-density estimation."""
    # 1. Baseline infinite slope
    base_res = calculate_infinite_slope_scalar(req.beta_deg, req.soil)

    # 2. Root cohesion & reinforcement (if root supplied)
    root_res: Optional[RootCohesionResult] = None
    reinf_res: Optional[ReinforcedSlopeResult] = None
    if req.root is not None:
        try:
            root_res = calculate_root_cohesion(req.root, base_soil_cohesion_kpa=req.soil.c_prime_kpa)
            reinf_res = calculate_reinforced_slope_scalar(
                beta_deg=req.beta_deg,
                soil=req.soil,
                root=req.root,
                fs_target=req.fs_target,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Root parameter calculation error: {str(e)}",
            )

    # 3. Target solver
    target_res = calculate_required_cohesion_scalar(
        beta_deg=req.beta_deg,
        soil=req.soil,
        fs_target=req.fs_target,
        root=req.root,
    )

    # 4. Tree density estimation
    tree_res: Optional[TreeDensityResult] = None
    if req.root is not None and target_res.delta_c_required_kpa is not None:
        tree_res = estimate_tree_density(
            delta_c_required_kpa=target_res.delta_c_required_kpa,
            root=req.root,
            calibration=req.calibration,
        )

    # Status interpretation
    if reinf_res is not None:
        target_reached = reinf_res.target_reached
        status_label = reinf_res.status_label
    else:
        target_reached = (base_res.factor_of_safety or 0.0) >= req.fs_target
        status_label = (
            "Target reached under baseline conditions"
            if target_reached
            else "Target not reached under baseline conditions"
        )

    warnings: List[str] = list(base_res.warnings)
    if reinf_res:
        warnings.extend(reinf_res.warnings)
    if tree_res:
        warnings.extend(tree_res.warnings)

    return SlopeStabilityAnalysisResponse(
        beta_deg=req.beta_deg,
        baseline=base_res,
        root_reinforcement=root_res,
        reinforced=reinf_res,
        target_solver=target_res,
        tree_density=tree_res,
        fs_target=req.fs_target,
        target_reached=target_reached,
        status_label=status_label,
        warnings=list(dict.fromkeys(warnings)),  # deduplicate preserving order
    )


@router.post(
    "/target-solver",
    response_model=RequiredCohesionResult,
    summary="Solve Required Additional Root Cohesion for Target FS",
)
def solve_target_cohesion(req: TargetCohesionRequest) -> RequiredCohesionResult:
    """Solve Delta_C_required = max(0, FS_target * tau - c' - (sigma_n - u)*tan(phi'))."""
    try:
        return calculate_required_cohesion_scalar(
            beta_deg=req.beta_deg,
            soil=req.soil,
            fs_target=req.fs_target,
            root=req.root,
            max_allowable_rar=req.max_allowable_rar,
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        )


@router.post(
    "/sensitivity",
    response_model=SensitivityResponse,
    summary="Deterministic Parameter Sensitivity Analysis",
)
def compute_sensitivity(req: SensitivityRequest) -> SensitivityResponse:
    """Run deterministic one-at-a-time parameter sensitivity sweeps."""
    try:
        res = run_parameter_sensitivity(
            beta_deg=req.beta_deg,
            soil=req.soil,
            root=req.root,
            fs_target=req.fs_target,
            custom_sweeps=req.custom_sweeps,
        )
        return SensitivityResponse(
            beta_deg=res.beta_deg,
            fs_target=res.fs_target,
            baseline_fs_unreinforced=res.baseline_fs_unreinforced,
            baseline_fs_reinforced=res.baseline_fs_reinforced,
            series=res.series,
            methodology_note=res.methodology_note,
            warnings=res.warnings,
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sensitivity calculation failed: {str(err)}",
        )


@router.post(
    "/raster-analysis",
    response_model=RasterAnalysisResponse,
    summary="Spatial Geotechnical Analysis Across Terrain Slope Raster",
)
def analyze_raster(req: RasterAnalysisRequest) -> RasterAnalysisResponse:
    """Execute geotechnical infinite slope model per-pixel on Wayanad slope raster."""
    if req.slope_artifact_id:
        slope_path = get_safe_artifact_path(req.slope_artifact_id)
        if not slope_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Slope raster artifact '{req.slope_artifact_id}' not found.",
            )
    else:
        slope_path = DEFAULT_REAL_SLOPE
        if not slope_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Default real Wayanad slope raster not found at {DEFAULT_REAL_SLOPE}.",
            )

    try:
        summary_dict = process_geotechnical_raster(
            slope_path=slope_path,
            soil=req.soil,
            root=req.root,
            fs_target=req.fs_target,
            calibration=req.calibration,
        )
        return RasterAnalysisResponse(**summary_dict)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Raster analysis failed: {str(err)}",
        )
