"""Phase 4 Spatial Recommendation Engine for TerraShield AI."""

from backend.app.core.recommendations.spatial_reference import (
    WGS84Ellipsoid,
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
    ExclusionReason,
    evaluate_parcel_eligibility,
)
from backend.app.core.recommendations.scoring import (
    MissingDataPolicy,
    NormalizationConfig,
    ParcelScoreBreakdown,
    ScoringWeights,
    calculate_parcel_score,
)
from backend.app.core.recommendations.ranking import (
    EvaluatedParcel,
    RankingResult,
    rank_candidate_parcels,
)
from backend.app.core.recommendations.explainability import (
    ParcelExplanation,
    generate_parcel_explanation,
)
from backend.app.core.recommendations.provenance import (
    DatasetProvenance,
    RecommendationProvenance,
    build_recommendation_provenance,
)
from backend.app.core.recommendations.budget_allocation import (
    BudgetAllocationConfig,
    AllocationResult,
    allocate_planting_budget,
)
from backend.app.core.recommendations.species_interface import (
    CuratedSpeciesRecord,
    SpeciesDatabase,
    SpeciesRecommendationResult,
    DEFAULT_SPECIES_DB,
)
from backend.app.core.recommendations.report_generation import (
    export_candidate_parcels_geojson,
    export_parcel_metrics_csv,
    export_parcel_rankings_csv,
    export_recommendation_summary_json,
    export_recommendation_report_html,
)

__all__ = [
    "WGS84Ellipsoid",
    "calculate_polygon_area_ha",
    "meters_to_degrees_approx",
    "CandidateParcel",
    "generate_candidate_parcels",
    "RasterLayerContext",
    "extract_parcel_zonal_statistics",
    "EligibilityConfig",
    "EligibilityStatus",
    "ExclusionReason",
    "evaluate_parcel_eligibility",
    "ParcelScoreBreakdown",
    "ScoringWeights",
    "calculate_parcel_score",
    "EvaluatedParcel",
    "RankingResult",
    "rank_candidate_parcels",
    "ParcelExplanation",
    "generate_parcel_explanation",
    "DatasetProvenance",
    "RecommendationProvenance",
    "build_recommendation_provenance",
    "BudgetAllocationConfig",
    "AllocationResult",
    "allocate_planting_budget",
    "CuratedSpeciesRecord",
    "SpeciesDatabase",
    "SpeciesRecommendationResult",
    "DEFAULT_SPECIES_DB",
    "export_candidate_parcels_geojson",
    "export_parcel_metrics_csv",
    "export_parcel_rankings_csv",
    "export_recommendation_summary_json",
    "export_recommendation_report_html",
]
