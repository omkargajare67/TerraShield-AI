"""Pydantic schemas for Phase 3 Geotechnical Intelligence Engine API."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.core.geotechnical.models import (
    InfiniteSlopeResult,
    ReinforcedSlopeResult,
    RequiredCohesionResult,
    RootCohesionResult,
    RootParameters,
    SoilParameters,
    TreeDensityCalibration,
    TreeDensityResult,
)
from backend.app.core.geotechnical.sensitivity import ParameterSensitivitySeries
from backend.app.schemas.geospatial import RasterMetadata


class GeotechnicalStatusResponse(BaseModel):
    """System and dataset readiness for geotechnical modeling."""
    engine_status: str = "operational"
    phase: str = "Phase 3: Geotechnical Intelligence Engine"
    real_slope_available: bool
    slope_file: str
    slope_metadata: Optional[RasterMetadata] = None
    geotechnical_products_available: List[str] = Field(default_factory=list)
    supported_models: List[str] = Field(
        default_factory=lambda: [
            "Infinite Slope Stability (Limit Equilibrium)",
            "Wu-Waldron Vegetative Root Reinforcement (ΔC = K * Tr * RAR)",
            "Target Factor of Safety Cohesion Solver",
            "Calibrated Tree Stem Density Estimator",
            "Deterministic Parameter Sensitivity Sweeps",
        ]
    )
    scientific_disclaimer: str = (
        "Geotechnical outputs are exploratory limit-equilibrium scenario models, "
        "not certified site-specific geotechnical investigations or empirical landslide probability forecasts."
    )


class ParameterValidationRequest(BaseModel):
    """Request to validate geotechnical and biological parameter sets."""
    soil: SoilParameters
    root: Optional[RootParameters] = None
    calibration: Optional[TreeDensityCalibration] = None


class ParameterValidationResponse(BaseModel):
    """Validation report for geotechnical parameter inputs."""
    is_valid: bool
    soil_valid: bool
    root_valid: bool
    calibration_valid: Optional[bool] = None
    messages: List[str] = Field(default_factory=list)
    provenance_summary: Dict[str, Any] = Field(default_factory=dict)


class RootCohesionRequest(BaseModel):
    """Request to compute Wu-Waldron root cohesion."""
    root: RootParameters
    base_soil_cohesion_kpa: float = Field(default=0.0, ge=0.0)


class SlopeStabilityAnalysisRequest(BaseModel):
    """Single-location slope stability analysis request."""
    beta_deg: float = Field(..., ge=0.0, lt=90.0, description="Slope inclination in degrees")
    soil: SoilParameters
    root: Optional[RootParameters] = None
    fs_target: float = Field(default=1.3, gt=0.0, description="Target Factor of Safety benchmark")
    calibration: Optional[TreeDensityCalibration] = None


class SlopeStabilityAnalysisResponse(BaseModel):
    """Comprehensive single-location slope stability assessment."""
    beta_deg: float
    baseline: InfiniteSlopeResult
    root_reinforcement: Optional[RootCohesionResult] = None
    reinforced: Optional[ReinforcedSlopeResult] = None
    target_solver: Optional[RequiredCohesionResult] = None
    tree_density: Optional[TreeDensityResult] = None
    fs_target: float
    target_reached: bool
    status_label: str
    warnings: List[str] = Field(default_factory=list)


class TargetCohesionRequest(BaseModel):
    """Request to solve for required root cohesion to reach target FS."""
    beta_deg: float = Field(..., ge=0.0, lt=90.0)
    soil: SoilParameters
    fs_target: float = Field(default=1.3, gt=0.0)
    root: Optional[RootParameters] = None
    max_allowable_rar: float = Field(default=1.0, gt=0.0, le=1.0)


class SensitivityRequest(BaseModel):
    """Request for deterministic parameter sensitivity sweeps."""
    beta_deg: float = Field(..., ge=0.0, lt=90.0)
    soil: SoilParameters
    root: RootParameters
    fs_target: float = Field(default=1.3, gt=0.0)
    custom_sweeps: Optional[Dict[str, List[float]]] = None


class SensitivityResponse(BaseModel):
    """Deterministic sensitivity sweep output."""
    beta_deg: float
    fs_target: float
    baseline_fs_unreinforced: Optional[float] = None
    baseline_fs_reinforced: Optional[float] = None
    series: Dict[str, ParameterSensitivitySeries]
    methodology_note: str
    warnings: List[str] = Field(default_factory=list)


class RasterAnalysisRequest(BaseModel):
    """Request to execute spatial geotechnical analysis across a terrain slope raster."""
    slope_artifact_id: Optional[str] = Field(
        default=None,
        description="Optional artifact ID for slope GeoTIFF. If None, default approved Wayanad slope is used.",
    )
    soil: SoilParameters
    root: RootParameters
    fs_target: float = Field(default=1.3, gt=0.0)
    calibration: Optional[TreeDensityCalibration] = None


class RasterAnalysisResponse(BaseModel):
    """Summary of spatial raster geotechnical stability run."""
    run_id: str
    source_raster: str
    crs: Optional[str] = None
    bounds: Dict[str, float]
    pixel_resolution_x: float
    pixel_resolution_y: float
    total_pixels: int
    valid_pixels: int
    calculated_slope_pixels: int
    flat_terrain_pixels: int
    scenario_assumptions: Dict[str, Any]
    statistics: Dict[str, Any]
    artifacts: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)
