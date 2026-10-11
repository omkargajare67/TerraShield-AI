"""FastAPI endpoints for the Phase 2 Geospatial Data Engine."""

import shutil
import uuid
from pathlib import Path
from typing import Any, Dict
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from backend.app.core.config import settings
from backend.app.core.demo_data import load_demo_geojson
from backend.app.core.geospatial.artifacts import get_safe_artifact_path
from backend.app.core.geospatial.ndvi import process_sentinel2_ndvi
from backend.app.core.geospatial.raster_loader import inspect_geotiff
from backend.app.core.geospatial.soil_data import validate_soil_metadata
from backend.app.core.geospatial.terrain import process_dem_terrain
from backend.app.core.geospatial.vector_loader import (
    intersect_parcels_with_protected_areas,
    load_and_validate_vector_file,
)
from backend.app.schemas.geospatial import (
    GeospatialEngineStatus,
    NDVIResponse,
    ProtectedAreaIntersectionResponse,
    RasterMetadata,
    SoilDataValidationRequest,
    SoilDataValidationResponse,
    TerrainResponse,
    VectorValidationResponse,
)

router = APIRouter(prefix="/geospatial", tags=["Geospatial Engine"])


def save_upload_safely(upload_file: UploadFile, allowed_extensions: list[str]) -> Path:
    """Save an uploaded file safely into UPLOAD_DIR with size limit and extension check."""
    ext = Path(upload_file.filename or "").suffix.lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed: {', '.join(allowed_extensions)}",
        )

    unique_filename = f"{uuid.uuid4().hex[:10]}_{Path(upload_file.filename or 'file').name}"
    target_path = settings.UPLOAD_DIR / unique_filename

    total_bytes = 0
    with open(target_path, "wb") as buffer:
        while chunk := upload_file.file.read(1024 * 1024):  # 1MB chunks
            total_bytes += len(chunk)
            if total_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
                buffer.close()
                target_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds maximum upload size limit of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB.",
                )
            buffer.write(chunk)

    return target_path


@router.get(
    "/status",
    response_model=GeospatialEngineStatus,
    summary="Geospatial Engine Capability Status",
)
async def get_geospatial_status() -> GeospatialEngineStatus:
    """Query current capability, supported raster/vector formats, and available datasets."""
    return GeospatialEngineStatus(
        status="ready",
        engine_backend="Pure-Python Geospatial Engine (tifffile + shapely + numpy + scipy + matplotlib)",
        supported_raster_formats=["GeoTIFF (.tif, .tiff)"],
        supported_vector_formats=["GeoJSON (.geojson, .json)"],
        native_gdal_available=False,
        available_sample_datasets=["demo_parcels.geojson", "synthetic_demo_dem.tif"],
        intended_pilot_region=settings.PILOT_STUDY_AREA_NAME,
        pilot_bounds=settings.PILOT_STUDY_AREA_BOUNDS,
        demo_study_area=settings.DEMO_STUDY_AREA_NAME,
    )


@router.post(
    "/dem/inspect",
    response_model=RasterMetadata,
    summary="Inspect DEM Raster Metadata",
)
async def inspect_dem(file: UploadFile = File(...)) -> RasterMetadata:
    """Upload and inspect a Digital Elevation Model (DEM) GeoTIFF without modifying data."""
    saved_path = save_upload_safely(file, settings.ALLOWED_RASTER_EXTENSIONS)
    try:
        _, metadata = inspect_geotiff(saved_path)
        return metadata
    except Exception as err:
        saved_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.post(
    "/dem/terrain",
    response_model=TerrainResponse,
    summary="Compute Elevation, Slope, and Aspect from DEM",
)
async def analyze_dem_terrain(file: UploadFile = File(...)) -> TerrainResponse:
    """Process a DEM GeoTIFF: derive elevation statistics, slope in degrees, and aspect in azimuth."""
    saved_path = save_upload_safely(file, settings.ALLOWED_RASTER_EXTENSIONS)
    try:
        response = process_dem_terrain(saved_path)
        return response
    except Exception as err:
        saved_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.post(
    "/ndvi",
    response_model=NDVIResponse,
    summary="Compute Sentinel-2 NDVI from Red and NIR Bands",
)
async def compute_ndvi(
    red_file: UploadFile = File(...),
    nir_file: UploadFile = File(...),
    cloud_masked: bool = Form(default=False),
    radiometric_offset: float = Form(default=0.0),
) -> NDVIResponse:
    """Upload Sentinel-2 Red (B04) and NIR (B08) GeoTIFF bands to calculate NDVI."""
    red_path = save_upload_safely(red_file, settings.ALLOWED_RASTER_EXTENSIONS)
    nir_path = save_upload_safely(nir_file, settings.ALLOWED_RASTER_EXTENSIONS)
    try:
        return process_sentinel2_ndvi(
            red_path,
            nir_path,
            cloud_masked=cloud_masked,
            radiometric_offset=radiometric_offset,
        )
    except Exception as err:
        red_path.unlink(missing_ok=True)
        nir_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.post(
    "/soil/validate",
    response_model=SoilDataValidationResponse,
    summary="Validate Soil Dataset Metadata",
)
async def validate_soil(request: SoilDataValidationRequest) -> SoilDataValidationResponse:
    """Validate soil dataset metadata against ISRIC SoilGrids standard parameters."""
    return validate_soil_metadata(request)


@router.post(
    "/vectors/validate",
    response_model=VectorValidationResponse,
    summary="Validate Vector File (GeoJSON)",
)
async def validate_vector(file: UploadFile = File(...)) -> VectorValidationResponse:
    """Upload and validate vector polygon boundary data."""
    saved_path = save_upload_safely(file, settings.ALLOWED_VECTOR_EXTENSIONS)
    try:
        _, val_resp = load_and_validate_vector_file(saved_path)
        return val_resp
    except Exception as err:
        saved_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.post(
    "/vectors/intersections",
    response_model=ProtectedAreaIntersectionResponse,
    summary="Test Candidate Parcels against Protected Areas",
)
async def check_protected_area_intersections(
    file: UploadFile = File(...),
) -> ProtectedAreaIntersectionResponse:
    """Upload a protected area vector file and evaluate spatial intersections with candidate parcels."""
    saved_path = save_upload_safely(file, settings.ALLOWED_VECTOR_EXTENSIONS)
    try:
        pa_features, _ = load_and_validate_vector_file(saved_path)
        parcels_geojson = load_demo_geojson()
        return intersect_parcels_with_protected_areas(
            parcels_geojson, pa_features, protected_source_name=file.filename or "Uploaded Protected Area Layer"
        )
    except Exception as err:
        saved_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.get(
    "/artifacts/{artifact_id}",
    summary="Download Processed Geospatial Artifact",
)
async def download_artifact(artifact_id: str):
    """Safely retrieve a generated GeoTIFF raster or preview PNG image by its artifact identifier."""
    file_path = get_safe_artifact_path(artifact_id)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Geospatial artifact '{artifact_id}' not found or access denied.",
        )

    # Determine media type
    ext = file_path.suffix.lower()
    media_type = "image/png" if ext == ".png" else "image/tiff"
    return FileResponse(path=file_path, filename=file_path.name, media_type=media_type)
