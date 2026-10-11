"""Pydantic schemas for Phase 2 Geospatial Data Engine."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RasterMetadata(BaseModel):
    filename: str
    width: int
    height: int
    bands: int
    dtype: str
    crs: Optional[str] = None
    is_geographic: bool = False
    pixel_size_x: float
    pixel_size_y: float
    bounds: Dict[str, float] = Field(
        ..., description="Bounding box with minx, miny, maxx, maxy"
    )
    nodata_value: Optional[float] = None
    valid_pixel_count: int
    nodata_pixel_count: int
    elevation_unit: str = "meters"
    validation_status: str = "VALID"
    validation_messages: List[str] = Field(default_factory=list)


class ElevationStats(BaseModel):
    min_elevation: float
    max_elevation: float
    mean_elevation: float
    median_elevation: Optional[float] = None
    unit: str = "meters"
    valid_pixels: int
    nodata_pixels: int


class SlopeStats(BaseModel):
    min_slope_deg: float
    max_slope_deg: float
    mean_slope_deg: float
    method: str = "Gradient-based Horn formulation (degrees)"
    calculation_crs: str = "Projected (Meters)"


class AspectStats(BaseModel):
    mean_aspect_deg: Optional[float] = None
    convention: str = (
        "Azimuth degrees from North: 0-360° (0°=N, 90°=E, 180°=S, 270°=W; flat=-1°)"
    )
    flat_pixel_count: int = 0


class TerrainResponse(BaseModel):
    status: str = "completed"
    dem_metadata: RasterMetadata
    elevation: ElevationStats
    slope: SlopeStats
    aspect: AspectStats
    slope_raster_id: Optional[str] = None
    aspect_raster_id: Optional[str] = None
    preview_image_id: Optional[str] = None
    notes: List[str] = Field(default_factory=list)


class NDVIStats(BaseModel):
    min_ndvi: float
    max_ndvi: float
    mean_ndvi: float
    valid_pixels: int
    zero_denominator_pixels: int = 0


class NDVIResponse(BaseModel):
    status: str = "completed"
    ndvi_stats: NDVIStats
    ndvi_raster_id: str
    preview_image_id: Optional[str] = None
    provenance: str
    warning: str


class SoilDataValidationRequest(BaseModel):
    source: str = Field(..., description="Soil data source name, e.g. ISRIC SoilGrids")
    property_name: str = Field(..., description="e.g. clay_fraction, bulk_density, soil_depth")
    depth_interval: Optional[str] = Field(None, description="e.g. 0-30cm")
    units: Optional[str] = Field(None, description="e.g. g/kg, g/cm³, cm")
    download_date: Optional[str] = None
    tabular_columns: Optional[List[str]] = None


class SoilDataValidationResponse(BaseModel):
    status: str = "validated"
    is_valid: bool
    source: str
    property_name: str
    depth_interval: Optional[str] = None
    units: Optional[str] = None
    provenance: Dict[str, Any]
    messages: List[str]
    warning: str


class VectorValidationResponse(BaseModel):
    format: str
    feature_count: int
    crs: Optional[str] = None
    geometry_types: List[str]
    bounds: Dict[str, float]
    is_valid: bool
    validation_messages: List[str]


class ParcelIntersectionResult(BaseModel):
    parcel_id: str
    name: str
    intersects_protected_area: bool
    protected_area_names: List[str] = Field(default_factory=list)
    overlap_area_hectares: Optional[float] = None
    exclusion_recommended: bool
    reason: Optional[str] = None


class ProtectedAreaIntersectionResponse(BaseModel):
    status: str = "completed"
    total_parcels_evaluated: int
    intersecting_parcels_count: int
    results: List[ParcelIntersectionResult]
    protected_area_source: str
    disclaimer: str


class GeospatialEngineStatus(BaseModel):
    status: str = "ready"
    engine_backend: str
    supported_raster_formats: List[str]
    supported_vector_formats: List[str]
    native_gdal_available: bool
    available_sample_datasets: List[str]
    intended_pilot_region: str = "Western Ghats Corridor (Intended Pilot Study Area)"
    pilot_bounds: Optional[Dict[str, float]] = None
    demo_study_area: str = "Cascade Foothills Demonstration Basin (Synthetic Test Fixture)"
