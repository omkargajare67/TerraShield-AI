"""Projects core module for multi-study area management."""

from backend.app.core.projects.project_models import (
    ProjectMetadata,
    GeotechnicalPreset,
    STANDARD_GEOTECHNICAL_PRESETS,
)
from backend.app.core.projects.project_service import ProjectService

__all__ = [
    "ProjectMetadata",
    "GeotechnicalPreset",
    "STANDARD_GEOTECHNICAL_PRESETS",
    "ProjectService",
]
