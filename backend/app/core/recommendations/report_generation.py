"""Export generation engine for GeoJSON, CSV, JSON summary, and HTML audit reports."""

import csv
import html
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from backend.app.core.recommendations.ranking import EvaluatedParcel, RankingResult
from backend.app.core.recommendations.explainability import generate_parcel_explanation
from backend.app.core.recommendations.provenance import RecommendationProvenance


def export_candidate_parcels_geojson(
    ranking_result: RankingResult,
    output_path: Path,
) -> Path:
    """Generate RFC 7946 compliant GeoJSON FeatureCollection of all candidate parcels."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    features = []
    # Combine eligible, excluded, and insufficient data parcels
    all_parcels = (
        ranking_result.ranked_eligible_parcels
        + ranking_result.excluded_parcels
        + ranking_result.insufficient_data_parcels
    )

    for p in all_parcels:
        m = p.metrics
        sc = p.score_breakdown
        props = {
            "parcel_id": p.parcel_id,
            "rank": p.rank,
            "priority_score_index": sc.priority_score_index if sc else None,
            "eligibility_status": p.eligibility_status.value,
            "total_area_ha": round(p.total_area_ha, 4),
            "plantable_area_ha": round(p.plantable_area_ha, 4),
            "exclusion_reasons": "; ".join(p.exclusion_reasons) if p.exclusion_reasons else "None",
            "slope_mean_deg": m.get("slope_mean_deg"),
            "slope_max_deg": m.get("slope_max_deg"),
            "elevation_mean_m": m.get("elevation_mean_m"),
            "fs_baseline_mean": m.get("fs_baseline_mean"),
            "fs_delta_mean": m.get("fs_delta_mean"),
            "required_cohesion_mean_kpa": m.get("required_cohesion_mean_kpa"),
            "ndvi_mean": m.get("ndvi_mean"),
            "terrain_coverage_pct": m.get("terrain_coverage_pct"),
            "modeled_stability_gain_per_stem": p.modeled_stability_gain_per_stem,
            "protected_area_clearance": p.protected_area_clearance_note,
        }
        features.append({
            "type": "Feature",
            "id": p.parcel_id,
            "geometry": p.geometry,
            "properties": props,
        })

    geojson_doc = {
        "type": "FeatureCollection",
        "name": f"terra_shield_recommendations_{ranking_result.run_id}",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "metadata": {
            "run_id": ranking_result.run_id,
            "total_parcels": ranking_result.total_parcels_evaluated,
            "eligible_parcels": ranking_result.eligible_count,
            "excluded_parcels": ranking_result.excluded_count,
            "insufficient_data_parcels": ranking_result.insufficient_data_count,
            "applied_missing_data_policy": ranking_result.applied_missing_data_policy,
            "missing_components_detected": ranking_result.missing_components_detected,
            "normalization_references": ranking_result.normalization_config.model_dump(),
        },
        "features": features,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson_doc, f, indent=2)

    return output_path


def export_parcel_metrics_csv(
    ranking_result: RankingResult,
    output_path: Path,
) -> Path:
    """Generate CSV tabular record of all evaluated parcels with raw zonal statistics."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_parcels = (
        ranking_result.ranked_eligible_parcels
        + ranking_result.excluded_parcels
        + ranking_result.insufficient_data_parcels
    )

    fieldnames = [
        "parcel_id",
        "rank",
        "eligibility_status",
        "priority_score_index",
        "total_area_ha",
        "plantable_area_ha",
        "exclusion_reasons",
        "terrain_coverage_pct",
        "elevation_mean_m",
        "elevation_min_m",
        "elevation_max_m",
        "slope_mean_deg",
        "slope_median_deg",
        "slope_max_deg",
        "fraction_steep_slope",
        "fs_baseline_mean",
        "fs_baseline_median",
        "fraction_unstable_fs",
        "fraction_subtarget_fs",
        "fs_reinforced_mean",
        "fs_reinforced_median",
        "fs_delta_mean",
        "required_cohesion_mean_kpa",
        "tree_density_mean_stems_ha",
        "ndvi_mean",
        "ndvi_coverage_pct",
        "fraction_dense_canopy_proxy",
        "modeled_stability_gain_per_stem",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in all_parcels:
            m = p.metrics
            sc = p.score_breakdown
            row = {
                "parcel_id": p.parcel_id,
                "rank": p.rank if p.rank is not None else "",
                "eligibility_status": p.eligibility_status.value,
                "priority_score_index": sc.priority_score_index if sc else "",
                "total_area_ha": round(p.total_area_ha, 4),
                "plantable_area_ha": round(p.plantable_area_ha, 4),
                "exclusion_reasons": "; ".join(p.exclusion_reasons) if p.exclusion_reasons else "",
                "terrain_coverage_pct": m.get("terrain_coverage_pct", "") if m.get("terrain_coverage_pct") is not None else "",
                "elevation_mean_m": m.get("elevation_mean_m", "") if m.get("elevation_mean_m") is not None else "",
                "elevation_min_m": m.get("elevation_min_m", "") if m.get("elevation_min_m") is not None else "",
                "elevation_max_m": m.get("elevation_max_m", "") if m.get("elevation_max_m") is not None else "",
                "slope_mean_deg": m.get("slope_mean_deg", "") if m.get("slope_mean_deg") is not None else "",
                "slope_median_deg": m.get("slope_median_deg", "") if m.get("slope_median_deg") is not None else "",
                "slope_max_deg": m.get("slope_max_deg", "") if m.get("slope_max_deg") is not None else "",
                "fraction_steep_slope": m.get("fraction_steep_slope", "") if m.get("fraction_steep_slope") is not None else "",
                "fs_baseline_mean": m.get("fs_baseline_mean", "") if m.get("fs_baseline_mean") is not None else "",
                "fs_baseline_median": m.get("fs_baseline_median", "") if m.get("fs_baseline_median") is not None else "",
                "fraction_unstable_fs": m.get("fraction_unstable_fs", "") if m.get("fraction_unstable_fs") is not None else "",
                "fraction_subtarget_fs": m.get("fraction_subtarget_fs", "") if m.get("fraction_subtarget_fs") is not None else "",
                "fs_reinforced_mean": m.get("fs_reinforced_mean", "") if m.get("fs_reinforced_mean") is not None else "",
                "fs_reinforced_median": m.get("fs_reinforced_median", "") if m.get("fs_reinforced_median") is not None else "",
                "fs_delta_mean": m.get("fs_delta_mean", "") if m.get("fs_delta_mean") is not None else "",
                "required_cohesion_mean_kpa": m.get("required_cohesion_mean_kpa", "") if m.get("required_cohesion_mean_kpa") is not None else "",
                "tree_density_mean_stems_ha": m.get("tree_density_mean_stems_ha", "") if m.get("tree_density_mean_stems_ha") is not None else "",
                "ndvi_mean": m.get("ndvi_mean", "") if m.get("ndvi_mean") is not None else "",
                "ndvi_coverage_pct": m.get("ndvi_coverage_pct", "") if m.get("ndvi_coverage_pct") is not None else "",
                "fraction_dense_canopy_proxy": m.get("fraction_dense_canopy_proxy", "") if m.get("fraction_dense_canopy_proxy") is not None else "",
                "modeled_stability_gain_per_stem": p.modeled_stability_gain_per_stem if p.modeled_stability_gain_per_stem is not None else "",
            }
            writer.writerow(row)

    return output_path


def export_parcel_rankings_csv(
    ranking_result: RankingResult,
    output_path: Path,
) -> Path:
    """Generate CSV of ranked eligible parcels with multi-criteria component scores."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "rank",
        "parcel_id",
        "priority_score_index",
        "geotechnical_need_score",
        "stability_gain_score",
        "plantable_area_score",
        "data_confidence_score",
        "plantable_area_ha",
        "total_area_ha",
        "slope_mean_deg",
        "fs_baseline_mean",
        "fs_delta_mean",
        "modeled_stability_gain_per_stem",
        "estimated_required_stems",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in ranking_result.ranked_eligible_parcels:
            sc = p.score_breakdown
            if not sc:
                continue
            row = {
                "rank": p.rank,
                "parcel_id": p.parcel_id,
                "priority_score_index": sc.priority_score_index,
                "geotechnical_need_score": sc.geotechnical_need_score if sc.geotechnical_need_score is not None else "",
                "stability_gain_score": sc.stability_gain_score if sc.stability_gain_score is not None else "",
                "plantable_area_score": sc.plantable_area_score,
                "data_confidence_score": sc.data_confidence_score,
                "plantable_area_ha": round(p.plantable_area_ha, 4),
                "total_area_ha": round(p.total_area_ha, 4),
                "slope_mean_deg": p.metrics.get("slope_mean_deg", "") if p.metrics.get("slope_mean_deg") is not None else "",
                "fs_baseline_mean": p.metrics.get("fs_baseline_mean", "") if p.metrics.get("fs_baseline_mean") is not None else "",
                "fs_delta_mean": p.metrics.get("fs_delta_mean", "") if p.metrics.get("fs_delta_mean") is not None else "",
                "modeled_stability_gain_per_stem": p.modeled_stability_gain_per_stem if p.modeled_stability_gain_per_stem is not None else "",
                "estimated_required_stems": p.estimated_required_stems if p.estimated_required_stems is not None else "",
            }
            writer.writerow(row)

    return output_path


def export_recommendation_summary_json(
    ranking_result: RankingResult,
    provenance: RecommendationProvenance,
    output_path: Path,
) -> Path:
    """Generate comprehensive analysis summary JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    top_parcels = []
    for p in ranking_result.ranked_eligible_parcels[:10]:
        sc = p.score_breakdown
        top_parcels.append({
            "rank": p.rank,
            "parcel_id": p.parcel_id,
            "priority_score_index": sc.priority_score_index if sc else 0.0,
            "plantable_area_ha": round(p.plantable_area_ha, 2),
            "slope_mean_deg": p.metrics.get("slope_mean_deg"),
            "fs_baseline_mean": p.metrics.get("fs_baseline_mean"),
            "fs_delta_mean": p.metrics.get("fs_delta_mean"),
        })

    summary_doc = {
        "run_id": ranking_result.run_id,
        "timestamp": ranking_result.ranking_timestamp,
        "study_area_crs": provenance.study_area_crs,
        "metrics_and_scoring": {
            "scoring_model_version": "v1.1-explainable-multi-criteria",
            "weights_configured": ranking_result.scoring_weights.model_dump(),
            "applied_missing_data_policy": ranking_result.applied_missing_data_policy,
            "missing_components_detected": ranking_result.missing_components_detected,
            "is_discriminative": ranking_result.is_discriminative,
            "differentiation_warning": ranking_result.differentiation_warning,
            "differentiating_components": ranking_result.differentiating_components,
            "constant_components": ranking_result.constant_components,
            "normalization_references": ranking_result.normalization_config.model_dump(),
        },
        "parcel_inventory": {
            "total_evaluated": ranking_result.total_parcels_evaluated,
            "eligible_count": ranking_result.eligible_count,
            "excluded_count": ranking_result.excluded_count,
            "insufficient_data_count": ranking_result.insufficient_data_count,
            "total_plantable_area_ha": round(
                sum(p.plantable_area_ha for p in ranking_result.ranked_eligible_parcels), 2
            ),
        },
        "top_10_recommendations": top_parcels,
        "provenance_and_integrity": {
            "dem_verified_source": "NASA SRTM NASADEM Global 1 Arc-Second V001 (NASADEM_HGT_n11e076)",
            "geotechnical_is_illustrative": provenance.geotechnical_is_illustrative,
            "geotechnical_scenario_note": provenance.geotechnical_scenario_note,
            "protected_area_verification_status": provenance.protected_area_verification_status,
            "disclosures": provenance.scientific_disclosures,
        },
        "leverage_metric_status": (
            "Modeled stability gain per stem (delta_FS / N) evaluated for parcels with calibrated tree density. "
            "True empirical risk reduction leverage (delta_R / N) is unavailable without calibrated failure probability curve."
        ),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary_doc, f, indent=2)

    return output_path


def export_recommendation_report_html(
    ranking_result: RankingResult,
    provenance: RecommendationProvenance,
    output_path: Path,
) -> Path:
    """Generate a clean, styled HTML audit report for decision-makers."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    top_parcels = ranking_result.ranked_eligible_parcels[:15]
    total_plantable_ha = sum(p.plantable_area_ha for p in ranking_result.ranked_eligible_parcels)

    rows_html = []
    for p in top_parcels:
        sc = p.score_breakdown
        exp = generate_parcel_explanation(
            p,
            provenance,
            differentiating_components=ranking_result.differentiating_components,
        )
        m = p.metrics
        base_fs_val = f"{m.get('fs_baseline_mean'):.2f}" if m.get('fs_baseline_mean') is not None else "N/A"
        gain_val = f"+{m.get('fs_delta_mean'):.2f}" if m.get('fs_delta_mean') is not None else "N/A"
        rank_label = f"#{p.rank}" if p.rank is not None else "Tied"
        primary_driver = exp.primary_ranking_drivers[0] if exp.primary_ranking_drivers else "N/A"

        safe_rank_label = html.escape(str(rank_label))
        safe_parcel_id = html.escape(str(p.parcel_id))
        safe_driver = html.escape(str(primary_driver))

        rows_html.append(f"""
        <tr>
            <td style="font-weight: 700; color: #10b981;">{safe_rank_label}</td>
            <td style="font-family: monospace; font-weight: 600;">{safe_parcel_id}</td>
            <td style="font-weight: 700; color: #0284c7;">{sc.priority_score_index:.1f}</td>
            <td>{p.plantable_area_ha:.2f} ha</td>
            <td>{m.get('slope_mean_deg', 0.0):.1f}°</td>
            <td>{base_fs_val}</td>
            <td style="color: #10b981; font-weight: 600;">{gain_val}</td>
            <td style="font-size: 0.85rem; color: #4b5563;">{safe_driver}</td>
        </tr>
        """)

    non_diff_banner = ""
    if not ranking_result.is_discriminative:
        safe_warning = html.escape(str(ranking_result.differentiation_warning or ""))
        non_diff_banner = f"""
        <div style="background-color: #fff3cd; border: 2px solid #ffc107; color: #856404; padding: 1.25rem; border-radius: 8px; margin-bottom: 2rem;">
            <h3 style="margin-top: 0; color: #856404;">⚠️ Non-Discriminative Ranking Notice</h3>
            <p style="margin-bottom: 0;">{safe_warning}</p>
        </div>
        """

    disclosures_html = "".join([f"<li>{html.escape(str(d))}</li>" for d in provenance.scientific_disclosures])
    norm = ranking_result.normalization_config

    missing_info = (
        f"Missing components detected: {', '.join(ranking_result.missing_components_detected)}"
        if ranking_result.missing_components_detected
        else "All input layers verified and active."
    )
    safe_missing_info = html.escape(str(missing_info))
    safe_run_id = html.escape(str(ranking_result.run_id))
    safe_timestamp = html.escape(str(ranking_result.ranking_timestamp))
    safe_geo_note = html.escape(str(provenance.geotechnical_scenario_note))
    safe_pa_status = html.escape(str(provenance.protected_area_verification_status))
    safe_policy = html.escape(str(ranking_result.applied_missing_data_policy))

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TerraShield AI - Phase 4 Spatial Recommendation Audit Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #1f2937;
            background-color: #f9fafb;
            margin: 0;
            padding: 2rem;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: #ffffff;
            padding: 2.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 1.5rem;
            margin-bottom: 2rem;
        }}
        h1 {{
            color: #0f172a;
            margin: 0 0 0.5rem 0;
            font-size: 1.875rem;
        }}
        .badge {{
            display: inline-block;
            background: #e0f2fe;
            color: #0369a1;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 600;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }}
        .stat-card {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 1.25rem;
        }}
        .stat-val {{
            font-size: 1.75rem;
            font-weight: 700;
            color: #0f172a;
        }}
        .stat-lbl {{
            font-size: 0.875rem;
            color: #64748b;
            text-transform: uppercase;
            font-weight: 600;
        }}
        .alert {{
            background: #fffbeb;
            border-left: 4px solid #f59e0b;
            padding: 1rem 1.25rem;
            border-radius: 6px;
            margin-bottom: 2rem;
            font-size: 0.95rem;
            color: #92400e;
        }}
        .meta-card {{
            background: #f1f5f9;
            border: 1px solid #cbd5e1;
            padding: 1rem;
            border-radius: 6px;
            margin-bottom: 2rem;
            font-size: 0.9rem;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 2.5rem;
        }}
        th, td {{
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }}
        th {{
            background: #f8fafc;
            font-size: 0.8rem;
            text-transform: uppercase;
            color: #475569;
            letter-spacing: 0.05em;
        }}
        ul {{
            padding-left: 1.25rem;
        }}
        li {{
            margin-bottom: 0.5rem;
        }}
        .footer {{
            margin-top: 3rem;
            border-top: 1px solid #e5e7eb;
            padding-top: 1.5rem;
            font-size: 0.875rem;
            color: #6b7280;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="badge">Phase 5 Integrated Audit</span>
            <h1>TerraShield AI — Spatial Planting Recommendation Report</h1>
            <p style="color: #64748b; margin: 0;">Run ID: <code>{safe_run_id}</code> | Generated: {safe_timestamp}</p>
        </div>

        {non_diff_banner}

        <div class="alert">
            <strong>⚠️ Scientific Integrity & Provenance Disclosure:</strong><br>
            • <strong>Verified DEM Source:</strong> NASA SRTM NASADEM Global 1 Arc-Second V001 (NASADEM_HGT_n11e076, SHA256: 680aa3cb46f4b7d148b2d62224ff8f8daa9591dcee5921d46c0f8c4c8a5ca2b6).<br>
            • <strong>Geotechnical Model:</strong> {safe_geo_note}<br>
            • <em>Protected Area Clearance:</em> {safe_pa_status}
        </div>

        <div class="meta-card">
            <strong>⚙️ Prioritization Methodology & Normalization Settings:</strong><br>
            • <strong>Missing Data Policy:</strong> <code>{safe_policy}</code> ({safe_missing_info})<br>
            • <strong>Configured Normalization Divisors:</strong> Modeled Stability Gain Divisor = <code>{norm.max_delta_fs_ref} ΔFS</code> | Plantable Area Divisor = <code>{norm.max_area_ref_ha} ha</code> | Benchmark FS Target = <code>{norm.fs_target}</code>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-val">{ranking_result.total_parcels_evaluated}</div>
                <div class="stat-lbl">Total Candidate Parcels</div>
            </div>
            <div class="stat-card">
                <div class="stat-val" style="color: #10b981;">{ranking_result.eligible_count}</div>
                <div class="stat-lbl">Eligible Parcels</div>
            </div>
            <div class="stat-card">
                <div class="stat-val" style="color: #ef4444;">{ranking_result.excluded_count}</div>
                <div class="stat-lbl">Excluded Parcels</div>
            </div>
            <div class="stat-card">
                <div class="stat-val" style="color: #0284c7;">{total_plantable_ha:.1f} ha</div>
                <div class="stat-lbl">Total Plantable Acreage</div>
            </div>
        </div>

        <h2>Top Priority Planting Parcels</h2>
        <p style="color: #64748b; font-size: 0.95rem;">
            Ranked deterministically by explainable multi-criteria score (Geotechnical Need 35%, Stability Improvement 30%, Plantable Area 20%, Data Confidence 15%).
        </p>

        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Parcel ID</th>
                    <th>Priority Score</th>
                    <th>Plantable Area</th>
                    <th>Mean Slope</th>
                    <th>Baseline FS</th>
                    <th>Modeled Gain</th>
                    <th>Primary Ranking Driver</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows_html)}
            </tbody>
        </table>

        <h2>Scientific & Operational Disclosures</h2>
        <ul>
            {disclosures_html}
        </ul>

        <div class="footer">
            TerraShield AI • Integrated Geospatial & Geotechnical Decision Support System • Native WGS 84 / Ellipsoidal Metric Projections
        </div>
    </div>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path
