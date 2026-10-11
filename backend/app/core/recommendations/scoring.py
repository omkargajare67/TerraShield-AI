"""Multi-criteria explainable priority scoring for candidate planting parcels."""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class MissingDataPolicy(str, Enum):
    """Policy applied when optional environmental or geotechnical metrics are missing across a run."""
    RENORMALIZE_AVAILABLE = "RENORMALIZE_AVAILABLE"  # Re-normalizes weights across available components
    ZERO_FILL = "ZERO_FILL"  # Treats unavailable components as zero
    BLOCK_UNAVAILABLE = "BLOCK_UNAVAILABLE"  # Disqualifies parcels with missing components from ranking


class NormalizationConfig(BaseModel):
    """Configurable normalization scale bounds for multi-criteria priority scoring."""
    fs_target: float = Field(default=1.3, ge=1.0, le=3.0, description="Stability benchmark Factor of Safety target")
    critical_fs: float = Field(default=0.7, ge=0.1, le=1.2, description="Critical limit-equilibrium failure FS threshold")
    max_delta_fs_ref: float = Field(default=15.0, gt=0.0, description="Divisor for modeled stability improvement (delta FS)")
    max_area_ref_ha: float = Field(default=15.0, gt=0.0, description="Divisor for plantable acreage in hectares")


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
    geotechnical_need_score: Optional[float] = None
    stability_gain_score: Optional[float] = None
    plantable_area_score: float = Field(..., ge=0.0, le=1.0)
    data_confidence_score: float = Field(..., ge=0.0, le=1.0)
    composite_score_normalized: float = Field(..., ge=0.0, le=1.0)
    priority_score_index: float = Field(..., ge=0.0, le=100.0)
    score_weights_configured: ScoringWeights
    score_weights_active: ScoringWeights
    missing_components: List[str] = Field(default_factory=list)
    missing_data_policy_applied: str = MissingDataPolicy.RENORMALIZE_AVAILABLE.value
    normalization_config_used: NormalizationConfig
    scoring_version: str = "v1.1-explainable-multi-criteria"


