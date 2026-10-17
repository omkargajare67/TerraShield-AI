"""FastAPI routes for Real-World Landslide Case Study Library."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from backend.app.core.case_studies.comparison import compare_observed_inventory_with_model
from backend.app.core.case_studies.models import CaseStudy
from backend.app.core.case_studies.registry import CaseStudyRegistry
from backend.app.core.projects.project_models import ProjectMetadata
from backend.app.core.projects.project_service import ProjectService

router = APIRouter(prefix="/case-studies", tags=["Landslide Case Studies"])


class LaunchWorkspaceResponse(BaseModel):
    case_id: str
    project_id: str
    is_existing: bool
    project: ProjectMetadata
    message: str


class CompareRequest(BaseModel):
    run_id: Optional[str] = None
    parcels_geojson: Optional[Dict[str, Any]] = None
    concern_fs_threshold: float = 1.3


@router.get("", response_model=List[CaseStudy], summary="List Real-World Landslide Case Studies")
def list_case_studies(
    region: Optional[str] = Query(None, description="Filter by region (western_ghats, himalayas, nepal, offline_demo)"),
    readiness: Optional[str] = Query(None, description="Filter by readiness (READY_TO_ANALYZE, CACHED_ANALYSIS_AVAILABLE, AWAITING_ADDITIONAL_DATA)"),
) -> List[CaseStudy]:
    """Retrieve curated registry of real-world landslide disaster case studies."""
    return CaseStudyRegistry.list_all(region=region, readiness=readiness)


@router.get("/{case_id}", response_model=CaseStudy, summary="Get Case Study Details")
def get_case_study(case_id: str) -> CaseStudy:
    """Retrieve detailed scientific metadata, datasets, and provenance for a specific case study."""
    case = CaseStudyRegistry.get(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case study '{case_id}' not found in registry.",
        )
    return case


@router.get("/{case_id}/observed-inventory", summary="Get Observed Disaster Inventory GeoJSON")
def get_observed_inventory(case_id: str) -> Dict[str, Any]:
    """Retrieve GeoJSON features of observed historical landslide footprints, scarps, and runout zones."""
    case = CaseStudyRegistry.get(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case study '{case_id}' not found in registry.",
        )
    if not case.observed_landslide_inventory:
        return {
            "type": "FeatureCollection",
            "features": [],
            "properties": {"note": "No observed inventory available for this case study."},
        }
    return case.observed_landslide_inventory


@router.post("/{case_id}/launch-workspace", response_model=LaunchWorkspaceResponse, summary="Launch Isolated Analysis Workspace")
def launch_case_study_workspace(case_id: str) -> LaunchWorkspaceResponse:
    """Instantiate or reference an isolated Project Workspace for this case study.

    Does NOT overwrite active user projects. Reuses pre-computed benchmark workspace
    if available, or creates a new dedicated project workspace initialized with
    the case study's authoritative bounding box and geotechnical parameters.
    """
    case = CaseStudyRegistry.get(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case study '{case_id}' not found in registry.",
        )

    # 1. If an existing linked project is active and available, return it
    if case.linked_project_id:
        proj = ProjectService.get_project(case.linked_project_id)
        if proj:
            return LaunchWorkspaceResponse(
                case_id=case.id,
                project_id=proj.id,
                is_existing=True,
                project=proj,
                message=f"Connected to verified benchmark workspace '{proj.name}'."
            )

    # 2. Otherwise create a dedicated case workspace (e.g. proj_case_malin_2014)
    target_proj_id = f"proj_case_{case.id}"
    existing_proj = ProjectService.get_project(target_proj_id)
    if existing_proj:
        return LaunchWorkspaceResponse(
            case_id=case.id,
            project_id=existing_proj.id,
            is_existing=True,
            project=existing_proj,
            message=f"Loaded existing workspace for '{case.name}'."
        )

    # Create new isolated project workspace
    created = ProjectService.create_project(
        name=f"Case Study: {case.name}",
        description=case.short_description[:200],
        study_area_type="case_study_aoi",
        bounds=case.bounds,
        boundary_geojson=case.study_area_geojson,
        geotech_preset_id=case.suggested_geotech_preset,
        project_id=target_proj_id,
    )

    return LaunchWorkspaceResponse(
        case_id=case.id,
        project_id=created.id,
        is_existing=False,
        project=created,
        message=f"Initialized dedicated study workspace '{created.name}'."
    )


@router.post("/{case_id}/compare", summary="Compare Observed Disaster Features with Model Results")
def compare_case_study_results(case_id: str, req: CompareRequest) -> Dict[str, Any]:
    """Execute spatial intersection and co-location analysis between documented event features and model outputs."""
    case = CaseStudyRegistry.get(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case study '{case_id}' not found in registry.",
        )

    if not case.observed_landslide_inventory:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Case study '{case.name}' has no observed landslide inventory data to compare.",
        )

    # Resolve parcel GeoJSON
    parcels_geojson = req.parcels_geojson
    if not parcels_geojson and req.run_id:
        from backend.app.core.config import settings
        import json
        recs_dir = settings.PROCESSED_DIR / "recommendations"
        run_file = recs_dir / f"run_{req.run_id}_parcels.geojson"
        if run_file.exists():
            with open(run_file, "r", encoding="utf-8") as f:
                parcels_geojson = json.load(f)

    if not parcels_geojson:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either valid 'parcels_geojson' or a valid 'run_id' with available artifacts is required.",
        )

    comparison = compare_observed_inventory_with_model(
        observed_inventory=case.observed_landslide_inventory,
        model_parcels_geojson=parcels_geojson,
        concern_fs_threshold=req.concern_fs_threshold,
    )
    comparison["case_id"] = case.id
    comparison["case_name"] = case.name
    return comparison
