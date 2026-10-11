"""Data provenance, environmental observation tracking, and scientific disclosures."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DatasetProvenance(BaseModel):
    """Metadata tracking source authenticity, processing level, and scientific status."""
    layer_name: str
    category: str = Field(
        ...,
        description="REAL_OBSERVED, DERIVED_GEOSPATIAL, ILLUSTRATIVE_SCENARIO, or UNVERIFIED_STATUS",
    )
    source_description: str
    spatial_resolution_approx: str
    is_field_validated: bool
    limitations: List[str]


class RecommendationProvenance(BaseModel):
    """Holistic provenance record for Phase 4 spatial recommendation analysis."""
    run_id: str
    timestamp: str
    study_area_crs: str = "EPSG:4326 (WGS 84)"
    metric_projection_used_for_area: str = "Local ellipsoidal geodesic metric projection"
    datasets: Dict[str, DatasetProvenance]
    geotechnical_is_illustrative: bool = True
    geotechnical_scenario_note: str
    protected_area_verification_status: str
    scientific_disclosures: List[str]


def build_recommendation_provenance(
    run_id: str,
    timestamp: str,
    geotech_summary_path: Optional[Path] = None,
    has_official_protected_areas: bool = False,
) -> RecommendationProvenance:
    """Build a comprehensive provenance record tracing all recommendation inputs."""
    geotech_note = (
        "Illustrative exploratory geotechnical scenario using spatially uniform parameters. "
        "Not spatially interpolated field borehole observations."
    )
    geotech_is_illustrative = True

    if geotech_summary_path and geotech_summary_path.is_file():
        try:
            with open(geotech_summary_path, "r", encoding="utf-8") as f:
                geo_summary = json.load(f)
                scenario_assumptions = geo_summary.get("scenario_assumptions", {})
                geotech_is_illustrative = scenario_assumptions.get("is_illustrative_scenario", True)
                if "spatial_uniformity_disclosure" in scenario_assumptions:
                    geotech_note = scenario_assumptions["spatial_uniformity_disclosure"]
        except Exception:
            pass

    pa_status = (
        "VERIFIED: Evaluated against user-supplied statutory protected-area boundaries."
        if has_official_protected_areas
        else "UNVERIFIED: Official legal cadastral reserve dataset unavailable. Protected-area clearance unverified."
    )

    datasets = {
        "elevation": DatasetProvenance(
            layer_name="wayanad_dem.tif",
            category="REAL_OBSERVED",
            source_description="NASA SRTM NASADEM Global 1 Arc-Second V001 (Item: NASADEM_HGT_n11e076)",
            spatial_resolution_approx="1 arc-second (~30.8 meters, 0.0002778 deg)",
            is_field_validated=True,
            limitations=[
                "Derived from Space Shuttle Radar Topography Mission C-band radar with ALOS/ASTER void-filling.",
                "Contains C-band radar elevation bias over dense tropical wet evergreen forest canopies.",
                "SHA-256 verified against Microsoft Planetary Computer STAC: 680aa3cb46f4b7d148b2d62224ff8f8daa9591dcee5921d46c0f8c4c8a5ca2b6.",
            ],
        ),
        "slope": DatasetProvenance(
            layer_name="wayanad_slope.tif",
            category="DERIVED_GEOSPATIAL",
            source_description="Horns 8-neighbourhood gradient calculated over genuine DEM",
            spatial_resolution_approx="~30.8 meters",
            is_field_validated=True,
            limitations=["Calculated on projected metric cell dimensions; micro-topographic gullies smoothed."],
        ),
        "aspect": DatasetProvenance(
            layer_name="wayanad_aspect.tif",
            category="DERIVED_GEOSPATIAL",
            source_description="Compass azimuth orientation calculated over genuine DEM",
            spatial_resolution_approx="~30.8 meters",
            is_field_validated=True,
            limitations=["Aspect undefined on perfectly horizontal pixels (assigned flat sentinel)."],
        ),
        "ndvi": DatasetProvenance(
            layer_name="wayanad_ndvi.tif",
            category="DERIVED_GEOSPATIAL",
            source_description="Copernicus Sentinel-2 L2A BOA reflectance (B04 Red, B08 NIR)",
            spatial_resolution_approx="~10.0 meters (0.000091 deg)",
            is_field_validated=True,
            limitations=[
                "NDVI is a photosynthetic greenness index, NOT direct proof of species, root architecture, or land tenure."
            ],
        ),
        "fs_baseline": DatasetProvenance(
            layer_name="wayanad_fs_baseline.tif",
            category="ILLUSTRATIVE_SCENARIO",
            source_description="Phase 3 Infinite Slope limit-equilibrium model with exploratory uniform parameters",
            spatial_resolution_approx="~30.8 meters",
            is_field_validated=False,
            limitations=[
                "Assumes spatially uniform soil cohesion (5 kPa) and friction angle (28°).",
                "Factor of Safety is a mechanistic stability index, NOT an empirical landslide probability.",
            ],
        ),
        "fs_delta": DatasetProvenance(
            layer_name="wayanad_fs_delta.tif",
            category="ILLUSTRATIVE_SCENARIO",
            source_description="Modeled Factor of Safety increase under Wu-Waldron root reinforcement assumption",
            spatial_resolution_approx="~30.8 meters",
            is_field_validated=False,
            limitations=[
                "Wu-Waldron model assumes simultaneous root tensile failure and overestimates cohesion reinforcement.",
                "Delta FS represents a modeled mechanistic shift, NOT empirical landslide risk reduction (delta R).",
            ],
        ),
    }

    disclosures = [
        "FACTOR OF SAFETY DISTINCTION: Factor of Safety (FS) is a mechanistic stability index, not a calibrated landslide probability.",
        "RISK REDUCTION DISTINCTION: Modeled change in Factor of Safety (delta FS) is NOT equivalent to empirical landslide risk reduction (delta R). The project leverage metric L = delta_R / N is evaluated as modeled stability gain per stem ONLY when tree density calibration exists.",
        "VEGETATION PROXY DISTINCTION: Sentinel-2 NDVI reflects photosynthetic activity. It does not certify botanical species composition, root tensile strength, or planting feasibility.",
        "PROTECTED LAND DISCLAIMER: Absence of a statutory exclusion polygon does NOT imply land is legally unencumbered or officially cleared for afforestation.",
        "DECISION-SUPPORT NOTICE: Recommendation rankings are prioritized decision-support outputs based on exploratory parameters, not certified civil or geotechnical engineering prescriptions.",
    ]

    return RecommendationProvenance(
        run_id=run_id,
        timestamp=timestamp,
        datasets=datasets,
        geotechnical_is_illustrative=geotech_is_illustrative,
        geotechnical_scenario_note=geotech_note,
        protected_area_verification_status=pa_status,
        scientific_disclosures=disclosures,
    )