def calculate_parcel_score(
    metrics: Dict[str, Any],
    plantable_area_ha: float,
    weights: Optional[ScoringWeights] = None,
    normalization_config: Optional[NormalizationConfig] = None,
    missing_data_policy: MissingDataPolicy = MissingDataPolicy.RENORMALIZE_AVAILABLE,
    fs_target: Optional[float] = None,
    max_area_ref_ha: Optional[float] = None,
    max_delta_fs_ref: Optional[float] = None,
) -> ParcelScoreBreakdown:
    """Calculate normalized component scores and composite priority index for an eligible parcel.

    Supports configurable normalization references, explicit missing-data handling,
    and rigorous distinction between unavailable layers and true calculated zeroes.

    Args:
        metrics: Zonal statistics extracted for the parcel.
        plantable_area_ha: Eligible plantable area in hectares.
        weights: Configurable component weights.
        normalization_config: Structured normalization bounds.
        missing_data_policy: Policy for handling unavailable layers (default RENORMALIZE_AVAILABLE).
        fs_target: Backward-compatible scalar override for fs_target.
        max_area_ref_ha: Backward-compatible scalar override for max_area_ref_ha.
        max_delta_fs_ref: Backward-compatible scalar override for max_delta_fs_ref.

    Returns:
        ParcelScoreBreakdown with individual and composite scores.
    """
    w_cfg = (weights or ScoringWeights()).normalized()
    norm = normalization_config or NormalizationConfig()

    # Allow backwards-compatible keyword overrides if supplied
    if fs_target is not None:
        norm.fs_target = fs_target
    if max_area_ref_ha is not None:
        norm.max_area_ref_ha = max_area_ref_ha
    if max_delta_fs_ref is not None:
        norm.max_delta_fs_ref = max_delta_fs_ref

    missing_components: List[str] = []

    # 1. Geotechnical Need Score (0.0 to 1.0, or None if layer missing)
    fs_base = metrics.get("fs_baseline_mean")
    frac_subtarget = metrics.get("fraction_subtarget_fs")

    if fs_base is not None:
        fs_crit = norm.critical_fs
        fs_tgt = norm.fs_target
        # Deficit below target: critical_fs represents acute instability, fs_target represents benchmark
        denom = max(0.1, fs_tgt - fs_crit)
        fs_deficit = max(0.0, min(1.0, (fs_tgt - fs_base) / denom))
        sub_frac = frac_subtarget if frac_subtarget is not None else 0.0
        need_score: Optional[float] = max(0.0, min(1.0, 0.5 * fs_deficit + 0.5 * sub_frac))
    else:
        need_score = None
        missing_components.append("geotechnical_need")

    # 2. Stability Gain Score (0.0 to 1.0, or None if layer missing)
    fs_delta = metrics.get("fs_delta_mean")
    if fs_delta is not None:
        # Clamped to [0.0, 1.0] relative to configurable normalization reference
        gain_score: Optional[float] = max(0.0, min(1.0, fs_delta / norm.max_delta_fs_ref))
    else:
        gain_score = None
        missing_components.append("stability_gain")

    # 3. Plantable Area Score (0.0 to 1.0)
    area_score = max(0.0, min(1.0, plantable_area_ha / norm.max_area_ref_ha))

    # 4. Data Confidence Score (0.0 to 1.0)
    # Distinguish missing NDVI from real zero coverage
    cov_terrain = metrics.get("terrain_coverage_pct")
    cov_ndvi = metrics.get("ndvi_coverage_pct")

    if cov_terrain is not None and cov_ndvi is not None:
        conf_score = max(0.0, min(1.0, (cov_terrain / 100.0 + cov_ndvi / 100.0) * 0.5))
    elif cov_terrain is not None:
        # NDVI absent: evaluate confidence strictly on terrain coverage without assuming 100% NDVI
        conf_score = max(0.0, min(1.0, cov_terrain / 100.0))
        missing_components.append("ndvi_coverage")
    else:
        conf_score = 0.0
        missing_components.append("terrain_coverage")

    # 5. Composite Score Calculation under MissingDataPolicy
    active_need_w = w_cfg.weight_geotechnical_need
    active_gain_w = w_cfg.weight_stability_gain
    active_area_w = w_cfg.weight_plantable_area
    active_conf_w = w_cfg.weight_data_confidence

    if missing_data_policy == MissingDataPolicy.RENORMALIZE_AVAILABLE:
        # Zero out weights for missing components and renormalize remaining components
        if need_score is None:
            active_need_w = 0.0
        if gain_score is None:
            active_gain_w = 0.0

        active_sum = active_need_w + active_gain_w + active_area_w + active_conf_w
        if active_sum > 1e-6:
            active_need_w /= active_sum
            active_gain_w /= active_sum
            active_area_w /= active_sum
            active_conf_w /= active_sum
        else:
            active_need_w = active_gain_w = active_area_w = active_conf_w = 0.0

        val_need = need_score if need_score is not None else 0.0
        val_gain = gain_score if gain_score is not None else 0.0

        composite = (
            active_need_w * val_need
            + active_gain_w * val_gain
            + active_area_w * area_score
            + active_conf_w * conf_score
        )

    elif missing_data_policy == MissingDataPolicy.ZERO_FILL:
        # Treat missing component values as zero without renormalizing weights
        val_need = need_score if need_score is not None else 0.0
        val_gain = gain_score if gain_score is not None else 0.0
        composite = (
            active_need_w * val_need
            + active_gain_w * val_gain
            + active_area_w * area_score
            + active_conf_w * conf_score
        )

    elif missing_data_policy == MissingDataPolicy.BLOCK_UNAVAILABLE:
        # If any component is missing, block priority scoring
        if missing_components:
            composite = 0.0
            active_need_w = active_gain_w = active_area_w = active_conf_w = 0.0
        else:
            composite = (
                active_need_w * (need_score or 0.0)
                + active_gain_w * (gain_score or 0.0)
                + active_area_w * area_score
                + active_conf_w * conf_score
            )
    else:
        raise ValueError(f"Unknown missing data policy: {missing_data_policy}")

    priority_index = round(composite * 100.0, 2)

    active_weights_obj = ScoringWeights(
        weight_geotechnical_need=round(active_need_w, 4),
        weight_stability_gain=round(active_gain_w, 4),
        weight_plantable_area=round(active_area_w, 4),
        weight_data_confidence=round(active_conf_w, 4),
    )

    return ParcelScoreBreakdown(
        geotechnical_need_score=round(need_score, 4) if need_score is not None else None,
        stability_gain_score=round(gain_score, 4) if gain_score is not None else None,
        plantable_area_score=round(area_score, 4),
        data_confidence_score=round(conf_score, 4),
        composite_score_normalized=round(composite, 4),
        priority_score_index=priority_index,
        score_weights_configured=w_cfg,
        score_weights_active=active_weights_obj,
        missing_components=missing_components,
        missing_data_policy_applied=missing_data_policy.value,
        normalization_config_used=norm,
    )
