"""Explainability engine generating human-readable narrative audits and factor breakdowns."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.core.recommendations.ranking import EvaluatedParcel
from backend.app.core.recommendations.provenance import RecommendationProvenance


class ParcelExplanation(BaseModel):
    """Detailed human-readable audit trail and component breakdown for a parcel."""
    parcel_id: str
    rank: Optional[int]
    priority_score_index: Optional[float]
    eligibility_summary: str
    exclusion_details: List[str]
    score_component_contributions: Dict[str, Optional[float]]
    primary_ranking_drivers: List[str]
    non_differentiating_contributors: List[str] = Field(default_factory=list)
    topographic_context: str
    geotechnical_context: str
    vegetation_context: str
    provenance_disclosures: List[str]
    leverage_metric_summary: str


def generate_parcel_explanation(
    parcel: EvaluatedParcel,
    provenance: Optional[RecommendationProvenance] = None,
    differentiating_components: Optional[List[str]] = None,
) -> ParcelExplanation:
    """Generate an explainable, fact-based narrative audit for an evaluated parcel."""
    m = parcel.metrics
    sc = parcel.score_breakdown

    # 1. Eligibility & Exclusion summary
    if parcel.rank is not None and sc is not None:
        elig_summary = (
            f"Ranked #{parcel.rank} with Priority Score {sc.priority_score_index:.1f}/100. "
            f"Qualified under currently active environmental constraints with {parcel.plantable_area_ha:.2f} ha plantable area "
            f"(Total area: {parcel.total_area_ha:.2f} ha)."
        )
    else:
        elig_summary = (
            f"Disqualified from ranking (Status: {parcel.eligibility_status.value}). "
            f"Plantable area: {parcel.plantable_area_ha:.2f} ha."
        )

    # 2. Score contributions
    contributions: Dict[str, Optional[float]] = {}
    drivers: List[str] = []

    if sc is not None:
        w = sc.score_weights_active

        if sc.geotechnical_need_score is not None:
            c_need = round(w.weight_geotechnical_need * sc.geotechnical_need_score * 100.0, 1)
            contributions["geotechnical_need_points"] = c_need
        else:
            c_need = None
            contributions["geotechnical_need_points"] = None

        if sc.stability_gain_score is not None:
            c_gain = round(w.weight_stability_gain * sc.stability_gain_score * 100.0, 1)
            contributions["stability_gain_points"] = c_gain
        else:
            c_gain = None
            contributions["stability_gain_points"] = None

        c_area = round(w.weight_plantable_area * sc.plantable_area_score * 100.0, 1)
        c_conf = round(w.weight_data_confidence * sc.data_confidence_score * 100.0, 1)

        contributions["plantable_area_points"] = c_area
        contributions["data_confidence_points"] = c_conf

        # Identify differentiating drivers vs baseline aggregate contributors
        diff_keys = set(differentiating_components) if differentiating_components is not None else {"stability_gain", "geotechnical_need"}

        diff_ranked = []
        non_diff_list: List[str] = []

        if c_need is not None:
            if "geotechnical_need" in diff_keys and c_need > 0.0:
                diff_ranked.append(("Geotechnical Stability Deficit", c_need))
            elif c_need > 0.0:
                non_diff_list.append(f"Geotechnical Stability Deficit: +{c_need:.1f} pts (baseline contributor)")

        if c_gain is not None:
            if "stability_gain" in diff_keys and c_gain > 0.0:
                diff_ranked.append(("Modeled Root Reinforcement Gain", c_gain))
            elif c_gain > 0.0:
                non_diff_list.append(f"Modeled Root Reinforcement Gain: +{c_gain:.1f} pts (baseline contributor)")

        if "plantable_area" in diff_keys and c_area > 0.0:
            diff_ranked.append(("Plantable Acreage Capacity", c_area))
        elif c_area > 0.0:
            non_diff_list.append(f"Plantable Acreage Capacity: +{c_area:.1f} pts (baseline aggregate contributor; uniform regular {parcel.plantable_area_ha:.1f} ha cells)")

        if "data_confidence" in diff_keys and c_conf > 0.0:
            diff_ranked.append(("Input Data Completeness", c_conf))
        elif c_conf > 0.0:
            non_diff_list.append(f"Input Data Completeness: +{c_conf:.1f} pts (baseline aggregate contributor; uniform across study grid)")

        diff_ranked.sort(key=lambda x: x[1], reverse=True)

        for name, pts in diff_ranked:
            pct = round(pts / max(0.1, sc.priority_score_index) * 100.0)
            drivers.append(f"{name}: +{pts:.1f} pts ({pct}% of total score)")

        if not drivers:
            drivers.append("Uniform Baseline (Non-Differentiating)")

    # 3. Topographic Context
    slope_mean = m.get("slope_mean_deg")
    slope_max = m.get("slope_max_deg")
    elev_mean = m.get("elevation_mean_m")
    topo_parts = []
    if slope_mean is not None:
        topo_parts.append(f"Mean slope: {slope_mean:.1f}°")
    if slope_max is not None:
        topo_parts.append(f"Max slope: {slope_max:.1f}°")
    if elev_mean is not None:
        topo_parts.append(f"Mean elevation: {elev_mean:.1f} m")
    cov_terrain = m.get("terrain_coverage_pct")
    if cov_terrain is not None:
        topo_parts.append(f"Valid DEM coverage: {cov_terrain:.1f}%")
    topo_context = ", ".join(topo_parts) if topo_parts else "Topographic data unavailable."

    # 4. Geotechnical Context
    fs_base = m.get("fs_baseline_mean")
    fs_delta = m.get("fs_delta_mean")
    req_c = m.get("required_cohesion_mean_kpa")
    subtarget = m.get("fraction_subtarget_fs")

    geo_parts = []
    if fs_base is not None:
        geo_parts.append(f"Mean baseline FS: {fs_base:.2f}")
    if fs_delta is not None:
        geo_parts.append(f"Modeled delta FS: +{fs_delta:.2f}")
    if req_c is not None and req_c > 0.0:
        geo_parts.append(f"Required root cohesion: {req_c:.2f} kPa")
    if subtarget is not None:
        geo_parts.append(f"Area below FS target (1.3): {subtarget * 100:.1f}%")
    geo_context = (
        "; ".join(geo_parts) + " (Phase 3 exploratory uniform scenario)"
        if geo_parts
        else "Geotechnical metrics unavailable (exploratory scenario not run or layer absent)."
    )

    # 5. Vegetation Context
    ndvi_mean = m.get("ndvi_mean")
    canopy_proxy = m.get("fraction_dense_canopy_proxy")
    veg_parts = []
    if ndvi_mean is not None:
        veg_parts.append(f"Sentinel-2 mean NDVI: {ndvi_mean:.3f}")
    if canopy_proxy is not None and canopy_proxy > 0:
        veg_parts.append(f"Estimated dense canopy proxy: {canopy_proxy * 100:.1f}%")
    veg_context = (
        "; ".join(veg_parts)
        if veg_parts
        else "Vegetation/NDVI metrics unavailable (Sentinel-2 layer absent)."
    )

    # 6. Provenance & Disclosures
    disclosures = [
        parcel.protected_area_clearance_note,
        "Geotechnical outputs derive from spatially uniform exploratory scenario parameters.",
        "Factor of Safety (FS) is a limit-equilibrium stability index, not measured failure probability.",
    ]
    if sc and sc.missing_components:
        disclosures.append(
            f"Missing Component Policy ({sc.missing_data_policy_applied}): The following layers were unavailable: {', '.join(sc.missing_components)}."
        )

    if provenance:
        disclosures.extend(provenance.scientific_disclosures[:2])

    # 7. Leverage summary
    leverage_summary = (
        parcel.leverage_metric_note
        if parcel.leverage_metric_note
        else "Leverage metric not evaluated for this parcel."
    )

    return ParcelExplanation(
        parcel_id=parcel.parcel_id,
        rank=parcel.rank,
        priority_score_index=sc.priority_score_index if sc else None,
        eligibility_summary=elig_summary,
        exclusion_details=parcel.exclusion_reasons,
        score_component_contributions=contributions,
        primary_ranking_drivers=drivers,
        non_differentiating_contributors=non_diff_list,
        topographic_context=topo_context,
        geotechnical_context=geo_context,
        vegetation_context=veg_context,
        provenance_disclosures=disclosures,
        leverage_metric_summary=leverage_summary,
    )
