"""FastAPI routes for Phase 4 Spatial Recommendation Engine."""

import os
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse
from shapely.geometry import shape

from backend.app.core.config import settings
from backend.app.core.recommendations.spatial_reference import (
    calculate_polygon_area_ha,
    meters_to_degrees_approx,
)
from backend.app.core.recommendations.parcel_generation import (
    CandidateParcel,
    generate_candidate_parcels,
)
from backend.app.core.recommendations.zonal_statistics import (
    RasterLayerContext,
    extract_parcel_zonal_statistics,
)
from backend.app.core.recommendations.eligibility import (
    EligibilityConfig,
    EligibilityStatus,
    evaluate_parcel_eligibility,
)
from backend.app.core.recommendations.scoring import (
    ScoringWeights,
    calculate_parcel_score,
)
from backend.app.core.recommendations.ranking import (
    EvaluatedParcel,
    RankingResult,
    rank_candidate_parcels,
)
from backend.app.core.recommendations.explainability import (
    generate_parcel_explanation,
)
from backend.app.core.recommendations.provenance import (
    RecommendationProvenance,
    build_recommendation_provenance,
)
from backend.app.core.recommendations.budget_allocation import (
    BudgetAllocationConfig,
    allocate_planting_budget,
)
from backend.app.core.recommendations.species_interface import (
    DEFAULT_SPECIES_DB,
    SpeciesRecommendationResult,
)
from backend.app.core.recommendations.report_generation import (
    export_candidate_parcels_geojson,
    export_parcel_metrics_csv,
    export_parcel_rankings_csv,
    export_recommendation_summary_json,
    export_recommendation_report_html,
)
from backend.app.schemas.recommendations import (
    InputLayerStatus,
    ParcelGenerationRequest,
    ParcelGenerationResponse,
    ParcelSummary,
    RankedParcelSummary,
    RecommendationRunRequest,
    RecommendationRunResponse,
    RecommendationStatusResponse,
)

router = APIRouter(prefix="/recommendations", tags=["Spatial Recommendations"])

RECOMMENDATIONS_DIR = settings.PROCESSED_DIR / "recommendations"
RECOMMENDATIONS_DIR.mkdir(parents=True, exist_ok=True)

GEOTECH_SUMMARY_PATH = settings.PROCESSED_DIR / "geotechnical" / "wayanad_geotechnical_summary.json"


def _get_active_layer_paths() -> Dict[str, Path]:
    """Resolve file paths for verified input raster layers."""
    return {
        "dem": settings.BASE_DIR / "data" / "raw" / "real" / "wayanad_dem.tif",
        "slope": settings.PROCESSED_DIR / "real" / "wayanad_slope.tif",
        "aspect": settings.PROCESSED_DIR / "real" / "wayanad_aspect.tif",
        "ndvi": settings.PROCESSED_DIR / "real" / "wayanad_ndvi.tif",
        "fs_baseline": settings.PROCESSED_DIR / "geotechnical" / "wayanad_fs_baseline.tif",
        "fs_reinforced": settings.PROCESSED_DIR / "geotechnical" / "wayanad_fs_reinforced.tif",
        "fs_delta": settings.PROCESSED_DIR / "geotechnical" / "wayanad_fs_delta.tif",
        "required_cohesion": settings.PROCESSED_DIR / "geotechnical" / "wayanad_required_cohesion.tif",
        "tree_density": settings.PROCESSED_DIR / "geotechnical" / "wayanad_required_tree_density.tif",
    }


def get_safe_recommendation_artifact(artifact_id: str) -> Optional[Path]:
    """Safely resolve an artifact inside RECOMMENDATIONS_DIR, preventing path traversal."""
    clean_name = os.path.basename(artifact_id)
    target = (RECOMMENDATIONS_DIR / clean_name).resolve()
    try:
        target.relative_to(RECOMMENDATIONS_DIR.resolve())
    except ValueError:
        return None
    if target.exists() and target.is_file():
        return target
    return None


