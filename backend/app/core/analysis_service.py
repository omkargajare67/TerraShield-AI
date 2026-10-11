"""TerraShield AI Demonstration Analysis Service.

Performs deterministic leverage calculations and exclusion evaluations
on Phase 1 demonstration data.
"""

from typing import Any, Dict, List, Optional, Tuple
from backend.app.core.config import settings
from backend.app.core.demo_data import load_demo_geojson
from backend.app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    ParcelAnalysisResult,
    StudyAreaMetadata,
)


def calculate_leverage_score(
    delta_risk: Optional[float], tree_count: Optional[int]
) -> Optional[float]:
    """Calculate the demonstration leverage score: L = delta_risk / tree_count.
    
    Validates numerator and denominator:
    - Returns None if either input is None or non-numeric.
    - Explicitly rejects non-positive tree counts (<= 0) to avoid division by zero.
    - Explicitly rejects negative delta_risk.
    - Returns a deterministic rounded floating-point leverage score.
    """
    if delta_risk is None or tree_count is None:
        return None

    try:
        dr = float(delta_risk)
        tc = int(tree_count)
    except (ValueError, TypeError):
        return None

    if tc <= 0:
        return None

    if dr < 0.0:
        return None

    # Calculate L = ΔR / N
    score = dr / tc
    return round(score, 6)


def evaluate_parcel_eligibility(
    properties: Dict[str, Any], min_risk_threshold: float = 0.0
) -> Tuple[bool, Optional[str]]:
    """Determine whether a candidate parcel is eligible for planting intervention.
    
    Returns (is_eligible, exclusion_reason).
    Maintains and explains any exclusion instead of dropping the parcel.
    """
    # 1. Existing demonstration exclusion flag (e.g. protected reserve or bedrock)
    if properties.get("is_excluded", False):
        reason = properties.get(
            "exclusion_reason",
            "Excluded in demonstration data (statutory or physical constraint).",
        )
        return False, reason

    # 2. Check tree count validity
    tree_count = properties.get("demo_tree_count", 0)
    if tree_count is None or tree_count <= 0:
        return False, "Non-positive plantable tree count (N <= 0)."

    # 3. Minimum baseline risk threshold check
    baseline_risk = properties.get("demo_baseline_risk", 0.0)
    if baseline_risk < min_risk_threshold:
        return (
            False,
            f"Baseline risk ({baseline_risk:.2f}) is below specified threshold ({min_risk_threshold:.2f}).",
        )

    return True, None


