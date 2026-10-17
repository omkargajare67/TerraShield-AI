import React, { useState, useMemo, useEffect } from 'react';
import type { ProjectMetadata, RecommendationRunResponse } from '../api/types';
import { api } from '../api/client';
import { MapCanvas } from '../components/map/MapCanvas';
import { ParcelIntelligencePanel } from '../components/intelligence/ParcelIntelligencePanel';
import { BottomAnalyticsStrip } from '../components/analytics/BottomAnalyticsStrip';
import { CaseStudyStrip } from '../components/case-studies/CaseStudyStrip';
import {
  Compass,
  PanelRightClose,
  PanelRightOpen,
  Plus,
} from 'lucide-react';

interface MapExplorerViewProps {
  activeProject: ProjectMetadata | null;
  latestRun: RecommendationRunResponse | null;
  parcelsGeojson: any;
  onNavigateToWizard?: () => void;
  onOpenResults?: () => void;
  onOpenReport?: () => void;
  onExploreCaseStudy?: (caseId: string) => Promise<void>;
}

export const MapExplorerView: React.FC<MapExplorerViewProps> = ({
  activeProject,
  latestRun,
  parcelsGeojson,
  onNavigateToWizard,
  onOpenResults,
  onOpenReport,
  onExploreCaseStudy,
}) => {
  const [selectedParcelId, setSelectedParcelId] = useState<string | null>(null);
  const [filterLayer, setFilterLayer] = useState<'all' | 'top5' | 'eligible' | 'excluded'>('all');
  const [isInspectorOpen, setIsInspectorOpen] = useState(true);
  const [fetchedInventory, setFetchedInventory] = useState<{ caseId: string; data: any } | null>(null);

  const activeCaseId = useMemo(() => {
    if (!activeProject) return null;
    if (activeProject.id === 'wayanad_pilot') return 'wayanad_2024';
    if (activeProject.id === 'cascade_demo') return 'cascade_demo';
    if (activeProject.id.startsWith('proj_case_')) return activeProject.id.replace('proj_case_', '');
    return null;
  }, [activeProject]);

  const observedInventory = fetchedInventory?.caseId === activeCaseId ? fetchedInventory.data : null;

  // Load observed disaster inventory if project corresponds to a verified case study
  useEffect(() => {
    if (!activeCaseId) {
      setFetchedInventory(null);
      return;
    }
    let isSubscribed = true;

    api
      .getCaseStudyObservedInventory(activeCaseId)
      .then((geo) => {
        if (isSubscribed) setFetchedInventory({ caseId: activeCaseId, data: geo });
      })
      .catch(() => {
        if (isSubscribed) setFetchedInventory({ caseId: activeCaseId, data: null });
      });

    return () => {
      isSubscribed = false;
    };
  }, [activeCaseId]);

  const topRecs = useMemo(
    () => latestRun?.top_recommendations || latestRun?.ranked_parcels || [],
    [latestRun]
  );

  // Filtered GeoJSON features based on layer selection
  const filteredGeojson = useMemo(() => {
    if (!parcelsGeojson?.features) return parcelsGeojson;

    let filtered = parcelsGeojson.features;
    if (filterLayer === 'top5') {
      filtered = filtered.filter((f: any) => {
        const rank = f.properties?.rank;
        return rank && rank <= 5;
      });
    } else if (filterLayer === 'eligible') {
      filtered = filtered.filter((f: any) => {
        const isExcluded = f.properties?.is_excluded || f.properties?.eligibility_status === 'EXCLUDED';
        return !isExcluded;
      });
    } else if (filterLayer === 'excluded') {
      filtered = filtered.filter((f: any) => {
        const isExcluded = f.properties?.is_excluded || f.properties?.eligibility_status === 'EXCLUDED';
        return isExcluded;
      });
    }

    return {
      ...parcelsGeojson,
      features: filtered,
    };
  }, [parcelsGeojson, filterLayer]);

  // Selected Parcel Normalized Data
  const selectedParcelData = useMemo(() => {
    if (selectedParcelId && parcelsGeojson?.features) {
      const feat = parcelsGeojson.features.find(
        (f: any) => (f.properties?.parcel_id || f.id) === selectedParcelId
      );
      if (feat) {
        const p = feat.properties || {};
        const status = String(p.eligibility_status || '').toUpperCase();
        const isExc = p.is_excluded || status === 'EXCLUDED';
        const isIns = status === 'INSUFFICIENT_DATA';
        return {
          parcel_id: p.parcel_id || feat.id,
          rank: p.rank,
          priority_score_index: p.priority_score_index,
          priority_score: p.priority_score,
          plantable_area_ha: p.plantable_area_ha,
          total_area_ha: p.total_area_ha,
          slope_mean_deg: p.slope_mean_deg,
          fs_baseline_mean: p.fs_baseline_mean,
          fs_reinforced_mean: p.fs_reinforced_mean,
          fs_delta_mean: p.fs_delta_mean,
          is_eligible: !isExc && !isIns,
          is_insufficient: isIns,
          is_excluded: isExc,
          exclusion_reasons: p.exclusion_reasons,
          primary_driver: p.primary_driver || (p.fs_delta_mean ? 'Stability Gain (+ΔFS)' : 'Terrain Constraints'),
          estimated_required_stems: p.estimated_required_stems,
          terrain_coverage_pct: p.terrain_coverage_pct,
          elevation_mean_m: p.elevation_mean_m || (p.elevation_min_m && p.elevation_max_m ? (p.elevation_min_m + p.elevation_max_m) / 2 : undefined),
          ndvi_mean: p.ndvi_mean,
        };
      }
    }
    if (selectedParcelId) {
      const foundInTop = topRecs.find((p) => p.parcel_id === selectedParcelId);
      if (foundInTop) {
        return {
          parcel_id: foundInTop.parcel_id,
          rank: foundInTop.rank,
          priority_score_index: foundInTop.priority_score_index,
          plantable_area_ha: foundInTop.plantable_area_ha,
          total_area_ha: foundInTop.total_area_ha,
          slope_mean_deg: foundInTop.slope_mean_deg,
          fs_baseline_mean: foundInTop.fs_baseline_mean,
          fs_reinforced_mean: foundInTop.fs_reinforced_mean,
          fs_delta_mean: foundInTop.fs_delta_mean,
          is_eligible: true,
          primary_driver: foundInTop.primary_driver,
          estimated_required_stems: foundInTop.estimated_required_stems,
        };
      }
    }
    // Default to rank 1 parcel if available
    if (topRecs.length > 0) {
      const top1 = topRecs[0];
      return {
        parcel_id: top1.parcel_id,
        rank: top1.rank,
        priority_score_index: top1.priority_score_index,
        plantable_area_ha: top1.plantable_area_ha,
        total_area_ha: top1.total_area_ha,
        slope_mean_deg: top1.slope_mean_deg,
        fs_baseline_mean: top1.fs_baseline_mean,
        fs_reinforced_mean: top1.fs_reinforced_mean,
        fs_delta_mean: top1.fs_delta_mean,
        is_eligible: true,
        primary_driver: top1.primary_driver,
        estimated_required_stems: top1.estimated_required_stems,
      };
    }
    return null;
  }, [selectedParcelId, topRecs, parcelsGeojson]);

  return (
    <div className="space-y-4 pb-12 animate-fade-in max-w-[1720px] mx-auto px-3 sm:px-6">
      {/* Top Filter and Context Controls Strip */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-2xl glass-panel-deep border border-emerald-500/20 backdrop-blur-xl shadow-lg">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-emerald-950/60 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
            <Compass className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-display font-bold text-white tracking-tight">
                Geospatial Intelligence Map
              </h2>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                Interactive Analysis
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-sans">
              Hillslope parcels, infinite-slope stability indices, and vegetative root reinforcement.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Quick Parcel Filter Buttons */}
          <div className="flex items-center p-1 rounded-xl bg-[#071610] border border-emerald-500/20 text-xs font-mono">
            <button
              onClick={() => setFilterLayer('all')}
              className={`px-2.5 py-1 rounded-lg transition font-medium cursor-pointer ${
                filterLayer === 'all'
                  ? 'bg-emerald-600/40 text-emerald-200 border border-emerald-400/40 font-semibold shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilterLayer('top5')}
              className={`px-2.5 py-1 rounded-lg transition font-medium cursor-pointer ${
                filterLayer === 'top5'
                  ? 'bg-emerald-600/40 text-emerald-200 border border-emerald-400/40 font-semibold shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Top Tier (1–5)
            </button>
            <button
              onClick={() => setFilterLayer('eligible')}
              className={`px-2.5 py-1 rounded-lg transition font-medium cursor-pointer ${
                filterLayer === 'eligible'
                  ? 'bg-emerald-600/40 text-emerald-200 border border-emerald-400/40 font-semibold shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Eligible
            </button>
            <button
              onClick={() => setFilterLayer('excluded')}
              className={`px-2.5 py-1 rounded-lg transition font-medium cursor-pointer ${
                filterLayer === 'excluded'
                  ? 'bg-emerald-600/40 text-emerald-200 border border-emerald-400/40 font-semibold shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Excluded
            </button>
          </div>

          {onNavigateToWizard && (
            <button
              onClick={onNavigateToWizard}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-500 hover:to-teal-600 text-white text-xs font-mono font-semibold transition cursor-pointer shadow-sm"
              title="Start a new guided analysis"
            >
              <Plus className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">New Analysis</span>
            </button>
          )}

          {/* Toggle Inspector Panel Button */}
          <button
            onClick={() => setIsInspectorOpen(!isInspectorOpen)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#081812] hover:bg-emerald-950/60 text-slate-300 hover:text-emerald-300 border border-emerald-500/20 text-xs font-mono transition cursor-pointer"
            title={isInspectorOpen ? 'Collapse inspection panel' : 'Open inspection panel'}
          >
            {isInspectorOpen ? <PanelRightClose className="w-3.5 h-3.5" /> : <PanelRightOpen className="w-3.5 h-3.5" />}
            <span className="hidden md:inline">{isInspectorOpen ? 'Hide Inspector' : 'Show Inspector'}</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Dominant Central Map (Left/Center) + Right Intelligence Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Dominant Central Map Canvas */}
        <div className={`transition-all duration-300 ${isInspectorOpen ? 'lg:col-span-8 xl:col-span-9' : 'lg:col-span-12'}`}>
          <div className="relative">
            <MapCanvas
              parcelsGeojson={filteredGeojson}
              boundaryGeojson={activeProject?.boundary_geojson}
              observedInventoryGeojson={observedInventory}
              bounds={activeProject?.bounds}
              selectedParcelId={selectedParcelId}
              onSelectParcel={(pid) => setSelectedParcelId(pid)}
              height="600px"
              className="border border-emerald-500/25 shadow-2xl"
              onOpenResults={onOpenResults}
            />

            {/* Quick Status Pill Overlay */}
            <div className="absolute bottom-3 left-3 z-[400] px-3 py-1.5 rounded-xl glass-panel-deep border border-emerald-500/20 text-[11px] font-mono text-slate-300 flex items-center gap-2 shadow-lg">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>
                {filteredGeojson?.features?.length
                  ? `${filteredGeojson.features.length} parcels rendered`
                  : 'Awaiting study area parcels'}
              </span>
              <span className="text-slate-500">|</span>
              <span className="text-emerald-400/90">{activeProject?.native_crs || 'EPSG:4326'}</span>
            </div>
          </div>
        </div>

        {/* Right-Side Intelligence Panel */}
        {isInspectorOpen && (
          <div className="lg:col-span-4 xl:col-span-3">
            <ParcelIntelligencePanel
              parcel={selectedParcelData}
              onClose={() => setIsInspectorOpen(false)}
              onOpenReport={onOpenReport}
              className="h-full min-h-[500px]"
            />
          </div>
        )}
      </div>

      {/* Bottom Analytics Strip (Analysis Summary + Priority Donut + Terrain Profile) */}
      <BottomAnalyticsStrip
        latestRun={latestRun}
        parcelsGeojson={parcelsGeojson}
        selectedParcel={selectedParcelData}
      />

      {/* Bottom Case-Study Strip Carousel */}
      {onExploreCaseStudy && (
        <CaseStudyStrip
          onExploreCaseStudy={onExploreCaseStudy}
          activeCaseId={activeCaseId}
        />
      )}
    </div>
  );
};

export default MapExplorerView;
