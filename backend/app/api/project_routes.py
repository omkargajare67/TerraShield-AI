"""FastAPI routes for Project Workspace management, dataset uploads, and processing."""

import json
import shutil
import uuid
from datetime import datetime, timezone
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


# -------------------------------------------------------------------------
# Automatic Geospatial Data Acquisition & One-Click Analysis Endpoints
# (Must be registered BEFORE parameterized /{project_id} to avoid route masking)
# -------------------------------------------------------------------------

class ValidateAOIRequest(BaseModel):
    bounds: Optional[Dict[str, float]] = None
    boundary_geojson: Optional[Dict[str, Any]] = None


class AutoAnalyzeRequest(BaseModel):
    name: Optional[str] = None
    project_id: Optional[str] = None
    bounds: Optional[Dict[str, float]] = None
    boundary_geojson: Optional[Dict[str, Any]] = None
    geotech_preset_id: str = "wayanad_saprolite"
    cell_size_m: float = 250.0
    priority_preset: str = "balanced"
    async_job: bool = True


@router.post("/validate-aoi", summary="Validate Area of Interest Boundary & Metric Acreage")
@router.post("/validate-aoi/", include_in_schema=False)
def validate_study_area(req: ValidateAOIRequest) -> Dict[str, Any]:
    """Validate AOI geometry, topology, coordinate ranges, and metric geodesic area."""
    from backend.app.core.geospatial.acquisition import validate_aoi
    try:
        return validate_aoi(boundary_geojson=req.boundary_geojson, bounds=req.bounds)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )


@router.get("/auto-analyze", summary="Auto-Analyze Info")
@router.get("/auto-analyze/", include_in_schema=False)
def auto_analyze_info() -> Dict[str, Any]:
    """Information endpoint for automated location analysis."""
    return {
        "status": "ready",
        "methods_supported": ["POST"],
        "description": "Send a POST request with boundary_geojson or bounds to trigger automatic geospatial analysis.",
    }