def run_demonstration_analysis(
    request: AnalysisRequest, raw_geojson: Optional[Dict[str, Any]] = None
) -> AnalysisResponse:
    """Execute the demonstration prioritization analysis across candidate parcels.
    
    1. Validates the intervention scenario.
    2. Ingests the sample GeoJSON FeatureCollection.
    3. Evaluates exclusions and computes leverage scores: L = ΔR / N.
    4. Ranks eligible parcels in descending order of leverage score.
    5. Returns structured results with full provenance, study-area metadata, and warnings.
    """
    # Validate scenario
    if request.scenario not in settings.SUPPORTED_SCENARIOS:
        supported = ", ".join(settings.SUPPORTED_SCENARIOS)
        raise ValueError(
            f"Unsupported scenario '{request.scenario}'. "
            f"Phase 1 demonstration currently supports: {supported}."
        )

    geojson_data = raw_geojson or load_demo_geojson()
    features: List[Dict[str, Any]] = geojson_data.get("features", [])

    results: List[ParcelAnalysisResult] = []
    enriched_features: List[Dict[str, Any]] = []

    # First pass: evaluate eligibility and calculate raw leverage scores
    temp_parcels = []
    for feat in features:
        props = feat.get("properties", {})
        parcel_id = props.get("parcel_id", feat.get("id", "UNKNOWN"))
        name = props.get("name", "Unnamed Parcel")
        description = props.get("description", "")
        area_ha = float(props.get("area_hectares", 1.0))
        baseline_risk = float(props.get("demo_baseline_risk", 0.0))
        delta_risk = float(props.get("demo_delta_risk", 0.0))
        tree_count = int(props.get("demo_tree_count", 0))

        is_eligible, exclusion_reason = evaluate_parcel_eligibility(
            props, min_risk_threshold=request.min_risk_threshold or 0.0
        )

        leverage_score = None
        if is_eligible:
            leverage_score = calculate_leverage_score(delta_risk, tree_count)
            # If calculation failed (e.g. invalid inputs), mark as excluded
            if leverage_score is None:
                is_eligible = False
                exclusion_reason = "Unable to compute leverage score from provided inputs."

        temp_parcels.append(
            {
                "parcel_id": parcel_id,
                "name": name,
                "description": description,
                "area_hectares": area_ha,
                "demo_baseline_risk": baseline_risk,
                "demo_delta_risk": delta_risk,
                "demo_tree_count": tree_count,
                "is_excluded": not is_eligible,
                "exclusion_reason": exclusion_reason if not is_eligible else None,
                "demo_leverage_score": leverage_score,
                "geometry": feat.get("geometry", {}),
            }
        )

    # Second pass: rank eligible parcels by leverage score descending
    eligible_items = [p for p in temp_parcels if not p["is_excluded"] and p["demo_leverage_score"] is not None]
    eligible_items.sort(key=lambda p: p["demo_leverage_score"], reverse=True)

    rank_map: Dict[str, int] = {}
    for idx, item in enumerate(eligible_items, start=1):
        rank_map[item["parcel_id"]] = idx

    highest_score: Optional[float] = None
    highest_parcel_id: Optional[str] = None
    if eligible_items:
        highest_score = eligible_items[0]["demo_leverage_score"]
        highest_parcel_id = eligible_items[0]["parcel_id"]

    # Finalize parcel objects and enriched GeoJSON features
    for p in temp_parcels:
        rank = rank_map.get(p["parcel_id"])
        parcel_result = ParcelAnalysisResult(
            parcel_id=p["parcel_id"],
            name=p["name"],
            description=p["description"],
            area_hectares=p["area_hectares"],
            demo_baseline_risk=p["demo_baseline_risk"],
            demo_delta_risk=p["demo_delta_risk"],
            demo_tree_count=p["demo_tree_count"],
            is_excluded=p["is_excluded"],
            exclusion_reason=p["exclusion_reason"],
            demo_leverage_score=p["demo_leverage_score"],
            rank=rank,
            is_synthetic=True,
        )
        results.append(parcel_result)
        enriched_features.append(
            {
                "type": "Feature",
                "id": p["parcel_id"],
                "properties": parcel_result.model_dump(),
                "geometry": p["geometry"],
            }
        )

    # Sort results so highest priority (rank 1, 2, ...) comes first, followed by excluded parcels
    results.sort(key=lambda item: (item.is_excluded, item.rank if item.rank is not None else 9999))

    enriched_geojson = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset_name": "TerraShield AI Phase 1 Analysis Results",
            "study_area": "Cascade Foothills Demonstration Basin (Synthetic)",
            "scenario": request.scenario,
            "data_type": "Synthetic Demonstration Output",
            "is_synthetic": True,
            "provenance": settings.PROVENANCE_NOTICE,
            "warning": settings.WARNING_NOTICE,
        },
        "features": enriched_features,
    }

    study_area = StudyAreaMetadata(
        name="Cascade Foothills Demonstration Basin (Synthetic)",
        coordinates_center=[47.452, -121.780],
        crs="EPSG:4326",
        data_type="Synthetic Demonstration Parcels",
        is_synthetic=True,
    )

    eligible_count = len(eligible_items)
    excluded_count = len(temp_parcels) - eligible_count

    return AnalysisResponse(
        app_mode=settings.APP_MODE,
        scenario=request.scenario,
        study_area=study_area,
        status="completed",
        total_candidate_parcels=len(temp_parcels),
        eligible_parcels_count=eligible_count,
        excluded_parcels_count=excluded_count,
        highest_leverage_score=highest_score,
        highest_leverage_parcel_id=highest_parcel_id,
        parcels=results,
        geojson=enriched_geojson,
        provenance=settings.PROVENANCE_NOTICE,
        warning=settings.WARNING_NOTICE,
    )
