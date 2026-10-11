"""Demonstration data loading and validation module."""

import json
from pathlib import Path
from typing import Any, Dict

from backend.app.core.config import settings


def load_demo_geojson(custom_path: Path | None = None) -> Dict[str, Any]:
    """Load and parse the deterministic demonstration GeoJSON file.
    
    Returns the parsed GeoJSON dictionary with verified structure.
    Raises FileNotFoundError if the file cannot be located.
    """
    path = custom_path or settings.SAMPLE_DATA_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Demonstration data file not found at: {path}. "
            "Please ensure data/sample/demo_parcels.geojson exists."
        )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if data.get("type") != "FeatureCollection":
        raise ValueError("Invalid GeoJSON: Root must be a FeatureCollection.")

    return data