@router.post("/auto-analyze", summary="One-Click Automatic Geospatial Acquisition & Analysis")
@router.post("/auto-analyze/", include_in_schema=False)
def auto_analyze_location(req: AutoAnalyzeRequest) -> Dict[str, Any]:
    """Discover, download, and analyze public geospatial data for a selected location.

    Supports both asynchronous background execution (with real-time progress polling)
    and synchronous execution.
    """
    import threading
    from backend.app.core.geospatial.acquisition import (
        ACTIVE_JOBS,
        run_auto_acquisition_pipeline,
        validate_aoi,
    )

    # Validate inputs first
    try:
        aoi_report = validate_aoi(boundary_geojson=req.boundary_geojson, bounds=req.bounds)
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    # Resolve or create project
    if req.project_id:
        proj = ProjectService.get_project(req.project_id)
        if not proj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{req.project_id}' not found.")
        target_project_id = req.project_id
    else:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        proj_name = req.name.strip() if req.name and req.name.strip() else f"Auto Analysis ({now_str})"
        created = ProjectService.create_project(
            name=proj_name,
            description="Automated analysis workspace with satellite and DEM data.",
            study_area_type="polygon_draw" if req.boundary_geojson else "bbox",
            bounds=aoi_report["bounds"],
            boundary_geojson=aoi_report["boundary_geojson"],
            geotech_preset_id=req.geotech_preset_id,
        )
        target_project_id = created.id

    if not req.async_job:
        # Run synchronously
        try:
            res = run_auto_acquisition_pipeline(
                project_id=target_project_id,
                boundary_geojson=aoi_report["boundary_geojson"],
                bounds=aoi_report["bounds"],
                cell_size_m=req.cell_size_m,
                priority_preset=req.priority_preset,
            )
            return res
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Automated analysis failed: {str(err)}",
            )

    # Asynchronous job with background progress tracking
    job_id = uuid.uuid4().hex[:12]
    ACTIVE_JOBS[job_id] = {
        "job_id": job_id,
        "status": "RUNNING",
        "stage_number": 1,
        "stage_title": "Validating selected area",
        "stage_message": "Verifying coordinates, topology, and study area size...",
        "project_id": target_project_id,
        "result": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    def _worker():
        def _prog_cb(step: int, title: str, msg: str):
            if job_id in ACTIVE_JOBS:
                ACTIVE_JOBS[job_id]["stage_number"] = step
                ACTIVE_JOBS[job_id]["stage_title"] = title
                ACTIVE_JOBS[job_id]["stage_message"] = msg

        try:
            res = run_auto_acquisition_pipeline(
                project_id=target_project_id,
                boundary_geojson=aoi_report["boundary_geojson"],
                bounds=aoi_report["bounds"],
                cell_size_m=req.cell_size_m,
                priority_preset=req.priority_preset,
                progress_callback=_prog_cb,
            )
            ACTIVE_JOBS[job_id]["status"] = "COMPLETED"
            ACTIVE_JOBS[job_id]["result"] = res
            ACTIVE_JOBS[job_id]["stage_number"] = 9
            ACTIVE_JOBS[job_id]["stage_title"] = "Analysis Completed"
            ACTIVE_JOBS[job_id]["stage_message"] = "Geospatial acquisition and parcel ranking completed successfully."
        except Exception as exc:
            ACTIVE_JOBS[job_id]["status"] = "FAILED"
            ACTIVE_JOBS[job_id]["error"] = str(exc)
            ACTIVE_JOBS[job_id]["stage_title"] = "Analysis Failed"
            ACTIVE_JOBS[job_id]["stage_message"] = str(exc)

    threading.Thread(target=_worker, daemon=True).start()

    return {
        "job_id": job_id,
        "status": "STARTED",
        "project_id": target_project_id,
        "area_ha": aoi_report["area_ha"],
        "bounds": aoi_report["bounds"],
        "message": "Automated geospatial acquisition and analysis job started.",
    }


@router.get("/auto-analyze/status/{job_id}", summary="Check Auto-Analyze Job Progress")
@router.get("/auto-analyze/status/{job_id}/", include_in_schema=False)
def get_auto_analyze_status(job_id: str) -> Dict[str, Any]:
    """Retrieve the current progress stage and result of an automated analysis job."""
    from backend.app.core.geospatial.acquisition import ACTIVE_JOBS
    job = ACTIVE_JOBS.get(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job '{job_id}' not found.",
        )
    return job


# -------------------------------------------------------------------------
# Parameterized Project Workspace Endpoints
# -------------------------------------------------------------------------

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

    slope_file = settings.ARTIFACTS_DIR / res.slope_raster_id
    aspect_file = settings.ARTIFACTS_DIR / res.aspect_raster_id

    # Attach slope and aspect to project
    project.layers["slope"] = {
        "path": str(slope_file),
        "status": "DERIVED_GEOSPATIAL",
        "description": f"Derived slope raster from {dem_path.name}",
    }
    project.layers["aspect"] = {
        "path": str(aspect_file),
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

    depth_val = float(soil_dict.get("depth_m", soil_dict.get("z_m", 1.8)))
    gamma_val = float(soil_dict.get("gamma_kn_m3", 18.5))
    m_ratio = float(soil_dict.get("m_water_table", 0.5))
    u_val = float(soil_dict.get("u_kpa", m_ratio * 9.81 * depth_val))

    soil = SoilParameters(
        c_prime_kpa=float(soil_dict.get("c_prime_kpa", 8.0)),
        phi_prime_deg=float(soil_dict.get("phi_deg", soil_dict.get("phi_prime_deg", 26.0))),
        gamma_kn_m3=gamma_val,
        z_m=depth_val,
        u_kpa=u_val,
    )
    root = RootParameters(
        tensile_stress_input=float(root_dict.get("tensile_stress_kpa", root_dict.get("tensile_stress_input", 25000.0))),
        root_area_ratio=float(root_dict.get("rar", root_dict.get("root_area_ratio", 0.002))),
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
    art_rasters = geo_res.get("artifacts", {}).get("rasters", {})
    for k in ["fs_baseline", "fs_reinforced", "fs_delta", "required_cohesion"]:
        fname = art_rasters.get(k)
        if fname:
            src_art = settings.ARTIFACTS_DIR / fname
            project.layers[k] = {
                "path": str(src_art),
                "status": "ILLUSTRATIVE_SCENARIO" if gp.get("is_demo_parameters", False) else "DERIVED_GEOTECHNICAL",
                "description": f"Geotechnical {k} raster",
            }

    ProjectService.update_project(project)

    stats = geo_res.get("statistics", {})
    return {
        "message": "Geotechnical raster analysis completed successfully.",
        "run_id": geo_res.get("run_id"),
        "delta_c_kpa": geo_res.get("scenario_assumptions", {}).get("root", {}).get("modeled_delta_c_kpa", 0.0),
        "baseline_summary": stats.get("baseline_fs", {}),
        "reinforced_summary": stats.get("reinforced_fs", {}),
        "required_cohesion_summary": stats.get("required_cohesion_kpa", {}),
        "output_rasters": art_rasters,
    }