@router.get(
    "/status",
    response_model=RecommendationStatusResponse,
    summary="Recommendation Engine & Input Layer Status",
)
def get_recommendation_status() -> RecommendationStatusResponse:
    """Inspect availability of all geospatial, geotechnical, and boundary layers."""
    layers = _get_active_layer_paths()
    layer_statuses: Dict[str, InputLayerStatus] = {}

    descriptions = {
        "dem": ("Copernicus 30m Global Elevation Tile", "REAL_OBSERVED"),
        "slope": ("Horns 8-neighbourhood gradient raster", "DERIVED_GEOSPATIAL"),
        "aspect": ("Topographic compass azimuth raster", "DERIVED_GEOSPATIAL"),
        "ndvi": ("Sentinel-2 BOA Normalized Difference Vegetation Index", "DERIVED_GEOSPATIAL"),
        "fs_baseline": ("Infinite Slope Baseline Factor of Safety", "ILLUSTRATIVE_SCENARIO"),
        "fs_reinforced": ("Infinite Slope Root-Reinforced Factor of Safety", "ILLUSTRATIVE_SCENARIO"),
        "fs_delta": ("Modeled Factor of Safety Improvement", "ILLUSTRATIVE_SCENARIO"),
        "required_cohesion": ("Root cohesion needed for FS >= 1.3", "ILLUSTRATIVE_SCENARIO"),
        "tree_density": ("Required Stem Density from linear RAR scaling", "ILLUSTRATIVE_SCENARIO"),
    }

    for key, p in layers.items():
        desc, cat = descriptions.get(key, ("Input raster layer", "UNKNOWN"))
        layer_statuses[key] = InputLayerStatus(
            layer_name=p.name,
            available=p.exists(),
            file_path=str(p) if p.exists() else None,
            category=cat,
            description=desc,
        )

    geotech_note = (
        "Available: Spatially uniform exploratory benchmark scenario (Phase 3)"
        if GEOTECH_SUMMARY_PATH.exists()
        else "Unavailable: Run Phase 3 geotechnical raster analysis"
    )

    return RecommendationStatusResponse(
        status="ready" if layers["slope"].exists() else "partially_configured",
        pilot_study_area_bounds={"minx": 76.00, "miny": 11.55, "maxx": 76.10, "maxy": 11.65},
        native_crs="EPSG:4326 (WGS 84)",
        supported_cell_sizes_m=[100, 200, 300, 500, 1000],
        input_layers=layer_statuses,
        geotechnical_scenario_status=geotech_note,
        protected_area_data_status="UNVERIFIED: Official legal cadastral reserve boundaries not loaded",
        species_database_status="PENDING_CURATED_BOTANICAL_DATA: Scientific evidence registry active (empty)",
    )


@router.post(
    "/parcels/generate",
    response_model=ParcelGenerationResponse,
    summary="Generate Discretized Candidate Planting Parcels",
)
def generate_parcels(req: ParcelGenerationRequest) -> ParcelGenerationResponse:
    """Generate candidate planning parcels across the bounding box with configurable cell size."""
    try:
        parcels = generate_candidate_parcels(
            min_lon=req.minx,
            min_lat=req.miny,
            max_lon=req.maxx,
            max_lat=req.maxy,
            cell_size_m=req.cell_size_m,
        )
        run_id = uuid.uuid4().hex[:8]
        total_area = sum(p.total_area_ha for p in parcels)

        samples = [
            ParcelSummary(
                parcel_id=p.parcel_id,
                total_area_ha=round(p.total_area_ha, 4),
                bounds={
                    "minx": p.bounds[0],
                    "miny": p.bounds[1],
                    "maxx": p.bounds[2],
                    "maxy": p.bounds[3],
                },
            )
            for p in parcels[:5]
        ]

        return ParcelGenerationResponse(
            run_id=run_id,
            cell_size_m=req.cell_size_m,
            parcel_count=len(parcels),
            total_grid_area_ha=round(total_area, 2),
            bounds={"minx": req.minx, "miny": req.miny, "maxx": req.maxx, "maxy": req.maxy},
            sample_parcels=samples,
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Candidate parcel generation failed: {str(err)}",
        )


