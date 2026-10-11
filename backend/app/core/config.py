"""TerraShield AI Backend Core Configuration."""

import os
from pathlib import Path
from pydantic import BaseModel


class Settings(BaseModel):
    PROJECT_NAME: str = "TerraShield AI"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    APP_MODE: str = os.getenv("TERRASHIELD_ENV", "demo")
    HOST: str = os.getenv("TERRASHIELD_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("TERRASHIELD_PORT", "8000"))

    # Directory Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    SAMPLE_DATA_PATH: Path = DATA_DIR / "sample" / "demo_parcels.geojson"
    UPLOAD_DIR: Path = DATA_DIR / "uploads"
    PROCESSED_DIR: Path = DATA_DIR / "processed"
    ARTIFACTS_DIR: Path = DATA_DIR / "artifacts"

    # Upload Constraints & Security
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_RASTER_EXTENSIONS: list[str] = [".tif", ".tiff"]
    ALLOWED_VECTOR_EXTENSIONS: list[str] = [".geojson", ".json"]

    # Supported scenarios
    SUPPORTED_SCENARIOS: list[str] = ["landslide_mitigation"]

    WARNING_NOTICE: str = (
        "Phase 1 demonstration: sample geometries and attributes are illustrative "
        "and are not verified environmental observations. Results are not validated "
        "geotechnical predictions or planting prescriptions."
    )
    PHASE2_NOTICE: str = (
        "Phase 2 Geospatial Data Engine: Terrain parameters (slope, aspect) and NDVI "
        "are physical geospatial features derived from valid raster inputs. "
        "Slope alone is an environmental factor, not a validated landslide prediction."
    )
    PROVENANCE_NOTICE: str = (
        "Synthetic sample dataset created deterministically for TerraShield AI Phase 1 "
        "pipeline validation. Real raster and vector inputs ingested via Phase 2 preserve "
        "source metadata and CRS provenance."
    )


settings = Settings()

# Ensure directories exist
for directory in [settings.UPLOAD_DIR, settings.PROCESSED_DIR, settings.ARTIFACTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
