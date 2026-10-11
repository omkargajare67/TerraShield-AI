"""Schemas for demonstration analysis requests and responses."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    scenario: str = Field(
        default="landslide_mitigation",
        description="Target intervention scenario. Phase 1 supports 'landslide_mitigation'."
    )
    min_risk_threshold: Optional[float] = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Optional minimum baseline risk threshold for filtering candidate parcels."
    )


class ParcelAnalysisResult(BaseModel):
    parcel_id: str
    name: str
    description: str
    area_hectares: float
    demo_baseline_risk: float
    demo_delta_risk: float
    demo_tree_count: int
    is_excluded: bool
    exclusion_reason: Optional[str] = None
    demo_leverage_score: Optional[float] = None
    rank: Optional[int] = None
    is_synthetic: bool = True


class StudyAreaMetadata(BaseModel):
    name: str
    coordinates_center: List[float]
    crs: str
    data_type: str
    is_synthetic: bool


class AnalysisResponse(BaseModel):
    app_mode: str = "demo"
    scenario: str
    study_area: StudyAreaMetadata
    status: str = "completed"
    total_candidate_parcels: int
    eligible_parcels_count: int
    excluded_parcels_count: int
    highest_leverage_score: Optional[float] = None
    highest_leverage_parcel_id: Optional[str] = None
    parcels: List[ParcelAnalysisResult]
    geojson: Dict[str, Any]
    provenance: str
    warning: str
