"""Pydantic schemas for the Phase 4 Spatial Recommendation API."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class InputLayerStatus(BaseModel):
    layer_name: str
    available: bool
    file_path: Optional[str] = None
    category: str
    description: str


class RecommendationStatusResponse(BaseModel):
    status: str
    pilot_study_area_bounds: Dict[str, float]
    native_crs: str
    supported_cell_sizes_m: List[int]
    input_layers: Dict[str, InputLayerStatus]
    dem_verified_source: str
    geotechnical_scenario_status: str
    protected_area_data_status: str
    species_database_status: str


class ParcelGenerationRequest(BaseModel):
    minx: float = Field(default=76.00, ge=-180.0, le=180.0)
    miny: float = Field(default=11.55, ge=-90.0, le=90.0)
    maxx: float = Field(default=76.10, ge=-180.0, le=180.0)
    maxy: float = Field(default=11.65, ge=-90.0, le=90.0)
    cell_size_m: float = Field(default=300.0, ge=50.0, le=5000.0)


class ParcelSummary(BaseModel):
    parcel_id: str
    total_area_ha: float
    bounds: Dict[str, float]


class ParcelGenerationResponse(BaseModel):
    run_id: str
    cell_size_m: float
    parcel_count: int
    total_grid_area_ha: float
    bounds: Dict[str, float]
    sample_parcels: List[ParcelSummary]


class EligibilitySettingsSchema(BaseModel):
    min_terrain_coverage_pct: float = Field(default=80.0, ge=10.0, le=100.0)
    max_slope_deg: float = Field(default=45.0, ge=5.0, le=80.0)
    enable_ndvi_canopy_filter: bool = Field(default=False)
    ndvi_canopy_threshold: float = Field(default=0.65, ge=-1.0, le=1.0)
    min_plantable_area_ha: float = Field(default=0.25, ge=0.01, le=100.0)


class ScoringWeightsSchema(BaseModel):
    weight_geotechnical_need: float = Field(default=0.35, ge=0.0)
    weight_stability_gain: float = Field(default=0.30, ge=0.0)
    weight_plantable_area: float = Field(default=0.20, ge=0.0)
    weight_data_confidence: float = Field(default=0.15, ge=0.0)


class NormalizationConfigSchema(BaseModel):
    fs_target: float = Field(default=1.3, ge=1.0, le=3.0)
    critical_fs: float = Field(default=0.7, ge=0.1, le=1.2)
    max_delta_fs_ref: float = Field(
        default=15.0,
        gt=0.0,
        description="Configurable normalization reference divisor for modeled stability improvement (delta FS), not a validated engineering threshold",
    )
    max_area_ref_ha: float = Field(default=15.0, gt=0.0)


class BudgetConfigSchema(BaseModel):
    total_budget_inr: float = Field(..., gt=0.0)
    cost_per_sapling_inr: float = Field(default=150.0, gt=0.0)
    fixed_parcel_setup_cost_inr: float = Field(default=5000.0, ge=0.0)
    default_planting_density_stems_ha: float = Field(default=400.0, gt=0.0)
    max_stems_per_ha_cap: float = Field(default=1000.0, gt=0.0)


class RecommendationRunRequest(BaseModel):
    cell_size_m: float = Field(default=300.0, ge=50.0, le=2000.0)
    eligibility_settings: Optional[EligibilitySettingsSchema] = None
    scoring_weights: Optional[ScoringWeightsSchema] = None
    normalization_config: Optional[NormalizationConfigSchema] = None
    missing_data_policy: Optional[str] = Field(default="RENORMALIZE_AVAILABLE")
    budget_config: Optional[BudgetConfigSchema] = None
    user_exclusions_geojson: Optional[Dict[str, Any]] = None
    protected_areas_geojson: Optional[Dict[str, Any]] = None
    fs_target: float = Field(default=1.3, ge=1.0, le=3.0)
    project_id: Optional[str] = None
    study_area_bounds: Optional[Dict[str, float]] = None
    study_area_geojson: Optional[Dict[str, Any]] = None
    custom_layers: Optional[Dict[str, str]] = None
    geotechnical_parameters: Optional[Dict[str, Any]] = None



class RankedParcelSummary(BaseModel):
    rank: Optional[int] = None
    parcel_id: str
    priority_score_index: float
    plantable_area_ha: float
    total_area_ha: float
    slope_mean_deg: Optional[float] = None
    fs_baseline_mean: Optional[float] = None
    fs_delta_mean: Optional[float] = None
    primary_driver: str
    modeled_stability_gain_per_stem: Optional[float] = None
    estimated_required_stems: Optional[float] = None


class RecommendationRunResponse(BaseModel):
    run_id: str
    timestamp: str
    total_parcels: int
    eligible_count: int
    excluded_count: int
    insufficient_data_count: int
    total_plantable_area_ha: float
    top_recommendations: List[RankedParcelSummary]
    scoring_weights_normalized: Dict[str, float]
    scoring_weights_active: Dict[str, float]
    applied_missing_data_policy: str
    missing_layers_detected: List[str]
    is_discriminative: bool = True
    differentiation_warning: Optional[str] = None
    differentiating_components: List[str] = Field(default_factory=list)
    constant_components: List[str] = Field(default_factory=list)
    normalization_references: Dict[str, float]
    dem_source_provenance: str
    provenance_warning: str
    artifacts: Dict[str, str]
    budget_summary: Optional[Dict[str, Any]] = None
