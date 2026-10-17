"""Data models for Real-World Landslide Case Study Library in TerraShield AI.

Defines schemas for curated historical and recent disaster case studies,
their authoritative citations, observed spatial landslide inventories,
and dataset licensing details.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CaseStudySourceReference(BaseModel):
    """Authoritative scientific or governmental source reference."""
    title: str
    organization: str
    publication_year: Optional[int] = None
    url: Optional[str] = None
    document_type: str = "Government Technical Report"  # Journal, Bulletin, Early Warning Report
    verification_notes: str = ""


class CaseStudyDataset(BaseModel):
    """Specific terrain or satellite dataset associated with a case study."""
    name: str
    provider: str
    resolution_m: float
    dataset_type: str  # elevation, multispectral_ndvi, optical_rgb, soil_survey
    status: str  # VERIFIED_LOCAL, STAC_ACQUIRABLE, PROVISIONAL, SYNTHETIC
    attribution: str
    access_url: Optional[str] = None
    notes: Optional[str] = None


class CaseStudy(BaseModel):
    """Complete definition of a real-world landslide case study."""
    id: str
    name: str
    country: str
    state_province: str
    district: str
    locality: str
    event_date: str  # ISO date or text range (e.g. "2024-07-30" or "July-August 2023")
    disaster_type: str
    short_description: str
    region_tag: str  # western_ghats, himalayas, nepal, offline_demo
    temporal_tag: str  # historical, recent, benchmark
    analysis_mode: str  # PRE_EVENT_RETROSPECTIVE, POST_EVENT_RESTORATION, MONITORING_CONTEXT, OFFLINE_TESTING
    verification_status: str  # VERIFIED_OBSERVATION, HISTORICAL_CATALOG, PROVISIONAL_RECENT, OFFLINE_BENCHMARK
    readiness: str  # READY_TO_ANALYZE, CACHED_ANALYSIS_AVAILABLE, AWAITING_ADDITIONAL_DATA

    bounds: Dict[str, float]  # minx, miny, maxx, maxy
    center: List[float]  # [lat, lon]
    study_area_ha: Optional[float] = None
    study_area_geojson: Optional[Dict[str, Any]] = None

    geometry_provenance: str
    geometry_confidence: str  # HIGH_CADASTRAL, MODERATE_WATERSHED, PROVISIONAL_CORRIDOR, SYNTHETIC

    source_references: List[CaseStudySourceReference] = Field(default_factory=list)
    terrain_datasets: List[CaseStudyDataset] = Field(default_factory=list)
    vegetation_datasets: List[CaseStudyDataset] = Field(default_factory=list)

    observed_landslide_inventory: Optional[Dict[str, Any]] = None  # GeoJSON FeatureCollection
    inventory_summary: str = ""

    data_acquisition_requirements: str = ""
    licensing_and_attribution: str = ""
    known_limitations: List[str] = Field(default_factory=list)

    suggested_geotech_preset: str = "wayanad_saprolite"
    suggested_cell_size_m: float = 250.0

    linked_project_id: Optional[str] = None  # If a matching ProjectWorkspace is pre-configured
