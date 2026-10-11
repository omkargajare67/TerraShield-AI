"""Project Workspace Service: persistence and management of analysis projects."""

import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.core.config import settings
from backend.app.core.projects.project_models import (
    ProjectMetadata,
    STANDARD_GEOTECHNICAL_PRESETS,
)

PROJECTS_DIR = settings.BASE_DIR / "data" / "projects"
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "_", slug)[:32]


def _init_builtin_projects():
    """Ensure baseline demonstration and pilot projects exist on disk."""
    # 1. Wayanad Watershed Pilot
    wayanad_dir = PROJECTS_DIR / "wayanad_pilot"
    wayanad_meta_file = wayanad_dir / "project.json"
    if not wayanad_meta_file.exists():
        wayanad_dir.mkdir(parents=True, exist_ok=True)
        w_preset = STANDARD_GEOTECHNICAL_PRESETS["wayanad_saprolite"]
        p_wayanad = ProjectMetadata(
            id="wayanad_pilot",
            name="Wayanad Watershed Pilot (Kerala, India)",
            description=(
                "Verified Western Ghats watershed study area using NASA SRTM NASADEM (30m) "
                "and Sentinel-2 L2A NDVI (10m) for landslide-risk vegetative stabilization."
            ),
            is_builtin=True,
            study_area_type="preset",
            bounds={"minx": 76.00, "miny": 11.55, "maxx": 76.10, "maxy": 11.65},
            native_crs="EPSG:4326 (WGS 84)",
            layers={
                "dem": {
                    "path": str(settings.BASE_DIR / "data" / "raw" / "real" / "wayanad_dem.tif"),
                    "status": "VERIFIED_OBSERVATION",
                    "description": "NASA SRTM NASADEM Global 1 Arc-Second V001 (NASADEM_HGT_n11e076)",
                },
                "slope": {
                    "path": str(settings.PROCESSED_DIR / "real" / "wayanad_slope.tif"),
                    "status": "DERIVED_GEOSPATIAL",
                    "description": "Horn's 8-neighbourhood gradient raster (30m)",
                },
                "aspect": {
                    "path": str(settings.PROCESSED_DIR / "real" / "wayanad_aspect.tif"),
                    "status": "DERIVED_GEOSPATIAL",
                    "description": "Topographic compass azimuth raster (30m)",
                },
                "ndvi": {
                    "path": str(settings.PROCESSED_DIR / "real" / "wayanad_ndvi.tif"),
                    "status": "DERIVED_GEOSPATIAL",
                    "description": "Sentinel-2 BOA Normalized Difference Vegetation Index (10m)",
                },
                "fs_baseline": {
                    "path": str(settings.PROCESSED_DIR / "geotechnical" / "wayanad_fs_baseline.tif"),
                    "status": "ILLUSTRATIVE_SCENARIO",
                    "description": "Infinite Slope Baseline Factor of Safety",
                },
                "fs_reinforced": {
                    "path": str(settings.PROCESSED_DIR / "geotechnical" / "wayanad_fs_reinforced.tif"),
                    "status": "ILLUSTRATIVE_SCENARIO",
                    "description": "Infinite Slope Root-Reinforced Factor of Safety",
                },
                "fs_delta": {
                    "path": str(settings.PROCESSED_DIR / "geotechnical" / "wayanad_fs_delta.tif"),
                    "status": "ILLUSTRATIVE_SCENARIO",
                    "description": "Modeled Factor of Safety Improvement",
                },
                "required_cohesion": {
                    "path": str(settings.PROCESSED_DIR / "geotechnical" / "wayanad_required_cohesion.tif"),
                    "status": "ILLUSTRATIVE_SCENARIO",
                    "description": "Root cohesion needed for FS >= 1.3",
                },
                "tree_density": {
                    "path": str(settings.PROCESSED_DIR / "geotechnical" / "wayanad_required_tree_density.tif"),
                    "status": "ILLUSTRATIVE_SCENARIO",
                    "description": "Required Stem Density from linear RAR scaling",
                },
            },
            geotechnical_parameters={
                "preset_id": "wayanad_saprolite",
                "name": w_preset.name,
                "soil": {
                    "c_prime_kpa": w_preset.c_prime_kpa,
                    "phi_deg": w_preset.phi_deg,
                    "gamma_kn_m3": w_preset.gamma_kn_m3,
                    "depth_m": w_preset.depth_m,
                    "m_water_table": w_preset.m_water_table,
                },
                "root": {
                    "tensile_stress_kpa": w_preset.tensile_stress_kpa,
                    "rar": w_preset.rar,
                    "k_factor": w_preset.k_factor,
                },
                "target_fs": w_preset.target_fs,
                "is_demo_parameters": w_preset.is_demo,
            },
            recommendation_settings={
                "cell_size_m": 300.0,
                "eligibility_settings": {
                    "min_terrain_coverage_pct": 80.0,
                    "max_slope_deg": 45.0,
                    "enable_ndvi_canopy_filter": False,
                    "ndvi_canopy_threshold": 0.65,
                    "min_plantable_area_ha": 0.25,
                },
                "scoring_weights": {
                    "weight_geotechnical_need": 0.35,
                    "weight_stability_gain": 0.30,
                    "weight_plantable_area": 0.20,
                    "weight_data_confidence": 0.15,
                },
                "normalization_config": {
                    "fs_target": 1.3,
                    "critical_fs": 0.7,
                    "max_delta_fs_ref": 15.0,
                    "max_area_ref_ha": 15.0,
                },
                "missing_data_policy": "RENORMALIZE_AVAILABLE",
            },
        )
        with open(wayanad_meta_file, "w", encoding="utf-8") as f:
            json.dump(p_wayanad.model_dump(), f, indent=2)

    # 2. Cascade Foothills Demo Basin
    cascade_dir = PROJECTS_DIR / "cascade_demo"
    cascade_meta_file = cascade_dir / "project.json"
    if not cascade_meta_file.exists():
        cascade_dir.mkdir(parents=True, exist_ok=True)
        c_preset = STANDARD_GEOTECHNICAL_PRESETS["glacial_till_demo"]
        sample_dem = settings.BASE_DIR / "data" / "sample" / "sample_dem.tif"
        p_cascade = ProjectMetadata(
            id="cascade_demo",
            name="Cascade Foothills Demonstration Basin (Offline Demo)",
            description=(
                "Deterministic synthetic demonstration basin for offline algorithmic testing and exploration."
            ),
            is_builtin=True,
            study_area_type="preset",
            bounds={"minx": -121.82, "miny": 47.42, "maxx": -121.74, "maxy": 47.48},
            native_crs="EPSG:4326 (WGS 84)",
            layers={
                "dem": {
                    "path": str(sample_dem) if sample_dem.exists() else "",
                    "status": "SYNTHETIC_TEST_FIXTURE",
                    "description": "Synthetic 256x256 test DEM with known elevation gradients",
                }
            },
            geotechnical_parameters={
                "preset_id": "glacial_till_demo",
                "name": c_preset.name,
                "soil": {
                    "c_prime_kpa": c_preset.c_prime_kpa,
                    "phi_deg": c_preset.phi_deg,
                    "gamma_kn_m3": c_preset.gamma_kn_m3,
                    "depth_m": c_preset.depth_m,
                    "m_water_table": c_preset.m_water_table,
                },
                "root": {
                    "tensile_stress_kpa": c_preset.tensile_stress_kpa,
                    "rar": c_preset.rar,
                    "k_factor": c_preset.k_factor,
                },
                "target_fs": c_preset.target_fs,
                "is_demo_parameters": True,
            },
            recommendation_settings={
                "cell_size_m": 300.0,
                "eligibility_settings": {
                    "min_terrain_coverage_pct": 80.0,
                    "max_slope_deg": 45.0,
                    "enable_ndvi_canopy_filter": False,
                    "ndvi_canopy_threshold": 0.65,
                    "min_plantable_area_ha": 0.25,
                },
                "scoring_weights": {
                    "weight_geotechnical_need": 0.35,
                    "weight_stability_gain": 0.30,
                    "weight_plantable_area": 0.20,
                    "weight_data_confidence": 0.15,
                },
                "normalization_config": {
                    "fs_target": 1.3,
                    "critical_fs": 0.7,
                    "max_delta_fs_ref": 15.0,
                    "max_area_ref_ha": 15.0,
                },
                "missing_data_policy": "RENORMALIZE_AVAILABLE",
            },
        )
        with open(cascade_meta_file, "w", encoding="utf-8") as f:
            json.dump(p_cascade.model_dump(), f, indent=2)


