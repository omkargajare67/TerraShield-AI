"""Extensible interface and schema for curated native plant species recommendations."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CuratedSpeciesRecord(BaseModel):
    """Schema for a verified, evidence-based botanical species profile."""
    scientific_name: str
    common_name: str
    native_range: str
    elevation_min_m: float
    elevation_max_m: float
    soil_preferences: List[str]
    root_system_type: str = Field(..., description="Taproot, heart, plate, fibrous, etc.")
    mean_rooting_depth_m: Optional[float] = None
    mean_root_tensile_strength_mpa: Optional[float] = None
    mean_root_area_ratio_rar: Optional[float] = None
    slope_suitability_max_deg: float = 40.0
    ecological_role: str
    source_citation: str
    data_limitations: List[str]


class SpeciesRecommendationResult(BaseModel):
    """Result of species matching for a specific candidate parcel."""
    parcel_id: str
    status: str = Field(
        ...,
        description="'PENDING_CURATED_BOTANICAL_DATA' or 'MATCHED_CANDIDATE_SPECIES'",
    )
    disclaimer: str
    suitable_species: List[CuratedSpeciesRecord] = Field(default_factory=list)


class SpeciesDatabase:
    """Registry of verified regional botanical and root biotechnical profiles."""

    def __init__(self, species_records: Optional[List[CuratedSpeciesRecord]] = None):
        self.records: List[CuratedSpeciesRecord] = species_records or []

    def is_curated_data_available(self) -> bool:
        """Check if any verified botanical records are loaded."""
        return len(self.records) > 0

    def query_for_parcel(
        self,
        parcel_id: str,
        elevation_mean_m: Optional[float],
        slope_mean_deg: Optional[float],
    ) -> SpeciesRecommendationResult:
        """Query suitable native species for a parcel's elevation and slope conditions."""
        if not self.records:
            return SpeciesRecommendationResult(
                parcel_id=parcel_id,
                status="PENDING_CURATED_BOTANICAL_DATA",
                disclaimer=(
                    "SPECIES SELECTION PENDING: No curated Western Ghats botanical and root-biomechanics database loaded. "
                    "TerraShield AI strictly avoids fabricating species recommendations or synthetic root tensile parameters."
                ),
                suitable_species=[],
            )

        matches: List[CuratedSpeciesRecord] = []
        for sp in self.records:
            # Check elevation range
            if elevation_mean_m is not None:
                if not (sp.elevation_min_m <= elevation_mean_m <= sp.elevation_max_m):
                    continue
            # Check slope tolerance
            if slope_mean_deg is not None:
                if slope_mean_deg > sp.slope_suitability_max_deg:
                    continue
            matches.append(sp)

        return SpeciesRecommendationResult(
            parcel_id=parcel_id,
            status="MATCHED_CANDIDATE_SPECIES" if matches else "NO_SPECIES_MATCHED_CONDITIONS",
            disclaimer="Field verification by local forestry and botanic specialists required before procurement.",
            suitable_species=matches,
        )


# Global default database instance (unpopulated by default to maintain scientific integrity)
DEFAULT_SPECIES_DB = SpeciesDatabase([])
