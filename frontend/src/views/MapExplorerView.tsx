import React, { useState, useMemo } from 'react';
import type { ProjectMetadata, RecommendationRunResponse } from '../api/types';
import { MapCanvas } from '../components/map/MapCanvas';
import {
  Compass,
  Info,
  TreePine,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  Play,
} from 'lucide-react';

interface MapExplorerViewProps {
  activeProject: ProjectMetadata | null;
  latestRun: RecommendationRunResponse | null;
  parcelsGeojson: any;
  onNavigateToWizard?: () => void;
}

export const MapExplorerView: React.FC<MapExplorerViewProps> = ({
  activeProject,
  latestRun,
  parcelsGeojson,
  onNavigateToWizard,
}) => {
  const [selectedParcelId, setSelectedParcelId] = useState<string | null>(null);
  const [filterLayer, setFilterLayer] = useState<'all' | 'top5' | 'eligible' | 'excluded'>('all');
  const [isTechDetailsOpen, setIsTechDetailsOpen] = useState(false);

  const topRecs = latestRun?.top_recommendations || latestRun?.ranked_parcels || [];

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

  const selectedParcel = useMemo(() => {
    if (!selectedParcelId) return topRecs[0] || null;
    return topRecs.find((p) => p.parcel_id === selectedParcelId) || topRecs[0] || null;
  }, [selectedParcelId, topRecs]);

  const isEligible = selectedParcel
    ? selectedParcel.is_eligible !== undefined
      ? selectedParcel.is_eligible
      : (selectedParcel.plantable_area_ha || 0) > 0
    : false;

  return (
    <div className="space-y-6 pb-12 animate-fade-in max-w-7xl mx-auto px-4 sm:px-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-2xl bg-terra-forest/40 border border-terra-border/40 backdrop-blur-xl shadow-lg">
        <div>
          <h2 className="text-xl font-display font-semibold text-terra-ivory flex items-center gap-2">
            <Compass className="w-5 h-5 text-terra-mint" />
            <span>Interactive Geospatial Map Explorer</span>
          </h2>
          <p className="text-xs text-terra-muted mt-0.5">
            Explore study area boundaries, hillslope parcel polygons, and restoration priority tiers.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Layer Filter Pills */}
          <div className="flex items-center p-1 rounded-xl bg-terra-deep/70 border border-terra-border/50 text-xs">
            <button
              onClick={() => setFilterLayer('all')}
              className={`px-2.5 py-1 rounded-lg transition font-medium cursor-pointer ${
                filterLayer === 'all'
                  ? 'bg-terra-forest text-terra-mint font-semibold shadow-sm'
                  : 'text-terra-muted hover:text-terra-ivory'
              }`}
            >
              All Parcels
            </button>
            <button
              onClick={() => setFilterLayer('top5')}
              className={`px-2.5 py-1 rounded-lg transition font-medium cursor-pointer ${
                filterLayer === 'top5'
                  ? 'bg-terra-forest text-terra-mint font-semibold shadow-sm'
                  : 'text-terra-muted hover:text-terra-ivory'
              }`}
            >
              Top Tier (1–5)
            </button>
            <button
              onClick={() => setFilterLayer('eligible')}
              className={`px-2.5 py-1 rounded-lg transition font-medium cursor-pointer ${
                filterLayer === 'eligible'
                  ? 'bg-terra-forest text-terra-mint font-semibold shadow-sm'
                  : 'text-terra-muted hover:text-terra-ivory'
              }`}
            >
              Recommended
            </button>
            <button
              onClick={() => setFilterLayer('excluded')}
              className={`px-2.5 py-1 rounded-lg transition font-medium cursor-pointer ${
                filterLayer === 'excluded'
                  ? 'bg-terra-forest text-terra-mint font-semibold shadow-sm'
                  : 'text-terra-muted hover:text-terra-ivory'
              }`}
            >
              Excluded
            </button>
          </div>

          <span className="text-xs font-mono text-terra-slate bg-terra-deep/70 px-3 py-1.5 rounded-xl border border-terra-border/50 hidden md:inline">
            CRS: {activeProject?.native_crs || 'EPSG:4326'}
          </span>
        </div>
      </div>

      {/* Main Grid: Map + Sidebar Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Map Canvas (3 Cols) */}
        <div className="lg:col-span-3 space-y-3">
          <MapCanvas
            parcelsGeojson={filteredGeojson}
            boundaryGeojson={activeProject?.boundary_geojson}
            selectedParcelId={selectedParcelId}
            onSelectParcel={(pid) => setSelectedParcelId(pid)}
            height="620px"
          />

          <div className="p-3.5 rounded-xl bg-terra-forest/30 border border-terra-border/30 text-xs text-terra-slate flex flex-col sm:flex-row sm:items-center justify-between gap-2 font-mono">
            <span>Click any parcel polygon on the map to inspect its stability gain and planting area.</span>
            <span className="text-terra-mint">
              {filteredGeojson?.features?.length || 0} parcels displayed
            </span>
          </div>
        </div>

        {/* Selected Parcel Inspector Panel (1 Col) */}
        <div className="rounded-2xl p-5 bg-terra-forest/30 border border-terra-border/40 backdrop-blur-xl space-y-4 self-start shadow-xl">
          <div className="flex items-center justify-between border-b border-terra-border/30 pb-3">
            <span className="text-xs font-mono uppercase tracking-wider text-terra-mint font-semibold">
              Location Inspector
            </span>
            {selectedParcel && (
              <span className="font-mono text-[11px] px-2 py-0.5 rounded-full bg-terra-mint/20 text-terra-mint border border-terra-mint/30 font-semibold">
                {selectedParcel.rank ? `Rank #${selectedParcel.rank}` : 'Unranked'}
              </span>
            )}
          </div>

          {selectedParcel ? (
            <div className="space-y-3.5 text-xs">
              <div className="p-3 rounded-xl bg-terra-deep/60 border border-terra-border/30">
                <span className="text-terra-slate block text-[11px] mb-0.5">Parcel Identifier</span>
                <span className="text-sm font-semibold text-terra-ivory font-mono">
                  {selectedParcel.parcel_id}
                </span>
              </div>

              {/* Priority Score */}
              <div className="p-3 rounded-xl bg-terra-deep/60 border border-terra-border/30">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-terra-slate text-[11px]">Priority Composite Score</span>
                  <span className="text-base font-bold text-terra-mint font-mono">
                    {((selectedParcel.priority_score_index ?? (selectedParcel.priority_score ? selectedParcel.priority_score * 100 : 0))).toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-terra-border/40 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-terra-mint h-full rounded-full transition-all"
                    style={{
                      width: `${Math.min(100, Math.max(0, (selectedParcel.priority_score_index ?? 0)))}%`,
                    }}
                  />
                </div>
              </div>

              {/* Status Badge */}
              <div className="p-2.5 rounded-xl bg-terra-deep/60 border border-terra-border/30 flex items-center justify-between">
                <span className="text-terra-slate text-[11px]">Suitability Status:</span>
                {isEligible ? (
                  <span className="text-[11px] font-semibold text-emerald-400 flex items-center gap-1">
                    <TreePine className="w-3.5 h-3.5" />
                    Recommended
                  </span>
                ) : (
                  <span className="text-[11px] font-semibold text-terra-slate flex items-center gap-1">
                    <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
                    Excluded (Slope/Mask)
                  </span>
                )}
              </div>

              {/* Key Metrics 2x2 */}
              <div className="grid grid-cols-2 gap-2">
                <div className="p-2.5 rounded-xl bg-terra-deep/60 border border-terra-border/30">
                  <span className="text-terra-slate block text-[10px]">Plantable Area</span>
                  <span className="text-terra-ivory font-semibold font-mono text-xs">
                    {(selectedParcel.plantable_area_ha ?? selectedParcel.total_area_ha ?? 0).toFixed(2)} ha
                  </span>
                </div>

                <div className="p-2.5 rounded-xl bg-terra-deep/60 border border-terra-border/30">
                  <span className="text-terra-slate block text-[10px]">Modeled Stability Gain</span>
                  <span className="text-emerald-400 font-semibold font-mono text-xs">
                    {selectedParcel.delta_fs !== undefined || selectedParcel.fs_delta_mean !== undefined
                      ? `+${((selectedParcel.delta_fs ?? selectedParcel.fs_delta_mean) || 0).toFixed(2)} ΔFS`
                      : 'N/A'}
                  </span>
                </div>

                <div className="p-2.5 rounded-xl bg-terra-deep/60 border border-terra-border/30">
                  <span className="text-terra-slate block text-[10px]">Mean Gradient</span>
                  <span className="text-terra-ivory font-semibold font-mono text-xs">
                    {selectedParcel.slope_mean_deg !== undefined
                      ? `${selectedParcel.slope_mean_deg.toFixed(1)}°`
                      : 'N/A'}
                  </span>
                </div>

                <div className="p-2.5 rounded-xl bg-terra-deep/60 border border-terra-border/30">
                  <span className="text-terra-slate block text-[10px]">Baseline Safety (FS₀)</span>
                  <span className="text-terra-ivory font-semibold font-mono text-xs">
                    {selectedParcel.baseline_fs !== undefined || selectedParcel.fs_baseline_mean !== undefined
                      ? ((selectedParcel.baseline_fs ?? selectedParcel.fs_baseline_mean) || 0).toFixed(2)
                      : 'N/A'}
                  </span>
                </div>
              </div>

              {/* Expandable Technical Diagnostics */}
              <div className="rounded-xl border border-terra-border/30 bg-terra-deep/30 overflow-hidden">
                <button
                  type="button"
                  onClick={() => setIsTechDetailsOpen(!isTechDetailsOpen)}
                  className="w-full px-3 py-2 flex items-center justify-between text-[11px] text-terra-muted hover:text-terra-ivory font-mono transition"
                >
                  <span>Technical Diagnostics</span>
                  {isTechDetailsOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>

                {isTechDetailsOpen && (
                  <div className="p-3 border-t border-terra-border/20 space-y-1 text-[11px] font-mono text-terra-slate">
                    <div>Ranking Driver: {selectedParcel.primary_driver || 'Geotechnical Stability Gain'}</div>
                    {selectedParcel.estimated_required_stems && (
                      <div>Estimated Seedlings: {Math.round(selectedParcel.estimated_required_stems).toLocaleString()} stems</div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="text-center py-10 text-terra-slate text-xs space-y-3">
              <Info className="w-7 h-7 text-terra-muted mx-auto" />
              <p>No parcel selected. Click any candidate parcel on the map to inspect its details.</p>
              {topRecs.length > 0 ? (
                <button
                  onClick={() => setSelectedParcelId(topRecs[0].parcel_id)}
                  className="px-3 py-1.5 rounded-lg bg-terra-mint/15 text-terra-mint font-semibold text-xs hover:bg-terra-mint/25 transition cursor-pointer"
                >
                  Select Top Ranked Parcel
                </button>
              ) : onNavigateToWizard ? (
                <button
                  onClick={onNavigateToWizard}
                  className="px-3.5 py-1.5 rounded-lg bg-terra-mint text-terra-deep font-semibold text-xs hover:bg-terra-mint/90 transition cursor-pointer inline-flex items-center gap-1.5"
                >
                  <Play className="w-3.5 h-3.5 fill-terra-deep" />
                  <span>Start New Analysis</span>
                </button>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MapExplorerView;
