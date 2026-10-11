import React, { useState } from 'react';
import type { ProjectMetadata, RecommendationRunResponse } from '../api/types';
import { MapCanvas } from '../components/map/MapCanvas';
import { Compass, Info } from 'lucide-react';

interface MapExplorerViewProps {
  activeProject: ProjectMetadata | null;
  latestRun: RecommendationRunResponse | null;
  parcelsGeojson: any;
}

export const MapExplorerView: React.FC<MapExplorerViewProps> = ({
  activeProject,
  latestRun,
  parcelsGeojson,
}) => {
  const [selectedParcelId, setSelectedParcelId] = useState<string | null>(null);

  const topRecs = latestRun?.top_recommendations || [];
  const selectedParcel = topRecs.find((p) => p.parcel_id === selectedParcelId) || topRecs[0];

  return (
    <div className="space-y-6 pb-12 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-2xl bg-terra-forest/40 border border-terra-border/40 backdrop-blur-xl">
        <div>
          <h2 className="text-xl font-display font-semibold text-terra-ivory flex items-center gap-2">
            <Compass className="w-5 h-5 text-terra-mint" />
            <span>Interactive Geospatial Map Explorer</span>
          </h2>
          <p className="text-xs text-terra-muted mt-0.5">
            Spatial inspection canvas for study area extents, candidate parcel grids, and prioritization rankings.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-terra-mint bg-terra-deep/70 px-3 py-1.5 rounded-xl border border-terra-border/50">
            CRS: {activeProject?.native_crs || 'EPSG:32643 (UTM 43N)'}
          </span>
        </div>
      </div>

      {/* Main Grid: Map + Sidebar Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Map Canvas (3 Cols) */}
        <div className="lg:col-span-3 space-y-4">
          <MapCanvas
            parcelsGeojson={parcelsGeojson}
            boundaryGeojson={activeProject?.boundary_geojson}
            selectedParcelId={selectedParcelId}
            onSelectParcel={(pid) => setSelectedParcelId(pid)}
            height="620px"
          />

          <div className="p-3.5 rounded-xl bg-terra-forest/30 border border-terra-border/30 text-xs text-terra-slate flex items-center justify-between font-mono">
            <span>Click any parcel polygon on the map to inspect zonal statistics and priority drivers.</span>
            <span className="text-terra-mint">
              {parcelsGeojson?.features?.length || 0} features loaded
            </span>
          </div>
        </div>

        {/* Selected Parcel Inspector Drawer (1 Col) */}
        <div className="rounded-2xl p-5 bg-terra-forest/30 border border-terra-border/40 backdrop-blur-xl space-y-4 self-start">
          <div className="flex items-center justify-between border-b border-terra-border/30 pb-3">
            <span className="text-xs font-mono uppercase tracking-wider text-terra-mint font-semibold">
              Parcel Inspector
            </span>
            {selectedParcel && (
              <span className="font-mono text-[11px] px-2 py-0.5 rounded-full bg-terra-mint/20 text-terra-mint border border-terra-mint/30">
                Rank #{selectedParcel.rank || 1}
              </span>
            )}
          </div>

          {selectedParcel ? (
            <div className="space-y-3.5 text-xs">
              <div className="p-3 rounded-xl bg-terra-deep/60 border border-terra-border/30">
                <span className="text-terra-slate block text-[11px]">Parcel Identifier</span>
                <span className="text-sm font-semibold text-terra-ivory font-mono">
                  {selectedParcel.parcel_id}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-terra-deep/60 border border-terra-border/30">
                <span className="text-terra-slate block text-[11px]">Priority Score Index</span>
                <span className="text-lg font-bold text-terra-mint font-mono">
                  {(selectedParcel.priority_score_index ?? 0).toFixed(1)} / 100
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="p-2.5 rounded-xl bg-terra-deep/60 border border-terra-border/30">
                  <span className="text-terra-slate block text-[10px]">Plantable Area</span>
                  <span className="text-terra-ivory font-semibold font-mono">
                    {(selectedParcel.plantable_area_ha ?? 0).toFixed(2)} ha
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-terra-deep/60 border border-terra-border/30">
                  <span className="text-terra-slate block text-[10px]">Total Area</span>
                  <span className="text-terra-ivory font-semibold font-mono">
                    {(selectedParcel.total_area_ha ?? 0).toFixed(2)} ha
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-terra-deep/60 border border-terra-border/30">
                  <span className="text-terra-slate block text-[10px]">Mean Gradient</span>
                  <span className="text-terra-ivory font-semibold font-mono">
                    {selectedParcel.slope_mean_deg !== undefined
                      ? selectedParcel.slope_mean_deg.toFixed(1) + '°'
                      : 'N/A'}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-terra-deep/60 border border-terra-border/30">
                  <span className="text-terra-slate block text-[10px]">Baseline FS₀</span>
                  <span className="text-terra-ivory font-semibold font-mono">
                    {selectedParcel.fs_baseline_mean !== undefined
                      ? selectedParcel.fs_baseline_mean.toFixed(2)
                      : 'N/A'}
                  </span>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-terra-deep/60 border border-terra-border/30 space-y-1">
                <span className="text-terra-slate block text-[11px]">Primary Ranking Driver</span>
                <span className="text-terra-muted font-medium">
                  {selectedParcel.primary_driver || 'Geotechnical Stability Gain'}
                </span>
              </div>

              {selectedParcel.estimated_required_stems && (
                <div className="p-3 rounded-xl bg-terra-mint/10 border border-terra-mint/20 text-terra-ivory">
                  <span className="block text-[11px] text-terra-mint font-semibold">Sapling Capacity</span>
                  <span className="text-sm font-bold font-mono">
                    {Math.round(selectedParcel.estimated_required_stems).toLocaleString()} stems
                  </span>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-terra-slate text-xs space-y-2">
              <Info className="w-8 h-8 text-terra-muted mx-auto" />
              <p>No parcel selected. Click any candidate on the map or run an analysis to view metrics.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
