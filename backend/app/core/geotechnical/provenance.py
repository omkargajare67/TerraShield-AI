"""Provenance and scientific metadata tracking for geotechnical parameters."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ProvenanceSourceType(str, Enum):
    """Scientific origin of a geotechnical input parameter."""
    LABORATORY_MEASUREMENT = "laboratory_measurement"
    FIELD_MEASUREMENT = "field_measurement"
    PUBLISHED_REFERENCE = "published_reference"
    USER_SCENARIO = "user_scenario"
    SYNTHETIC_FIXTURE = "synthetic_fixture"


ProvenanceType = ProvenanceSourceType


class ParameterProvenance(BaseModel):
    """Metadata tracking the origin, assumptions, and validity of an input parameter."""
    parameter_name: str = Field(..., description="Name of the parameter (e.g. c_prime, phi_prime)")
    value: float = Field(..., description="Numerical value supplied")
    unit: str = Field(..., description="Physical unit of the value (e.g. kPa, kN/m³, deg)")
    source_type: ProvenanceSourceType = Field(
        default=ProvenanceSourceType.USER_SCENARIO,
        description="Source classification of the parameter",
    )
    citation: Optional[str] = Field(
        None,
        description="Reference citation, lab test report ID, or field station identifier",
    )
    assumptions: Optional[str] = Field(
        None,
        description="Key physical assumptions (e.g., drained conditions, uniform profile)",
    )
    notes: Optional[str] = Field(
        None,
        description="Additional technical notes or calibration boundaries",
    )
