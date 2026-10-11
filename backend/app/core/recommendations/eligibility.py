"""Rule-based eligibility and spatial exclusion engine for candidate parcels."""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from shapely.geometry import Polygon, shape
from shapely.strtree import STRtree


class EligibilityStatus(str, Enum):
    """Formal qualification status for a candidate planting parcel."""
    ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS = "ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS"
    EXCLUDED = "EXCLUDED"
    ELIGIBILITY_UNVERIFIED = "ELIGIBILITY_UNVERIFIED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ExclusionReason(str, Enum):
    """Specific reason justifying parcel exclusion or disqualification."""
    NONE = "NONE"
    INSUFFICIENT_TERRAIN_COVERAGE = "INSUFFICIENT_TERRAIN_COVERAGE"
    PROTECTED_AREA_INTERSECTION = "PROTECTED_AREA_INTERSECTION"
    USER_EXCLUSION_ZONE = "USER_EXCLUSION_ZONE"
    EXCESSIVE_CLIFF_SLOPE = "EXCESSIVE_CLIFF_SLOPE"
    EXISTING_DENSE_CANOPY = "EXISTING_DENSE_CANOPY"
    NEGLIGIBLE_PLANTABLE_AREA = "NEGLIGIBLE_PLANTABLE_AREA"


class EligibilityConfig:
    """Configurable threshold parameters for the eligibility engine."""

    def __init__(
        self,
        min_terrain_coverage_pct: float = 80.0,
        max_slope_deg: float = 45.0,
        min_slope_deg: float = 2.0,
        enable_ndvi_canopy_filter: bool = False,
        ndvi_canopy_threshold: float = 0.65,
        min_plantable_area_ha: float = 0.25,
        protected_areas_geojson: Optional[Dict[str, Any]] = None,
        user_exclusions_geojson: Optional[Dict[str, Any]] = None,
    ):
        self.min_terrain_coverage_pct = min_terrain_coverage_pct
        self.max_slope_deg = max_slope_deg
        self.min_slope_deg = min_slope_deg
        self.enable_ndvi_canopy_filter = enable_ndvi_canopy_filter
        self.ndvi_canopy_threshold = ndvi_canopy_threshold
        self.min_plantable_area_ha = min_plantable_area_ha
        self.has_official_protected_areas = protected_areas_geojson is not None
        self.protected_areas_tree: Optional[Tuple[STRtree, List[str]]] = None
        self.user_exclusions_tree: Optional[Tuple[STRtree, List[str]]] = None

        if protected_areas_geojson:
            self.protected_areas_tree = self._build_spatial_index(protected_areas_geojson)

        if user_exclusions_geojson:
            self.user_exclusions_tree = self._build_spatial_index(user_exclusions_geojson)

    def _build_spatial_index(self, geojson_data: Dict[str, Any]) -> Optional[Tuple[STRtree, List[str]]]:
        """Build a fast spatial index (STRtree) over polygon features."""
        feats = geojson_data.get("features", [])
        geoms = []
        names = []
        for f in feats:
            geom_dict = f.get("geometry")
            if geom_dict:
                try:
                    s_geom = shape(geom_dict)
                    if s_geom.is_valid and not s_geom.is_empty:
                        geoms.append(s_geom)
                        name = f.get("properties", {}).get("name") or f.get("id") or "Exclusion Zone"
                        names.append(str(name))
                except Exception:
                    continue
        if geoms:
            return STRtree(geoms), names
        return None


def evaluate_parcel_eligibility(
    parcel_poly: Polygon,
    parcel_total_area_ha: float,
    metrics: Dict[str, Any],
    config: EligibilityConfig,
) -> Tuple[EligibilityStatus, List[str], float, str]:
    """Evaluate candidate parcel against physical, statutory, and environmental constraints.

    Returns:
        Tuple of (status, exclusion_reasons, plantable_area_ha, protected_area_clearance_note)
    """
    exclusion_reasons: List[str] = []
    pa_note = (
        "Verified against supplied protected area layer"
        if config.has_official_protected_areas
        else "UNVERIFIED: Protected-area clearance unverified (no legal cadastral reserve dataset loaded)"
    )

    # 1. Data Sufficiency Check
    coverage_pct = metrics.get("terrain_coverage_pct")
    if coverage_pct is None or coverage_pct < config.min_terrain_coverage_pct:
        return (
            EligibilityStatus.INSUFFICIENT_DATA,
            [f"Insufficient terrain data coverage ({coverage_pct or 0.0}% < {config.min_terrain_coverage_pct}%)"],
            0.0,
            pa_note,
        )

    # 2. Severe Slope Cliff Exclusion
    slope_mean = metrics.get("slope_mean_deg") or 0.0
    slope_max = metrics.get("slope_max_deg") or 0.0
    frac_steep = metrics.get("fraction_steep_slope") or 0.0
    if slope_mean > config.max_slope_deg or (frac_steep > 0.60 and slope_max > 55.0):
        exclusion_reasons.append(
            f"Mean hillslope gradient ({slope_mean:.1f}°) exceeds vegetative stabilization limit ({config.max_slope_deg}°)"
        )

    # 3. Statutory Protected Area Intersection
    if config.protected_areas_tree:
        tree, names = config.protected_areas_tree
        indices = tree.query(parcel_poly)
        hit_names = []
        for idx in indices:
            pa_geom = tree.geometries[idx]
            if parcel_poly.intersects(pa_geom):
                hit_names.append(names[idx])
        if hit_names:
            exclusion_reasons.append(
                f"Intersects statutory ecological reserve: {', '.join(set(hit_names))}"
            )

    # 4. User Exclusion Zone Intersection
    if config.user_exclusions_tree:
        tree_u, names_u = config.user_exclusions_tree
        indices_u = tree_u.query(parcel_poly)
        hit_u = []
        for idx in indices_u:
            u_geom = tree_u.geometries[idx]
            if parcel_poly.intersects(u_geom):
                hit_u.append(names_u[idx])
        if hit_u:
            exclusion_reasons.append(
                f"Intersects user-configured exclusion zone: {', '.join(set(hit_u))}"
            )

    # 5. Canopy Masking & Plantable Area Calculation
    canopy_fraction = 0.0
    if config.enable_ndvi_canopy_filter:
        canopy_fraction = metrics.get("fraction_dense_canopy_proxy") or 0.0

    plantable_ha = max(0.0, parcel_total_area_ha * (1.0 - canopy_fraction))

    if config.enable_ndvi_canopy_filter and plantable_ha < config.min_plantable_area_ha:
        exclusion_reasons.append(
            f"Existing mature vegetation canopy proxy ({canopy_fraction*100:.1f}%) leaves insufficient plantable area "
            f"({plantable_ha:.2f} ha < {config.min_plantable_area_ha} ha)"
        )

    # Determine final status
    if exclusion_reasons:
        return (
            EligibilityStatus.EXCLUDED,
            exclusion_reasons,
            round(plantable_ha, 4),
            pa_note,
        )

    if not config.has_official_protected_areas:
        # Eligible under available environmental constraints, but protected areas unverified
        return (
            EligibilityStatus.ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS,
            [],
            round(plantable_ha, 4),
            pa_note,
        )

    return (
        EligibilityStatus.ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS,
        [],
        round(plantable_ha, 4),
        pa_note,
    )
