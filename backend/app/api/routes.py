"""TerraShield AI API v1 Route Handlers."""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status

from backend.app.core.analysis_service import run_demonstration_analysis
from backend.app.core.config import settings
from backend.app.core.demo_data import load_demo_geojson
from backend.app.schemas.analysis import AnalysisRequest, AnalysisResponse

router = APIRouter()


@router.get(
    "/parcels",
    response_model=Dict[str, Any],
    summary="Get Demonstration Candidate Parcels",
    description="Returns the deterministic Phase 1 sample parcels as a GeoJSON FeatureCollection.",
)
async def get_parcels() -> Dict[str, Any]:
    """Retrieve the demonstration candidate parcels for the study area."""
    try:
        return load_demo_geojson()
    except FileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sample dataset unavailable: {str(err)}",
        )


@router.post(
    "/analysis",
    response_model=AnalysisResponse,
    summary="Run Demonstration Prioritization Analysis",
    description="Calculates deterministic leverage scores and evaluates exclusions for candidate parcels.",
)
async def run_analysis(request: AnalysisRequest) -> AnalysisResponse:
    """Execute the Phase 1 demonstration analysis."""
    try:
        return run_demonstration_analysis(request)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )
    except FileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis input data unavailable: {str(err)}",
        )
