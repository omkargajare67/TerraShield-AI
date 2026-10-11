"""Data structures and representations for geotechnical modeling."""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.core.geotechnical.provenance import ParameterProvenance


class UnitTensileStress(str, Enum):
    """Supported input units for root tensile stress."""
    KPA = "kPa"
    MPA = "MPa"


class SoilParameters(BaseModel):
    """Soil physical and shear strength parameters for infinite slope evaluation."""
    c_prime_kpa: float = Field(
        ...,
        ge=0.0,
        description="Effective soil cohesion in kilopascals (kPa)",
    )
    gamma_kn_m3: float = Field(
        ...,
        gt=0.0,
        description="Total soil unit weight in kilonewtons per cubic meter (kN/m³)",
    )
    z_m: float = Field(
        ...,
        gt=0.0,
        description="Vertical depth to the planar failure surface in meters (m)",
    )
    phi_prime_deg: float = Field(
        ...,
        ge=0.0,
        lt=90.0,
        description="Effective internal friction angle in degrees (°)",
    )
    u_kpa: float = Field(
        default=0.0,
        ge=0.0,
        description="Pore-water pressure at the failure surface in kilopascals (kPa)",
    )
    pore_water_assumption: str = Field(
        default="Hydrostatic / user-specified pore-water pressure",
        description="Explicit description of the hydrologic pore pressure condition",
    )
    provenance: Optional[Dict[str, ParameterProvenance]] = Field(
        default=None,
        description="Provenance records for individual soil parameters",
    )


class RootParameters(BaseModel):
    """Vegetative root reinforcement parameters based on Wu-Waldron formulation."""
    tensile_stress_input: float = Field(
        ...,
        gt=0.0,
        description="Root tensile strength / stress value supplied by user",
    )
    tensile_stress_unit: UnitTensileStress = Field(
        default=UnitTensileStress.KPA,
        description="Input unit of tensile strength (kPa or MPa)",
    )
    root_area_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Root Area Ratio (RAR), dimensionless fraction of root cross-sectional area to soil area",
    )
    k_factor: float = Field(
        default=1.2,
        gt=0.0,
        description="Reinforcement coefficient K (default 1.2 per Wu et al. 1979 / Waldron 1977)",
    )
    species_label: Optional[str] = Field(
        None,
        description="Optional vegetative species or root morphology profile label",
    )
    provenance: Optional[Dict[str, ParameterProvenance]] = Field(
        default=None,
        description="Provenance records for root parameters",
    )

    @property
    def tensile_stress_kpa(self) -> float:
        """Tensile stress normalized internally to kilopascals (kPa)."""
        if self.tensile_stress_unit == UnitTensileStress.MPA:
            return self.tensile_stress_input * 1000.0
        return self.tensile_stress_input


class TreeDensityCalibration(BaseModel):
    """Optional empirical calibration relating stem density to Root Area Ratio (RAR)."""
    reference_stems_per_ha: float = Field(
        ...,
        gt=0.0,
        description="Measured stem density at reference condition (stems/hectare)",
    )
    rar_at_reference_density: float = Field(
        ...,
        gt=0.0,
        le=1.0,
        description="Measured root area ratio observed at reference stem density",
    )
    max_stems_per_ha: Optional[float] = Field(
        None,
        gt=0.0,
        description="Upper biological carrying capacity or maximum planting density (stems/hectare)",
    )
    assumed_relationship: str = Field(
        default="Linear proportionality within calibrated range: RAR ~ density",
        description="Mathematical relationship assumed between stem density and RAR",
    )
    provenance_note: Optional[str] = Field(
        None,
        description="Citation or field study establishing the calibration relationship",
    )


class StressState(BaseModel):
    """Stresses acting on the planar failure surface."""
    normal_stress_kpa: float = Field(..., description="Total normal stress σ_n (kPa)")
    effective_normal_stress_kpa: float = Field(..., description="Effective normal stress σ'_n = σ_n - u (kPa)")
    shear_stress_kpa: float = Field(..., description="Driving shear stress τ (kPa)")
    available_shear_strength_kpa: float = Field(..., description="Resisting shear strength τ_f (kPa)")


class InfiniteSlopeResult(BaseModel):
    """Result of baseline infinite slope Factor of Safety calculation."""
    beta_deg: float = Field(..., description="Slope angle in degrees")
    beta_rad: float = Field(..., description="Slope angle in radians")
    factor_of_safety: Optional[float] = Field(None, description="Baseline Factor of Safety (FS_0)")
    stresses: Optional[StressState] = None
    is_valid: bool = Field(..., description="Whether the calculation is physically valid")
    status: str = Field(..., description="Status code (e.g. VALID, FLAT_TERRAIN, NON_POSITIVE_EFFECTIVE_STRESS)")
    status_label: str = Field(..., description="Human-readable interpretation label")
    warnings: List[str] = Field(default_factory=list, description="Model validity warnings and notes")


class RootCohesionResult(BaseModel):
    """Result of Wu-Waldron additional root cohesion computation."""
    delta_c_kpa: float = Field(..., ge=0.0, description="Additional root cohesion ΔC (kPa)")
    tr_kpa: float = Field(..., description="Normalized root tensile stress Tr (kPa)")
    rar: float = Field(..., description="Root area ratio (dimensionless)")
    k_factor: float = Field(..., description="Reinforcement coefficient K")
    total_cohesion_kpa: float = Field(..., description="Total cohesion c' + ΔC (kPa)")
    species_label: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class ReinforcedSlopeResult(BaseModel):
    """Result of root-reinforced infinite slope stability evaluation."""
    beta_deg: float
    fs_baseline: Optional[float] = None
    delta_c_kpa: float
    fs_reinforced: Optional[float] = None
    delta_fs: Optional[float] = None
    fs_target: float = 1.3
    target_reached: bool = False
    is_valid: bool
    status: str
    status_label: str
    stresses: Optional[StressState] = None
    warnings: List[str] = Field(default_factory=list)


class RequiredCohesionResult(BaseModel):
    """Result of required additional root cohesion solver to achieve target Factor of Safety."""
    beta_deg: float
    fs_target: float
    fs_baseline: Optional[float] = None
    delta_c_required_kpa: Optional[float] = None
    verification_fs: Optional[float] = None
    verification_tolerance: float = 1e-4
    is_attainable: bool = True
    no_reinforcement_needed: bool = False
    required_rar: Optional[float] = None
    status: str
    status_label: str
    warnings: List[str] = Field(default_factory=list)


class TreeDensityResult(BaseModel):
    """Result of tree density estimation based on calibrated RAR relationship."""
    delta_c_required_kpa: float
    required_rar: float
    stems_per_ha_required: Optional[float] = None
    is_calibrated: bool = False
    is_feasible: bool = True
    max_stems_per_ha: Optional[float] = None
    status: str
    status_label: str
    warnings: List[str] = Field(default_factory=list)