@router.post(
    "/run",
    response_model=RecommendationRunResponse,
    summary="Execute Full Spatial Recommendation & Prioritization Pipeline",
)
def run_spatial_recommendations(req: RecommendationRunRequest) -> RecommendationRunResponse:
    """Execute end-to-end spatial recommendation analysis, scoring, ranking, and export generation."""
    run_id = uuid.uuid4().hex[:8]
    timestamp = datetime.now(timezone.utc).isoformat()

    layers = _get_active_layer_paths()
    if not layers["slope"].exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Required Wayanad slope raster not found. Run Phase 2 geospatial engine first.",
        )

    # 1. Generate candidate parcels
    # Wayanad pilot extent
    parcels = generate_candidate_parcels(
        min_lon=76.00,
        min_lat=11.55,
        max_lon=76.10,
        max_lat=11.65,
        cell_size_m=req.cell_size_m,
    )

    # 2. Open raster contexts
    dem_ctx = RasterLayerContext(layers["dem"]) if layers["dem"].exists() else None
    slope_ctx = RasterLayerContext(layers["slope"])
    aspect_ctx = RasterLayerContext(layers["aspect"]) if layers["aspect"].exists() else None
    ndvi_ctx = RasterLayerContext(layers["ndvi"]) if layers["ndvi"].exists() else None
    fs_base_ctx = RasterLayerContext(layers["fs_baseline"]) if layers["fs_baseline"].exists() else None
    fs_reinf_ctx = RasterLayerContext(layers["fs_reinforced"]) if layers["fs_reinforced"].exists() else None
    fs_delta_ctx = RasterLayerContext(layers["fs_delta"]) if layers["fs_delta"].exists() else None
    req_c_ctx = RasterLayerContext(layers["required_cohesion"]) if layers["required_cohesion"].exists() else None
    tree_d_ctx = RasterLayerContext(layers["tree_density"]) if layers["tree_density"].exists() else None

    # 3. Configure eligibility engine
    el_cfg_in = req.eligibility_settings
    elig_config = EligibilityConfig(
        min_terrain_coverage_pct=el_cfg_in.min_terrain_coverage_pct if el_cfg_in else 80.0,
        max_slope_deg=el_cfg_in.max_slope_deg if el_cfg_in else 45.0,
        enable_ndvi_canopy_filter=el_cfg_in.enable_ndvi_canopy_filter if el_cfg_in else False,
        ndvi_canopy_threshold=el_cfg_in.ndvi_canopy_threshold if el_cfg_in else 0.65,
        min_plantable_area_ha=el_cfg_in.min_plantable_area_ha if el_cfg_in else 0.25,
        protected_areas_geojson=req.protected_areas_geojson,
        user_exclusions_geojson=req.user_exclusions_geojson,
    )

    # 4. Evaluate parcels
    evaluated_list: List[EvaluatedParcel] = []
    for cand in parcels:
        s_geom = shape(cand.geometry)
        metrics = extract_parcel_zonal_statistics(
            parcel_poly=s_geom,
            bounds=cand.bounds,
            slope_ctx=slope_ctx,
            dem_ctx=dem_ctx,
            aspect_ctx=aspect_ctx,
            ndvi_ctx=ndvi_ctx,
            fs_base_ctx=fs_base_ctx,
            fs_reinf_ctx=fs_reinf_ctx,
            fs_delta_ctx=fs_delta_ctx,
            req_c_ctx=req_c_ctx,
            tree_d_ctx=tree_d_ctx,
            fs_target=req.fs_target,
            ndvi_canopy_threshold=elig_config.ndvi_canopy_threshold,
        )

        status_code, reasons, plantable_ha, pa_note = evaluate_parcel_eligibility(
            parcel_poly=s_geom,
            parcel_total_area_ha=cand.total_area_ha,
            metrics=metrics,
            config=elig_config,
        )

        evaluated_list.append(
            EvaluatedParcel(
                parcel_id=cand.parcel_id,
                geometry=cand.geometry,
                total_area_ha=cand.total_area_ha,
                plantable_area_ha=plantable_ha,
                eligibility_status=status_code,
                exclusion_reasons=reasons,
                protected_area_clearance_note=pa_note,
                metrics=metrics,
            )
        )

    # 5. Rank eligible parcels
    weights_in = req.scoring_weights
    scoring_w = ScoringWeights(
        weight_geotechnical_need=weights_in.weight_geotechnical_need if weights_in else 0.35,
        weight_stability_gain=weights_in.weight_stability_gain if weights_in else 0.30,
        weight_plantable_area=weights_in.weight_plantable_area if weights_in else 0.20,
        weight_data_confidence=weights_in.weight_data_confidence if weights_in else 0.15,
    )

    ranking_result = rank_candidate_parcels(
        evaluated_parcels=evaluated_list,
        run_id=run_id,
        timestamp=timestamp,
        scoring_weights=scoring_w,
        fs_target=req.fs_target,
    )

    # 6. Build Provenance
    provenance = build_recommendation_provenance(
        run_id=run_id,
        timestamp=timestamp,
        geotech_summary_path=GEOTECH_SUMMARY_PATH,
        has_official_protected_areas=req.protected_areas_geojson is not None,
    )

    # 7. Optional Budget Allocation
    budget_res = None
    if req.budget_config:
        b_cfg = BudgetAllocationConfig(
            total_budget_inr=req.budget_config.total_budget_inr,
            cost_per_sapling_inr=req.budget_config.cost_per_sapling_inr,
            fixed_parcel_setup_cost_inr=req.budget_config.fixed_parcel_setup_cost_inr,
            default_planting_density_stems_ha=req.budget_config.default_planting_density_stems_ha,
            max_stems_per_ha_cap=req.budget_config.max_stems_per_ha_cap,
        )
        budget_res = allocate_planting_budget(
            ranked_parcels=ranking_result.ranked_eligible_parcels,
            config=b_cfg,
        ).model_dump()

    # 8. Export files
    prefix = f"run_{run_id}"
    geojson_path = export_candidate_parcels_geojson(
        ranking_result, RECOMMENDATIONS_DIR / f"{prefix}_parcels.geojson"
    )
    metrics_path = export_parcel_metrics_csv(
        ranking_result, RECOMMENDATIONS_DIR / f"{prefix}_parcel_metrics.csv"
    )
    rankings_path = export_parcel_rankings_csv(
        ranking_result, RECOMMENDATIONS_DIR / f"{prefix}_parcel_rankings.csv"
    )
    summary_path = export_recommendation_summary_json(
        ranking_result, provenance, RECOMMENDATIONS_DIR / f"{prefix}_summary.json"
    )
    report_path = export_recommendation_report_html(
        ranking_result, provenance, RECOMMENDATIONS_DIR / f"{prefix}_report.html"
    )

    # Artifact ID mapping
    artifacts = {
        "parcels_geojson": geojson_path.name,
        "parcel_metrics_csv": metrics_path.name,
        "parcel_rankings_csv": rankings_path.name,
        "summary_json": summary_path.name,
        "audit_report_html": report_path.name,
    }

    # Prepare top recommendations summaries
    top_summaries: List[RankedParcelSummary] = []
    for p in ranking_result.ranked_eligible_parcels[:20]:
        sc = p.score_breakdown
        exp = generate_parcel_explanation(p, provenance)
        top_summaries.append(
            RankedParcelSummary(
                rank=p.rank or 0,
                parcel_id=p.parcel_id,
                priority_score_index=sc.priority_score_index if sc else 0.0,
                plantable_area_ha=round(p.plantable_area_ha, 2),
                total_area_ha=round(p.total_area_ha, 2),
                slope_mean_deg=p.metrics.get("slope_mean_deg"),
                fs_baseline_mean=p.metrics.get("fs_baseline_mean"),
                fs_delta_mean=p.metrics.get("fs_delta_mean"),
                primary_driver=exp.primary_ranking_drivers[0] if exp.primary_ranking_drivers else "Composite Multi-Criteria",
                modeled_stability_gain_per_stem=p.modeled_stability_gain_per_stem,
                estimated_required_stems=p.estimated_required_stems,
            )
        )

    tot_plantable = sum(p.plantable_area_ha for p in ranking_result.ranked_eligible_parcels)

    return RecommendationRunResponse(
        run_id=run_id,
        timestamp=timestamp,
        total_parcels=ranking_result.total_parcels_evaluated,
        eligible_count=ranking_result.eligible_count,
        excluded_count=ranking_result.excluded_count,
        insufficient_data_count=ranking_result.insufficient_data_count,
        total_plantable_area_ha=round(tot_plantable, 2),
        top_recommendations=top_summaries,
        scoring_weights_normalized=ranking_result.scoring_weights.model_dump(),
        provenance_warning=provenance.geotechnical_scenario_note,
        artifacts=artifacts,
        budget_summary=budget_res,
    )


