import type { ProjectMetadata, RecommendationRunResponse } from '../api/types';

/**
 * Safely normalizes project bounding boxes.
 * Handles missing fields, inverted coordinates (minx > maxx), out-of-range values.
 */
export function normalizeBounds(bounds?: {
  minx?: number | null;
  miny?: number | null;
  maxx?: number | null;
  maxy?: number | null;
} | null): { minx: number; miny: number; maxx: number; maxy: number } {
  if (
    bounds &&
    typeof bounds.minx === 'number' &&
    typeof bounds.maxx === 'number' &&
    typeof bounds.miny === 'number' &&
    typeof bounds.maxy === 'number' &&
    !isNaN(bounds.minx) &&
    !isNaN(bounds.maxx) &&
    !isNaN(bounds.miny) &&
    !isNaN(bounds.maxy)
  ) {
    return {
      minx: Math.min(bounds.minx, bounds.maxx),
      miny: Math.min(bounds.miny, bounds.maxy),
      maxx: Math.max(bounds.minx, bounds.maxx),
      maxy: Math.max(bounds.miny, bounds.maxy),
    };
  }
  // Safe default: Wayanad watershed pilot
  return { minx: 76.0, miny: 11.55, maxx: 76.1, maxy: 11.65 };
}

/**
 * Normalizes a RecommendationRunResponse or raw summary JSON.
 * Guarantees total_parcels, eligible_count, and total_plantable_area_ha are numbers.
 */
export function normalizeRunResponse(
  raw: any,
  fallbackArtifacts?: Record<string, string>
): RecommendationRunResponse | null {
  if (!raw) return null;

  const inv = raw.parcel_inventory || {};
  const artifacts =
    raw.artifacts && Object.keys(raw.artifacts).length > 0
      ? raw.artifacts
      : fallbackArtifacts || {};

  const totalParcels =
    raw.total_parcels !== undefined && raw.total_parcels !== null
      ? Number(raw.total_parcels)
      : inv.total_evaluated !== undefined && inv.total_evaluated !== null
      ? Number(inv.total_evaluated)
      : 0;

  const eligibleCount =
    raw.eligible_count !== undefined && raw.eligible_count !== null
      ? Number(raw.eligible_count)
      : inv.eligible_count !== undefined && inv.eligible_count !== null
      ? Number(inv.eligible_count)
      : 0;

  const excludedCount =
    raw.excluded_count !== undefined && raw.excluded_count !== null
      ? Number(raw.excluded_count)
      : inv.excluded_count !== undefined && inv.excluded_count !== null
      ? Number(inv.excluded_count)
      : 0;

  const insufficientCount =
    raw.insufficient_data_count !== undefined && raw.insufficient_data_count !== null
      ? Number(raw.insufficient_data_count)
      : inv.insufficient_data_count !== undefined && inv.insufficient_data_count !== null
      ? Number(inv.insufficient_data_count)
      : 0;

  const totalAreaHa =
    raw.total_plantable_area_ha !== undefined && raw.total_plantable_area_ha !== null
      ? Number(raw.total_plantable_area_ha)
      : inv.total_plantable_area_ha !== undefined && inv.total_plantable_area_ha !== null
      ? Number(inv.total_plantable_area_ha)
      : 0;

  const topRecs =
    raw.top_recommendations ||
    raw.top_10_recommendations ||
    raw.ranked_parcels ||
    [];

  return {
    ...raw,
    run_id: raw.run_id || 'unknown_run',
    timestamp: raw.timestamp || new Date().toISOString(),
    total_parcels: isNaN(totalParcels) ? 0 : totalParcels,
    eligible_count: isNaN(eligibleCount) ? 0 : eligibleCount,
    excluded_count: isNaN(excludedCount) ? 0 : excludedCount,
    insufficient_data_count: isNaN(insufficientCount) ? 0 : insufficientCount,
    total_plantable_area_ha: isNaN(totalAreaHa) ? 0 : totalAreaHa,
    top_recommendations: topRecs,
    artifacts,
  };
}

/**
 * Normalizes project metadata to prevent undefined/null crashes on optional fields.
 */
export function normalizeProjectMetadata(p: any): ProjectMetadata {
  return {
    ...p,
    id: p.id || 'unknown_project',
    name: p.name || 'Unnamed Project',
    description: p.description || '',
    bounds: normalizeBounds(p.bounds),
    layers: p.layers || {},
    saved_runs: p.saved_runs || [],
    geotechnical_parameters: p.geotechnical_parameters || {
      name: 'Standard Presets',
      soil: {},
      root: {},
    },
    recommendation_settings: p.recommendation_settings || {},
  };
}
