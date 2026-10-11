"""Multi-criteria explainable priority scoring for candidate planting parcels."""

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class ScoringWeights(BaseModel):
    """Configurable weights for the multi-criteria prioritization model."""
    weight_geotechnical_need: float = Field(default=0.35, ge=0.0)
    weight_stability_gain: float = Field(default=0.30, ge=0.0)
    weight_plantable_area: float = Field(default=0.20, ge=0.0)
    weight_data_confidence: float = Field(default=0.15, ge=0.0)

    def normalized(self) -> "ScoringWeights":
        """Return weights strictly normalized to sum to 1.0."""
        total = (
            self.weight_geotechnical_need
            + self.weight_stability_gain
            + self.weight_plantable_area
            + self.weight_data_confidence
        )
        if total <= 1e-6:
            raise ValueError("At least one scoring component weight must be strictly positive.")
        return ScoringWeights(
            weight_geotechnical_need=self.weight_geotechnical_need / total,
            weight_stability_gain=self.weight_stability_gain / total,
            weight_plantable_area=self.weight_plantable_area / total,
            weight_data_confidence=self.weight_data_confidence / total,
        )


class ParcelScoreBreakdown(BaseModel):
    """Detailed transparent breakdown of a parcel's priority score components."""
    geotechnical_need_score: float = Field(..., ge=0.0, le=1.0)
    stability_gain_score: float = Field(..., ge=0.0, le=1.0)
    plantable_area_score: float = Field(..., ge=0.0, le=1.0)
    data_confidence_score: float = Field(..., ge=0.0, le=1.0)
    composite_score_normalized: float = Field(..., ge=0.0, le=1.0)
    priority_score_index: float = Field(..., ge=0.0, le=100.0)
    score_weights_used: ScoringWeights
    scoring_version: str = "v1.0-explainable-multi-criteria"


def calculate_parcel_score(
    metrics: Dict[str, Any],
    plantable_area_ha: float,
    weights: Optional[ScoringWeights] = None,
    fs_target: float = 1.3,
    max_area_ref_ha: float = 15.0,
    max_delta_fs_ref: float = 15.0,
) -> ParcelScoreBreakdown:
    """Calculate normalized component scores and composite priority index for an eligible parcel.

    Args:
        metrics: Zonal statistics extracted for the parcel.
        plantable_area_ha: Eligible plantable area in hectares.
        weights: Configurable component weights.
        fs_target: Benchmark Factor of Safety target.
        max_area_ref_ha: Normalization reference for plantable area.
        max_delta_fs_ref: Normalization reference for modeled stability gain.

    Returns:
        ParcelScoreBreakdown with individual and composite scores.
    """
    w = (weights or ScoringWeights()).normalized()

    # 1. Geotechnical Need Score (0.0 to 1.0)
    # Higher score when baseline FS is low and fraction below target is high
    fs_base = metrics.get("fs_baseline_mean")
    frac_subtarget = metrics.get("fraction_subtarget_fs") or 0.0

    if fs_base is not None:
        # Deficit below target: 0.7 FS represents critical instability, 1.3 represents target
        fs_deficit = max(0.0, min(1.0, (fs_target - fs_base) / max(0.1, (fs_target - 0.7))))
        need_score = max(0.0, min(1.0, 0.5 * fs_deficit + 0.5 * frac_subtarget))
    else:
        # Fallback to slope steepness as a proxy if geotechnical outputs are absent
        slope_mean = metrics.get("slope_mean_deg") or 0.0
        need_score = max(0.0, min(1.0, slope_mean / 35.0))

    # 2. Stability Gain Score (0.0 to 1.0)
    # Modeled Factor of Safety increase under root reinforcement
    fs_delta = metrics.get("fs_delta_mean")
    if fs_delta is not None:
        gain_score = max(0.0, min(1.0, fs_delta / max_delta_fs_ref))
    else:
        gain_score = 0.0

    # 3. Plantable Area Score (0.0 to 1.0)
    # Larger continuous plantable acreage enables higher reforestation payoff
    area_score = max(0.0, min(1.0, plantable_area_ha / max_area_ref_ha))

    # 4. Data Confidence Score (0.0 to 1.0)
    cov_terrain = (metrics.get("terrain_coverage_pct") or 0.0) / 100.0
    cov_ndvi = (metrics.get("ndvi_coverage_pct") or 100.0) / 100.0
    conf_score = max(0.0, min(1.0, (cov_terrain + cov_ndvi) * 0.5))

    # Composite Normalized Score
    composite = (
        w.weight_geotechnical_need * need_score
        + w.weight_stability_gain * gain_score
        + w.weight_plantable_area * area_score
        + w.weight_data_confidence * conf_score
    )

    priority_index = round(composite * 100.0, 2)

    return ParcelScoreBreakdown(
        geotechnical_need_score=round(need_score, 4),
        stability_gain_score=round(gain_score, 4),
        plantable_area_score=round(area_score, 4),
        data_confidence_score=round(conf_score, 4),
        composite_score_normalized=round(composite, 4),
        priority_score_index=priority_index,
        score_weights_used=w,
    )