@router.get(
    "/runs/{run_id}",
    summary="Retrieve Prior Analysis Summary Record",
)
def get_run_summary(run_id: str) -> Dict[str, Any]:
    """Retrieve saved JSON summary for a prior recommendation run."""
    clean_id = os.path.basename(run_id)
    summary_file = RECOMMENDATIONS_DIR / f"run_{clean_id}_summary.json"
    if not summary_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation run '{clean_id}' summary not found.",
        )
    with open(summary_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get(
    "/artifacts/{artifact_id}",
    summary="Download Generated Recommendation Artifact",
)
def download_recommendation_artifact(artifact_id: str):
    """Securely download GeoJSON, CSV, JSON, or HTML analysis exports."""
    safe_path = get_safe_recommendation_artifact(artifact_id)
    if not safe_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact '{artifact_id}' not found or invalid path.",
        )

    # Determine media type
    ext = safe_path.suffix.lower()
    media_types = {
        ".geojson": "application/geo+json",
        ".json": "application/json",
        ".csv": "text/csv",
        ".html": "text/html",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=safe_path,
        media_type=media_type,
        filename=safe_path.name,
    )


@router.get(
    "/species/{parcel_id}",
    response_model=SpeciesRecommendationResult,
    summary="Query Native Species Recommendations for Parcel",
)
def query_parcel_species(
    parcel_id: str,
    elevation_m: Optional[float] = Query(None),
    slope_deg: Optional[float] = Query(None),
) -> SpeciesRecommendationResult:
    """Query botanical database for native planting species."""
    return DEFAULT_SPECIES_DB.query_for_parcel(
        parcel_id=parcel_id,
        elevation_mean_m=elevation_m,
        slope_mean_deg=slope_deg,
    )
