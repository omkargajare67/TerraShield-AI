"""Deterministic ranking engine and scientific leverage metric evaluation for candidate parcels."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.core.recommendations.eligibility import EligibilityStatus
from backend.app.core.recommendations.scoring import (
    MissingDataPolicy,
    NormalizationConfig,
    ParcelScoreBreakdown,
    ScoringWeights,
    calculate_parcel_score,
)


class EvaluatedParcel(BaseModel):
    """Complete evaluation record for a single candidate parcel."""
    parcel_id: str
    geometry: Dict[str, Any]
    total_area_ha: float
    plantable_area_ha: float
    eligibility_status: EligibilityStatus
    exclusion_reasons: List[str]
    protected_area_clearance_note: str
    metrics: Dict[str, Any]
    score_breakdown: Optional[ParcelScoreBreakdown] = None
    rank: Optional[int] = None

    # Leverage metrics
    has_calibrated_stem_density: bool = False
    estimated_required_stems: Optional[float] = None
    modeled_stability_gain_per_stem: Optional[float] = None
    leverage_metric_note: str = ""


class RankingResult(BaseModel):
    """Comprehensive ranking result containing eligible, excluded, and insufficient data parcels."""
    run_id: str
    total_parcels_evaluated: int
    eligible_count: int
    excluded_count: int
    insufficient_data_count: int
    ranked_eligible_parcels: List[EvaluatedParcel]
    excluded_parcels: List[EvaluatedParcel]
    insufficient_data_parcels: List[EvaluatedParcel]
    scoring_weights: ScoringWeights
    normalization_config: NormalizationConfig = Field(default_factory=NormalizationConfig)
    applied_missing_data_policy: str = MissingDataPolicy.RENORMALIZE_AVAILABLE.value
    missing_components_detected: List[str] = Field(default_factory=list)
    ranking_timestamp: str


def rank_candidate_parcels(
    evaluated_parcels: List[EvaluatedParcel],
    run_id: str,
    timestamp: str,
    scoring_weights: Optional[ScoringWeights] = None,
    normalization_config: Optional[NormalizationConfig] = None,
    missing_data_policy: MissingDataPolicy = MissingDataPolicy.RENORMALIZE_AVAILABLE,
    fs_target: float = 1.3,
) -> RankingResult:
    """Rank eligible candidate parcels deterministically using multi-criteria priority scores.

    Rules:
    1. Excluded parcels (EXCLUDED) and parcels lacking data (INSUFFICIENT_DATA) NEVER receive a rank.
    2. Only ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS parcels receive priority scores and ordinal ranks.
    3. Sorting is strictly deterministic:
       - priority_score_index (descending)
       - stability_gain_score (descending, if available)
       - plantable_area_ha (descending)
       - parcel_id (ascending string comparison)
    4. Leverage calculation:
       - Evaluates modeled_stability_gain_per_stem if calibrated tree density exists.
       - Discloses why true risk reduction leverage (delta R / N) cannot be computed.
    5. Normalization is strictly deterministic and consistent across all parcels in the run.
    """
    weights = (scoring_weights or ScoringWeights()).normalized()
    norm_cfg = normalization_config or NormalizationConfig(fs_target=fs_target)

    eligible_list: List[EvaluatedParcel] = []
    excluded_list: List[EvaluatedParcel] = []
    insufficient_list: List[EvaluatedParcel] = []
    all_missing_components: set = set()

    for p in evaluated_parcels:
        if p.eligibility_status == EligibilityStatus.ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS:
            # Compute score breakdown with explicit missing data policy and normalization config
            score = calculate_parcel_score(
                metrics=p.metrics,
                plantable_area_ha=p.plantable_area_ha,
                weights=weights,
                normalization_config=norm_cfg,
                missing_data_policy=missing_data_policy,
                fs_target=fs_target,
            )
            p.score_breakdown = score
            for c in score.missing_components:
                all_missing_components.add(c)

            # Evaluate leverage / stability gain per stem
            tree_density_mean = p.metrics.get("tree_density_mean_stems_ha")
            fs_delta_mean = p.metrics.get("fs_delta_mean")

            if tree_density_mean is not None and tree_density_mean > 0.0 and p.plantable_area_ha > 0.0:
                p.has_calibrated_stem_density = True
                total_stems = round(tree_density_mean * p.plantable_area_ha, 1)
                p.estimated_required_stems = total_stems
                if fs_delta_mean is not None and total_stems > 0:
                    gain_per_stem = fs_delta_mean / total_stems
                    p.modeled_stability_gain_per_stem = round(gain_per_stem, 6)
                    p.leverage_metric_note = (
                        f"Modeled stability gain per stem = {gain_per_stem:.6f} delta_FS/stem "
                        f"({fs_delta_mean:.2f} delta_FS across ~{total_stems:.0f} stems on {p.plantable_area_ha:.2f} ha). "
                        "NOTE: This is modeled mechanical stability index per stem, NOT empirical landslide risk reduction."
                    )
            else:
                p.has_calibrated_stem_density = False
                p.estimated_required_stems = None
                p.modeled_stability_gain_per_stem = None
                p.leverage_metric_note = (
                    "UNAVAILABLE: Calibrated root-density or stem-density benchmark not available for this parcel. "
                    "Original project leverage (delta_R / N) requires empirical landslide risk curve and calibrated silvicultural spacing."
                )

            eligible_list.append(p)

        elif p.eligibility_status == EligibilityStatus.EXCLUDED:
            p.score_breakdown = None
            p.rank = None
            p.leverage_metric_note = "UNAVAILABLE: Parcel disqualified from planting eligibility."
            excluded_list.append(p)

        elif p.eligibility_status == EligibilityStatus.INSUFFICIENT_DATA:
            p.score_breakdown = None
            p.rank = None
            p.leverage_metric_note = "UNAVAILABLE: Inadequate terrain raster data coverage."
            insufficient_list.append(p)

    # Deterministic sorting for eligible parcels
    # Sort key: (-priority_score_index, -stability_gain_score, -plantable_area_ha, parcel_id)
    def sort_key(item: EvaluatedParcel):
        sc = item.score_breakdown
        priority = sc.priority_score_index if sc else -1.0
        gain = sc.stability_gain_score if (sc and sc.stability_gain_score is not None) else -1.0
        area = item.plantable_area_ha
        return (-priority, -gain, -area, item.parcel_id)

    eligible_list.sort(key=sort_key)

    # Assign 1-indexed ranks
    for rank_idx, parcel in enumerate(eligible_list, start=1):
        parcel.rank = rank_idx

    return RankingResult(
        run_id=run_id,
        total_parcels_evaluated=len(evaluated_parcels),
        eligible_count=len(eligible_list),
        excluded_count=len(excluded_list),
        insufficient_data_count=len(insufficient_list),
        ranked_eligible_parcels=eligible_list,
        excluded_parcels=excluded_list,
        insufficient_data_parcels=insufficient_list,
        scoring_weights=weights,
        normalization_config=norm_cfg,
        applied_missing_data_policy=missing_data_policy.value,
        missing_components_detected=sorted(list(all_missing_components)),
        ranking_timestamp=timestamp,
    )
