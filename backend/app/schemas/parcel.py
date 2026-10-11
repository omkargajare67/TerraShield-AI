"""Schemas for parcel demonstration data."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ParcelProperties(BaseModel):
    parcel_id: str
    name: str
    description: str
    area_hectares: float
    demo_baseline_risk: float
    demo_delta_risk: float
    demo_tree_count: int
    is_excluded: bool
    exclusion_reason: Optional[str] = None
    is_synthetic: bool = True


class ParcelFeature(BaseModel):
    type: str = "Feature"
    id: str
    properties: ParcelProperties
    geometry: Dict[str, Any]


class ParcelFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    metadata: Dict[str, Any]
    features: List[ParcelFeature]