# Initialize on module import
_init_builtin_projects()


class ProjectService:
    """Service to create, update, retrieve, and execute project workspaces."""

    @staticmethod
    def list_projects() -> List[ProjectMetadata]:
        """List all existing projects."""
        projects = []
        for p_dir in PROJECTS_DIR.iterdir():
            if p_dir.is_dir():
                meta_file = p_dir / "project.json"
                if meta_file.exists():
                    try:
                        with open(meta_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            projects.append(ProjectMetadata(**data))
                    except Exception:
                        continue
        # Sort builtins first, then by updated_at descending
        projects.sort(key=lambda p: (not p.is_builtin, p.name))
        return projects

    @staticmethod
    def get_project(project_id: str) -> Optional[ProjectMetadata]:
        """Fetch project by ID."""
        meta_file = PROJECTS_DIR / project_id / "project.json"
        if not meta_file.exists():
            return None
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return ProjectMetadata(**data)
        except Exception:
            return None

    @staticmethod
    def create_project(
        name: str,
        description: str = "",
        study_area_type: str = "bbox",
        bounds: Optional[Dict[str, float]] = None,
        boundary_geojson: Optional[Dict[str, Any]] = None,
        geotech_preset_id: str = "wayanad_saprolite",
    ) -> ProjectMetadata:
        """Create a new user-defined analysis project."""
        p_id = f"proj_{_slugify(name)}_{uuid.uuid4().hex[:6]}"
        p_dir = PROJECTS_DIR / p_id
        p_dir.mkdir(parents=True, exist_ok=True)

        effective_bounds = bounds or {"minx": 76.00, "miny": 11.55, "maxx": 76.10, "maxy": 11.65}
        preset = STANDARD_GEOTECHNICAL_PRESETS.get(
            geotech_preset_id, STANDARD_GEOTECHNICAL_PRESETS["wayanad_saprolite"]
        )

        project = ProjectMetadata(
            id=p_id,
            name=name,
            description=description,
            is_builtin=False,
            study_area_type=study_area_type,
            bounds=effective_bounds,
            boundary_geojson=boundary_geojson,
            layers={},
            geotechnical_parameters={
                "preset_id": geotech_preset_id,
                "name": preset.name,
                "soil": {
                    "c_prime_kpa": preset.c_prime_kpa,
                    "phi_deg": preset.phi_deg,
                    "gamma_kn_m3": preset.gamma_kn_m3,
                    "depth_m": preset.depth_m,
                    "m_water_table": preset.m_water_table,
                },
                "root": {
                    "tensile_stress_kpa": preset.tensile_stress_kpa,
                    "rar": preset.rar,
                    "k_factor": preset.k_factor,
                },
                "target_fs": preset.target_fs,
                "is_demo_parameters": preset.is_demo,
            },
            recommendation_settings={
                "cell_size_m": 300.0,
                "eligibility_settings": {
                    "min_terrain_coverage_pct": 80.0,
                    "max_slope_deg": 45.0,
                    "enable_ndvi_canopy_filter": False,
                    "ndvi_canopy_threshold": 0.65,
                    "min_plantable_area_ha": 0.25,
                },
                "scoring_weights": {
                    "weight_geotechnical_need": 0.35,
                    "weight_stability_gain": 0.30,
                    "weight_plantable_area": 0.20,
                    "weight_data_confidence": 0.15,
                },
                "normalization_config": {
                    "fs_target": 1.3,
                    "critical_fs": 0.7,
                    "max_delta_fs_ref": 15.0,
                    "max_area_ref_ha": 15.0,
                },
                "missing_data_policy": "RENORMALIZE_AVAILABLE",
            },
        )

        meta_file = p_dir / "project.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(project.model_dump(), f, indent=2)

        return project

    @staticmethod
    def update_project(project: ProjectMetadata) -> ProjectMetadata:
        """Update and persist project metadata."""
        p_dir = PROJECTS_DIR / project.id
        p_dir.mkdir(parents=True, exist_ok=True)
        project.updated_at = datetime.now(timezone.utc).isoformat()
        meta_file = p_dir / "project.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(project.model_dump(), f, indent=2)
        return project

    @staticmethod
    def delete_project(project_id: str) -> bool:
        """Delete custom project directory. Builtin projects are protected."""
        project = ProjectService.get_project(project_id)
        if not project or project.is_builtin:
            return False
        p_dir = PROJECTS_DIR / project_id
        if p_dir.exists():
            shutil.rmtree(p_dir)
            return True
        return False
