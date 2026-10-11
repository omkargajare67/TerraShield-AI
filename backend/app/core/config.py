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
    
    # Path to sample GeoJSON data
    SAMPLE_DATA_PATH: Path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "sample" / "demo_parcels.geojson"

    # Supported scenarios for Phase 1 demonstration
    SUPPORTED_SCENARIOS: list[str] = ["landslide_mitigation"]

    WARNING_NOTICE: str = (
        "Phase 1 demonstration: sample geometries and attributes are illustrative "
        "and are not verified environmental observations. Results are not validated "
        "geotechnical predictions or planting prescriptions."
    )
    PROVENANCE_NOTICE: str = (
        "Synthetic sample dataset created deterministically for TerraShield AI Phase 1 "
        "pipeline validation. No live satellite (SRTM, Sentinel-2), soil (SoilGrids), "
        "or reserve (WDPA) feeds are ingested in this phase."
    )


settings = Settings()
