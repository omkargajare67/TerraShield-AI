"""Secure artifact storage and retrieval manager."""

import os
from pathlib import Path
from typing import Optional
from backend.app.core.config import settings


def get_safe_artifact_path(artifact_id: str) -> Optional[Path]:
    """Resolve and validate an artifact file path, preventing directory traversal.
    
    Returns the resolved Path if the file exists within ARTIFACTS_DIR, otherwise None.
    """
    # Sanitize artifact_id: remove path separators
    clean_id = os.path.basename(artifact_id)
    target_path = (settings.ARTIFACTS_DIR / clean_id).resolve()

    # Ensure path stays within ARTIFACTS_DIR
    try:
        target_path.relative_to(settings.ARTIFACTS_DIR.resolve())
    except ValueError:
        return None

    if target_path.exists() and target_path.is_file():
        return target_path
    return None
