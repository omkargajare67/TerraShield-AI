"""FastAPI routes for Project Workspace management, dataset uploads, and processing."""

import json
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.core.geospatial.raster_loader import (
    align_and_resample_raster,
    inspect_geotiff,
    validate_and_inspect_uploaded_raster,
)
from backend.app.core.geospatial.terrain import process_dem_terrain
from backend.app.core.geospatial.vector_loader import parse_uploaded_study_area
from backend.app.core.geotechnical.models import RootParameters, SoilParameters, TreeDensityCalibration
from backend.app.core.geotechnical.raster_analysis import process_geotechnical_raster
from backend.app.core.projects.project_models import (
    ProjectMetadata,
    STANDARD_GEOTECHNICAL_PRESETS,
)
from backend.app.core.projects.project_service import (
    PROJECTS_DIR,
    ProjectService,
)

router = APIRouter(prefix="/projects", tags=["Project Workspaces"])


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str = ""
    study_area_type: str = "bbox"
    bounds: Optional[Dict[str, float]] = None
    boundary_geojson: Optional[Dict[str, Any]] = None
    geotech_preset_id: str = "wayanad_saprolite"


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    bounds: Optional[Dict[str, float]] = None
    boundary_geojson: Optional[Dict[str, Any]] = None
    geotechnical_parameters: Optional[Dict[str, Any]] = None
    recommendation_settings: Optional[Dict[str, Any]] = None


@router.get("", response_model=List[ProjectMetadata], summary="List Analysis Projects")
def list_projects() -> List[ProjectMetadata]:
    """Retrieve all available analysis projects."""
    return ProjectService.list_projects()


@router.get("/presets", summary="Get Standard Geotechnical Presets")
def get_presets() -> Dict[str, Any]:
    """List standardized physical geotechnical soil and root presets."""
    return {k: v.model_dump() for k, v in STANDARD_GEOTECHNICAL_PRESETS.items()}


@router.post("", response_model=ProjectMetadata, summary="Create New Project Workspace")
def create_project(req: CreateProjectRequest) -> ProjectMetadata:
    """Create a new user project for a custom study area and parameters."""
    return ProjectService.create_project(
        name=req.name,
        description=req.description,
        study_area_type=req.study_area_type,
        bounds=req.bounds,
        boundary_geojson=req.boundary_geojson,
        geotech_preset_id=req.geotech_preset_id,
    )


@router.get("/{project_id}", response_model=ProjectMetadata, summary="Get Project Details")
def get_project(project_id: str) -> ProjectMetadata:
    """Retrieve detailed project configuration and layer metadata."""
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )
    return project


@router.put("/{project_id}", response_model=ProjectMetadata, summary="Update Project Settings")
def update_project(project_id: str, req: UpdateProjectRequest) -> ProjectMetadata:
    """Update study area, geotechnical parameters, or scoring settings."""
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    if req.name is not None:
        project.name = req.name
    if req.description is not None:
        project.description = req.description
    if req.bounds is not None:
        project.bounds = req.bounds
    if req.boundary_geojson is not None:
        project.boundary_geojson = req.boundary_geojson
    if req.geotechnical_parameters is not None:
        project.geotechnical_parameters.update(req.geotechnical_parameters)
    if req.recommendation_settings is not None:
        project.recommendation_settings.update(req.recommendation_settings)

    return ProjectService.update_project(project)


@router.delete("/{project_id}", summary="Delete Project")
def delete_project(project_id: str) -> Dict[str, str]:
    """Delete a custom project workspace."""
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")
    if project.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete built-in benchmark projects.",
        )
    success = ProjectService.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete project.")
    return {"message": f"Project '{project_id}' deleted successfully."}


@router.post("/{project_id}/upload-vector", summary="Upload Vector Boundary or Exclusions")
async def upload_vector(
    project_id: str,
    file: UploadFile = File(...),
    purpose: str = Form("boundary"),  # "boundary" or "exclusion"
) -> Dict[str, Any]:
    """Upload and validate a study area vector file (.geojson, .json, .zip Shapefile, .gpkg)."""
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    proj_dir = PROJECTS_DIR / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    filename = file.filename or "upload.geojson"
    dest_path = proj_dir / f"{purpose}_{uuid.uuid4().hex[:6]}_{filename}"

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        report = parse_uploaded_study_area(dest_path)
    except Exception as err:
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to validate vector dataset: {str(err)}",
        )

    # Attach to project
    if purpose == "boundary":
        project.study_area_type = "uploaded_file"
        project.bounds = report["bounds"]
        project.boundary_geojson = report["geojson"]
        project.layers["boundary"] = {
            "path": str(dest_path),
            "format": report["format"],
            "original_crs": report["original_crs"],
            "reprojected": report["reprojected"],
            "feature_count": report["feature_count"],
            "area_approx_ha": report["area_approx_ha"],
            "status": "VALID_BOUNDARY",
        }
    else:
        project.layers["user_exclusions"] = {
            "path": str(dest_path),
            "format": report["format"],
            "original_crs": report["original_crs"],
            "feature_count": report["feature_count"],
            "status": "VALID_EXCLUSIONS",
        }

    ProjectService.update_project(project)

    return {
        "message": f"Successfully loaded and validated {purpose} vector layer.",
        "report": report,
    }


