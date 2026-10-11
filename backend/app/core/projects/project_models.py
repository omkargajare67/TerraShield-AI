"""Project metadata and configuration data models."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GeotechnicalPreset(BaseModel):
    name: str
    description: str
    c_prime_kpa: float
    phi_deg: float
    gamma_kn_m3: float
    depth_m: float
    m_water_table: float
    tensile_stress_kpa: float
    rar: float
    k_factor: float
    target_fs: float = 1.3
    is_demo: bool = False


STANDARD_GEOTECHNICAL_PRESETS: Dict[str, GeotechnicalPreset] = {
    "wayanad_saprolite": GeotechnicalPreset(
        name="Tropical Monsoon Saprolite (Wayanad Baseline)",
        description="Lateritic weathered saprolite typical of Western Ghats steep slopes under heavy monsoon infiltration.",
        c_prime_kpa=8.0,
        phi_deg=26.0,
        gamma_kn_m3=18.5,
        depth_m=1.8,
        m_water_table=0.5,
        tensile_stress_kpa=25000.0,
        rar=0.002,
        k_factor=1.2,
        target_fs=1.3,
        is_demo=False,
    ),
    "colluvial_clay_silt": GeotechnicalPreset(
        name="Colluvial Clay-Silt Hillslope",
        description="Fine-grained colluvial mantle on moderate to steep slopes prone to seasonal creep and reactivation.",
        c_prime_kpa=12.0,
        phi_deg=22.0,
        gamma_kn_m3=19.0,
        depth_m=2.2,
        m_water_table=0.6,
        tensile_stress_kpa=20000.0,
        rar=0.0015,
        k_factor=1.1,
        target_fs=1.3,
        is_demo=False,
    ),
    "residual_sandy_loam": GeotechnicalPreset(
        name="Residual Sandy Loam",
        description="Coarse-textured well-drained weathered mantle with high internal friction and moderate cohesion.",
        c_prime_kpa=4.0,
        phi_deg=32.0,
        gamma_kn_m3=17.5,
        depth_m=1.5,
        m_water_table=0.3,
        tensile_stress_kpa=30000.0,
        rar=0.0025,
        k_factor=1.2,
        target_fs=1.3,
        is_demo=False,
    ),
    "glacial_till_demo": GeotechnicalPreset(
        name="Glacial Till / Foothills (Demo Scenario)",
        description="Illustrative synthetic parameters for Cascade Foothills offline demonstration.",
        c_prime_kpa=10.0,
        phi_deg=28.0,
        gamma_kn_m3=19.5,
        depth_m=1.6,
        m_water_table=0.4,
        tensile_stress_kpa=22000.0,
        rar=0.0018,
        k_factor=1.15,
        target_fs=1.3,
        is_demo=True,
    ),
}


class ProjectMetadata(BaseModel):
    id: str
    name: str
    description: str = ""
    is_builtin: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    study_area_type: str = "preset"  # preset, bbox, polygon_draw, uploaded_file
    bounds: Dict[str, float] = Field(
        default_factory=lambda: {"minx": 76.00, "miny": 11.55, "maxx": 76.10, "maxy": 11.65}
    )
    native_crs: str = "EPSG:4326 (WGS 84)"
    boundary_geojson: Optional[Dict[str, Any]] = None
    layers: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    geotechnical_parameters: Dict[str, Any] = Field(default_factory=dict)
    recommendation_settings: Dict[str, Any] = Field(default_factory=dict)
    latest_run_id: Optional[str] = None
    saved_runs: List[Dict[str, Any]] = Field(default_factory=list)
