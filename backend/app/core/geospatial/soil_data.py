"""Soil data ingestion and validation module (Phase 2)."""

from typing import Any, Dict, List, Optional
from backend.app.schemas.geospatial import (
    SoilDataValidationRequest,
    SoilDataValidationResponse,
)

# Standard ISRIC SoilGrids Physical Properties
VALID_SOILGRIDS_PROPERTIES = {
    "clay": {"unit": "g/kg", "description": "Clay content (< 2 μm)"},
    "silt": {"unit": "g/kg", "description": "Silt content (2-50 μm)"},
    "sand": {"unit": "g/kg", "description": "Sand content (50-2000 μm)"},
    "bdod": {"unit": "cg/cm³", "description": "Bulk density of the fine earth fraction"},
    "soc": {"unit": "dg/kg", "description": "Soil organic carbon content"},
    "phh2o": {"unit": "pH*10", "description": "Soil pH in H2O"},
    "cfvo": {"unit": "cm³/dm³", "description": "Volumetric fraction of coarse fragments (> 2 mm)"},
    "soil_depth": {"unit": "cm", "description": "Depth to bedrock / plantable mantle"},
}

STANDARD_DEPTH_INTERVALS = ["0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm", "100-200cm", "0-30cm"]


def validate_soil_metadata(
    request: SoilDataValidationRequest,
) -> SoilDataValidationResponse:
    """Validate soil dataset metadata, checking against recognized SoilGrids properties,
    depth intervals, and tabular column integrity without inventing default values.
    """
    messages: List[str] = []
    is_valid = True

    prop_key = request.property_name.lower().strip()
    if prop_key not in VALID_SOILGRIDS_PROPERTIES:
        messages.append(
            f"Unrecognized soil property '{request.property_name}'. "
            f"Expected one of: {', '.join(sorted(VALID_SOILGRIDS_PROPERTIES.keys()))}."
        )
        is_valid = False
    else:
        expected_unit = VALID_SOILGRIDS_PROPERTIES[prop_key]["unit"]
        if request.units and request.units != expected_unit:
            messages.append(
                f"Supplied units '{request.units}' differ from standard standard SoilGrids units '{expected_unit}'."
            )

    if request.depth_interval and request.depth_interval not in STANDARD_DEPTH_INTERVALS:
        messages.append(
            f"Non-standard depth interval '{request.depth_interval}'. "
            f"Standard intervals: {', '.join(STANDARD_DEPTH_INTERVALS)}."
        )

    if request.tabular_columns:
        required_coords = {"latitude", "longitude", "x", "y", "lat", "lon"}
        col_set = {c.lower() for c in request.tabular_columns}
        if not (col_set & required_coords):
            messages.append("Tabular dataset is missing explicit spatial coordinate columns (e.g. lat/lon or x/y).")
            is_valid = False

    provenance: Dict[str, Any] = {
        "source": request.source,
        "property": request.property_name,
        "depth_interval": request.depth_interval or "unspecified",
        "units": request.units or VALID_SOILGRIDS_PROPERTIES.get(prop_key, {}).get("unit", "unknown"),
        "download_date": request.download_date or "unrecorded",
        "is_synthetic": False,
    }

    warning = (
        "Phase 2 performs soil data validation and preparation. "
        "Geotechnical slope-stability equations, soil shear strength, and root-reinforcement "
        "computations will be evaluated in Phase 3."
    )

    return SoilDataValidationResponse(
        status="validated" if is_valid else "invalid",
        is_valid=is_valid,
        source=request.source,
        property_name=request.property_name,
        depth_interval=request.depth_interval,
        units=request.units,
        provenance=provenance,
        messages=messages,
        warning=warning,
    )