@router.post("/{project_id}/upload-raster", summary="Upload GeoTIFF Raster Layer")
async def upload_raster(
    project_id: str,
    file: UploadFile = File(...),
    layer_type: str = Form("dem"),  # dem, ndvi, red, nir
) -> Dict[str, Any]:
    """Upload and validate a GeoTIFF raster dataset (DEM, NDVI, Red, or NIR)."""
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    proj_dir = PROJECTS_DIR / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    filename = file.filename or f"{layer_type}.tif"
    dest_path = proj_dir / f"{layer_type}_{uuid.uuid4().hex[:6]}_{filename}"

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        val = validate_and_inspect_uploaded_raster(dest_path, expected_layer_type=layer_type)
        if not val["is_valid"]:
            if dest_path.exists():
                dest_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Raster validation failed: {'; '.join(val['errors'])}",
            )
    except HTTPException:
        raise
    except Exception as err:
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid GeoTIFF raster: {str(err)}",
        )

    # Attach layer to project
    project.layers[layer_type] = {
        "path": str(dest_path),
        "status": "USER_UPLOADED_LAYER",
        "description": f"User-uploaded {layer_type.upper()} raster ({val['width']}x{val['height']})",
        "validation": val,
    }

    # If DEM is uploaded, update project bounds to match raster bounds
    if layer_type == "dem":
        b = val["bounds"]
        project.bounds = {
            "minx": round(float(b["minx"]), 6),
            "miny": round(float(b["miny"]), 6),
            "maxx": round(float(b["maxx"]), 6),
            "maxy": round(float(b["maxy"]), 6),
        }

    ProjectService.update_project(project)

    return {
        "message": f"Successfully uploaded and validated {layer_type.upper()} raster.",
        "validation": val,
    }


@router.post("/{project_id}/process-terrain", summary="Process DEM into Slope & Aspect")
def process_project_terrain(project_id: str) -> Dict[str, Any]:
    """Calculate slope, aspect, and terrain statistics from project DEM."""
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    dem_entry = project.layers.get("dem")
    if not dem_entry or not dem_entry.get("path") or not Path(dem_entry["path"]).exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DEM raster not found in project. Upload a DEM GeoTIFF first.",
        )

    dem_path = Path(dem_entry["path"])
    res = process_dem_terrain(dem_path)

    # Attach slope and aspect to project
    project.layers["slope"] = {
        "path": res.slope_geotiff_path,
        "status": "DERIVED_GEOSPATIAL",
        "description": f"Derived slope raster from {dem_path.name}",
    }
    project.layers["aspect"] = {
        "path": res.aspect_geotiff_path,
        "status": "DERIVED_GEOSPATIAL",
        "description": f"Derived aspect raster from {dem_path.name}",
    }

    ProjectService.update_project(project)

    return {
        "message": "Terrain processing completed successfully.",
        "elevation_stats": res.elevation_stats.model_dump(),
        "slope_stats": res.slope_stats.model_dump(),
        "aspect_stats": res.aspect_stats.model_dump(),
        "slope_path": res.slope_geotiff_path,
        "aspect_path": res.aspect_geotiff_path,
        "preview_path": res.terrain_preview_png_path,
    }


@router.post("/{project_id}/process-geotechnical", summary="Process Slope into Geotechnical Rasters")
def process_project_geotechnical(project_id: str) -> Dict[str, Any]:
    """Generate baseline FS, reinforced FS, delta FS, and required cohesion rasters."""
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    slope_entry = project.layers.get("slope")
    if not slope_entry or not slope_entry.get("path") or not Path(slope_entry["path"]).exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slope raster not found in project. Run terrain processing first.",
        )

    slope_path = Path(slope_entry["path"])

    # Extract geotech parameters
    gp = project.geotechnical_parameters or {}
    soil_dict = gp.get("soil", {})
    root_dict = gp.get("root", {})
    target_fs = float(gp.get("target_fs", 1.3))

    soil = SoilParameters(
        c_prime_kpa=float(soil_dict.get("c_prime_kpa", 8.0)),
        phi_deg=float(soil_dict.get("phi_deg", 26.0)),
        gamma_kn_m3=float(soil_dict.get("gamma_kn_m3", 18.5)),
        depth_m=float(soil_dict.get("depth_m", 1.8)),
        m_water_table=float(soil_dict.get("m_water_table", 0.5)),
    )
    root = RootParameters(
        tensile_stress_kpa=float(root_dict.get("tensile_stress_kpa", 25000.0)),
        rar=float(root_dict.get("rar", 0.002)),
        k_factor=float(root_dict.get("k_factor", 1.2)),
    )

    try:
        geo_res = process_geotechnical_raster(
            slope_path=slope_path,
            soil=soil,
            root=root,
            fs_target=target_fs,
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Geotechnical raster analysis failed: {str(err)}",
        )

    # Attach geotechnical rasters to project
    geotech_layers = {
        "fs_baseline": geo_res.output_rasters.get("fs_baseline"),
        "fs_reinforced": geo_res.output_rasters.get("fs_reinforced"),
        "fs_delta": geo_res.output_rasters.get("fs_delta"),
        "required_cohesion": geo_res.output_rasters.get("required_cohesion"),
    }
    for k, v in geotech_layers.items():
        if v:
            project.layers[k] = {
                "path": v,
                "status": "ILLUSTRATIVE_SCENARIO" if gp.get("is_demo_parameters", False) else "DERIVED_GEOTECHNICAL",
                "description": f"Geotechnical {k} raster",
            }

    ProjectService.update_project(project)

    return {
        "message": "Geotechnical raster analysis completed successfully.",
        "run_id": geo_res.run_id,
        "delta_c_kpa": geo_res.root_cohesion_delta_c_kpa,
        "baseline_summary": geo_res.fs_baseline_summary.model_dump(),
        "reinforced_summary": geo_res.fs_reinforced_summary.model_dump(),
        "required_cohesion_summary": geo_res.required_cohesion_summary.model_dump(),
        "output_rasters": geo_res.output_rasters,
    }
