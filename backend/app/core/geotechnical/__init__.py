"""TerraShield AI Geotechnical Intelligence Engine.

Phase 3 core mathematical and raster computation modules:
- infinite_slope: Classical limit-equilibrium infinite slope stability solver
- root_cohesion: Wu-Waldron root reinforcement model (Wu et al. 1979, Waldron 1977)
- required_cohesion: Analytical solver for target Factor of Safety attainment
- tree_density: Calibrated vegetation stem density estimator
- raster_analysis: Spatial grid processing pipeline on real terrain slope rasters
- sensitivity: Deterministic one-at-a-time geotechnical parameter sensitivity sweeps
- models: Strongly typed Pydantic models for parameters and stress states
- parameter_validation: Physical range checks and validation constraints
- provenance: Audit trail and data-source categorization
"""

from backend.app.core.geotechnical.infinite_slope import (
    calculate_infinite_slope_array,
    calculate_infinite_slope_scalar,
)
from backend.app.core.geotechnical.models import (
    InfiniteSlopeResult,
    ReinforcedSlopeResult,
    RequiredCohesionResult,
    RootCohesionResult,
    RootParameters,
    SoilParameters,
    StressState,
    TreeDensityCalibration,
    TreeDensityResult,
    UnitTensileStress,
)
from backend.app.core.geotechnical.parameter_validation import (
    validate_root_parameters,
    validate_soil_parameters,
    validate_tree_density_calibration,
)
from backend.app.core.geotechnical.provenance import ParameterProvenance, ProvenanceType
from backend.app.core.geotechnical.raster_analysis import process_geotechnical_raster
from backend.app.core.geotechnical.required_cohesion import (
    calculate_required_cohesion_array,
    calculate_required_cohesion_scalar,
)
from backend.app.core.geotechnical.root_cohesion import (
    calculate_reinforced_slope_array,
    calculate_reinforced_slope_scalar,
    calculate_root_cohesion,
)
from backend.app.core.geotechnical.sensitivity import run_parameter_sensitivity
from backend.app.core.geotechnical.tree_density import estimate_tree_density

__all__ = [
    "calculate_infinite_slope_scalar",
    "calculate_infinite_slope_array",
    "calculate_root_cohesion",
    "calculate_reinforced_slope_scalar",
    "calculate_reinforced_slope_array",
    "calculate_required_cohesion_scalar",
    "calculate_required_cohesion_array",
    "estimate_tree_density",
    "run_parameter_sensitivity",
    "process_geotechnical_raster",
    "validate_soil_parameters",
    "validate_root_parameters",
    "validate_tree_density_calibration",
    "SoilParameters",
    "RootParameters",
    "TreeDensityCalibration",
    "StressState",
    "InfiniteSlopeResult",
    "RootCohesionResult",
    "ReinforcedSlopeResult",
    "RequiredCohesionResult",
    "TreeDensityResult",
    "UnitTensileStress",
    "ParameterProvenance",
    "ProvenanceType",
]
