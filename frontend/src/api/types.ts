/**
 * TypeScript interface definitions matching FastAPI Pydantic models.
 */

export interface SystemHealth {
  status: string;
  app_name?: string;
  version?: string;
  mode?: string;
  timestamp?: string;
  message?: string;
}

export interface GeotechnicalPreset {
  name: string;
  description: string;
  c_prime_kpa: number;
  phi_deg: number;
  gamma_kn_m3: number;
  depth_m: number;
  m_water_table: number;
  tensile_stress_kpa: number;
  rar: number;
  k_factor: number;
  target_fs: number;
  is_demo: boolean;
}

export interface ProjectMetadata {
  id: string;
  name: string;
  description?: string;
  is_builtin?: boolean;
  created_at?: string;
  updated_at?: string;
  study_area_type?: string;
  geotech_preset_id?: string;
  bounds?: {
    minx: number;
    miny: number;
    maxx: number;
    maxy: number;
  };
  native_crs?: string;
  boundary_geojson?: any;
  layers?: Record<string, {
    path?: string;
    status?: string;
    description?: string;
    format?: string;
    original_crs?: string;
    reprojected?: boolean;
    validation?: any;
  }>;
  geotechnical_parameters?: {
    preset_id?: string;
    name?: string;
    soil?: {
      c_prime_kpa?: number;
      phi_deg?: number;
      gamma_kn_m3?: number;
      depth_m?: number;
      m_water_table?: number;
    };
    root?: {
      tensile_stress_kpa?: number;
      rar?: number;
      k_factor?: number;
    };
    target_fs?: number;
    is_demo_parameters?: boolean;
  };
  recommendation_settings?: {
    cell_size_m?: number;
    eligibility_settings?: {
      min_terrain_coverage_pct?: number;
      max_slope_deg?: number;
      enable_ndvi_canopy_filter?: boolean;
      ndvi_canopy_threshold?: number;
      min_plantable_area_ha?: number;
    };
    scoring_weights?: {
      weight_geotechnical_need?: number;
      weight_stability_gain?: number;
      weight_plantable_area?: number;
      weight_data_confidence?: number;
    };
    normalization_config?: {
      fs_target?: number;
      critical_fs?: number;
      max_delta_fs_ref?: number;
      max_area_ref_ha?: number;
    };
    missing_data_policy?: string;
  };
  latest_run_id?: string;
  saved_runs?: Array<{
    run_id: string;
    timestamp: string;
    cell_size_m: number;
    total_parcels: number;
    eligible_count: number;
    excluded_count: number;
    total_plantable_area_ha: number;
    artifacts: Record<string, string>;
  }>;
}

export interface RankedParcelSummary {
  rank?: number;
  parcel_id: string;
  priority_score_index?: number;
  priority_score?: number;
  plantable_area_ha?: number;
  total_area_ha?: number;
  area_sqm?: number;
  slope_mean_deg?: number;
  fs_baseline_mean?: number;
  baseline_fs?: number;
  fs_reinforced_mean?: number;
  reinforced_fs?: number;
  fs_delta_mean?: number;
  delta_fs?: number;
  is_eligible?: boolean;
  primary_driver?: string;
  modeled_stability_gain_per_stem?: number;
  estimated_required_stems?: number;
}

export interface RecommendationRunResponse {
  run_id: string;
  timestamp: string;
  cell_size_m?: number;
  total_parcels: number;
  eligible_count: number;
  excluded_count: number;
  insufficient_data_count: number;
  total_plantable_area_ha: number;
  top_recommendations: RankedParcelSummary[];
  ranked_parcels?: RankedParcelSummary[];
  summary?: any;
  scoring_weights_normalized?: Record<string, number>;
  scoring_weights_active?: Record<string, number>;
  applied_missing_data_policy?: string;
  missing_layers_detected?: string[];
  is_discriminative?: boolean;
  differentiation_warning?: string;
  differentiating_components?: string[];
  constant_components?: string[];
  normalization_references?: Record<string, number>;
  dem_source_provenance?: string;
  provenance_warning?: string;
  artifacts?: Record<string, string>;
  budget_summary?: {
    total_budget_inr: number;
    total_budget_spent_inr: number;
    remaining_budget_inr: number;
    parcels_funded_count: number;
    total_stems_allocated: number;
  };
}

export interface VectorReport {
  format?: string;
  original_crs?: string;
  crs?: string;
  reprojected?: boolean;
  feature_count: number;
  geometry_types?: string[];
  geom_type?: string;
  bounds?: { minx: number; miny: number; maxx: number; maxy: number };
  centroid?: { lon: number; lat: number };
  area_approx_ha?: number;
  total_area_sqm?: number;
  geojson?: any;
  is_valid: boolean;
  validation_messages?: string[];
}
