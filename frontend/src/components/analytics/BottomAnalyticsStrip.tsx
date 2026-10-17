import React, { useMemo } from 'react';
import type { RecommendationRunResponse } from '../../api/types';
import {
  BarChart3,
  PieChart,
  Mountain,
} from 'lucide-react';

interface BottomAnalyticsStripProps {
  latestRun: RecommendationRunResponse | null;
  parcelsGeojson?: any;
  selectedParcel?: any;
  className?: string;
}

export const BottomAnalyticsStrip: React.FC<BottomAnalyticsStripProps> = ({
  latestRun,
  parcelsGeojson,
  selectedParcel,
  className = '',
}) => {
  // Module A: Metrics calculation from genuine active run data
  const metrics = useMemo(() => {
    if (!latestRun && !parcelsGeojson?.features?.length) {
      return null;
    }

    const totalEvaluated = latestRun?.total_parcels ?? parcelsGeojson?.features?.length ?? 0;
    const eligibleCount = latestRun?.eligible_count ?? 0;
    const excludedCount = latestRun?.excluded_count ?? 0;
    const insufficientCount = latestRun?.insufficient_data_count ?? 0;
    const totalPlantableAreaHa = latestRun?.total_plantable_area_ha ?? 0;

    return {
      totalEvaluated,
      eligibleCount,
      excludedCount,
      insufficientCount,
      totalPlantableAreaHa,
      timestamp: latestRun?.timestamp ? new Date(latestRun.timestamp).toLocaleDateString() : 'Active Session',
      status: totalEvaluated > 0 ? 'COMPLETED' : 'NO_DATA',
    };
  }, [latestRun, parcelsGeojson]);

  // Module B: Priority distribution calculation
  const distribution = useMemo(() => {
    if (!metrics || metrics.totalEvaluated === 0) return null;

    const topRecommendations = latestRun?.top_recommendations || latestRun?.ranked_parcels || [];
    let highPriority = 0;
    let moderatePriority = 0;
    let eligibleRemaining = 0;

    if (parcelsGeojson?.features?.length) {
      for (const f of parcelsGeojson.features) {
        const p = f.properties || {};
        const isExc = p.is_excluded || p.eligibility_status === 'EXCLUDED';
        const isIns = p.eligibility_status === 'INSUFFICIENT_DATA';
        if (!isExc && !isIns) {
          const rank = p.rank;
          if (rank && rank <= 5) highPriority++;
          else if (rank && rank <= 20) moderatePriority++;
          else eligibleRemaining++;
        }
      }
    } else {
      highPriority = Math.min(5, topRecommendations.length);
      moderatePriority = Math.max(0, Math.min(15, topRecommendations.length - 5));
      eligibleRemaining = Math.max(0, metrics.eligibleCount - highPriority - moderatePriority);
    }

    const total = metrics.totalEvaluated;
    const pctHigh = Math.round((highPriority / total) * 100);
    const pctMod = Math.round((moderatePriority / total) * 100);
    const pctElig = Math.round((eligibleRemaining / total) * 100);
    const pctExc = Math.round((metrics.excludedCount / total) * 100);
    const pctIns = Math.round((metrics.insufficientCount / total) * 100);

    return {
      highPriority,
      moderatePriority,
      eligibleRemaining,
      excluded: metrics.excludedCount,
      insufficient: metrics.insufficientCount,
      total,
      pctHigh,
      pctMod,
      pctElig,
      pctExc,
      pctIns,
    };
  }, [metrics, latestRun, parcelsGeojson]);

  // Module C: Terrain profile from actual selected parcel or active run distributions
  const terrainProfile = useMemo(() => {
    if (selectedParcel?.slope_mean_deg !== undefined) {
      return {
        type: 'PARCEL',
        label: `Parcel ${selectedParcel.parcel_id || ''}`,
        slopeMean: selectedParcel.slope_mean_deg,
        elevation: selectedParcel.elevation_mean_m,
        baselineFs: selectedParcel.fs_baseline_mean,
        reinforcedFs: selectedParcel.fs_reinforced_mean,
      };
    }

    if (latestRun?.top_recommendations?.length) {
      const slopes = latestRun.top_recommendations
        .map((p) => p.slope_mean_deg)
        .filter((s): s is number => s !== undefined);
      if (slopes.length > 0) {
        const minSlope = Math.min(...slopes);
        const maxSlope = Math.max(...slopes);
        const avgSlope = slopes.reduce((a, b) => a + b, 0) / slopes.length;
        return {
          type: 'STUDY_AREA',
          label: 'Top Parcels Gradient Range',
          slopeMean: avgSlope,
          slopeMin: minSlope,
          slopeMax: maxSlope,
        };
      }
    }

    return null;
  }, [selectedParcel, latestRun]);

  return (
    <div
      className={`grid grid-cols-1 md:grid-cols-3 gap-3 p-3.5 rounded-2xl bg-white border border-slate-200 shadow-xs text-slate-800 ${className}`}
    >
      {/* Module A: Analysis Summary */}
      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col justify-between">
        <div className="flex items-center justify-between pb-2 border-b border-slate-200 mb-2.5">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-emerald-600" />
            <span className="text-xs font-bold font-display text-slate-900">Analysis Summary</span>
          </div>
          {metrics && (
            <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-semibold">
              {metrics.status}
            </span>
          )}
        </div>

        {metrics ? (
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="p-2 rounded-lg bg-white border border-slate-200 shadow-2xs">
              <span className="text-[9.5px] font-mono text-slate-500 block uppercase font-medium">Evaluated</span>
              <span className="text-sm font-bold font-mono text-slate-900">
                {metrics.totalEvaluated.toLocaleString()}
              </span>
              <span className="text-[9px] text-slate-500 font-mono block">parcels</span>
            </div>

            <div className="p-2 rounded-lg bg-emerald-50 border border-emerald-200 shadow-2xs">
              <span className="text-[9.5px] font-mono text-emerald-700 block uppercase font-medium">Eligible</span>
              <span className="text-sm font-bold font-mono text-emerald-800">
                {metrics.eligibleCount.toLocaleString()}
              </span>
              <span className="text-[9px] text-emerald-700 font-mono block">
                {metrics.totalPlantableAreaHa.toFixed(1)} ha
              </span>
            </div>

            <div className="p-2 rounded-lg bg-rose-50 border border-rose-200 shadow-2xs">
              <span className="text-[9.5px] font-mono text-rose-700 block uppercase font-medium">Excluded</span>
              <span className="text-sm font-bold font-mono text-rose-800">
                {metrics.excludedCount.toLocaleString()}
              </span>
              <span className="text-[9px] text-rose-600 font-mono block">
                {metrics.insufficientCount} gap
              </span>
            </div>
          </div>
        ) : (
          <div className="py-4 text-center text-xs text-slate-500">
            <span>No analysis results available for this project workspace.</span>
          </div>
        )}
      </div>

      {/* Module B: Priority Distribution Donut / Progress */}
      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col justify-between">
        <div className="flex items-center justify-between pb-2 border-b border-slate-200 mb-2.5">
          <div className="flex items-center gap-2">
            <PieChart className="w-4 h-4 text-sky-600" />
            <span className="text-xs font-bold font-display text-slate-900">Priority Distribution</span>
          </div>
          {distribution && (
            <span className="text-[10px] font-mono text-slate-500">
              {distribution.total} candidate parcels
            </span>
          )}
        </div>

        {distribution ? (
          <div className="space-y-2">
            {/* Multi-segment distribution bar */}
            <div className="w-full h-3 rounded-full bg-slate-200 flex overflow-hidden shadow-inner">
              {distribution.pctHigh > 0 && (
                <div
                  style={{ width: `${distribution.pctHigh}%` }}
                  className="bg-emerald-500 h-full"
                  title={`High Priority (Top 5): ${distribution.highPriority} (${distribution.pctHigh}%)`}
                />
              )}
              {distribution.pctMod > 0 && (
                <div
                  style={{ width: `${distribution.pctMod}%` }}
                  className="bg-teal-500 h-full"
                  title={`Moderate Priority (Top 6-20): ${distribution.moderatePriority} (${distribution.pctMod}%)`}
                />
              )}
              {distribution.pctElig > 0 && (
                <div
                  style={{ width: `${distribution.pctElig}%` }}
                  className="bg-emerald-700 h-full"
                  title={`Eligible Rest: ${distribution.eligibleRemaining} (${distribution.pctElig}%)`}
                />
              )}
              {distribution.pctExc > 0 && (
                <div
                  style={{ width: `${distribution.pctExc}%` }}
                  className="bg-rose-500 h-full"
                  title={`Excluded Parcels: ${distribution.excluded} (${distribution.pctExc}%)`}
                />
              )}
              {distribution.pctIns > 0 && (
                <div
                  style={{ width: `${distribution.pctIns}%` }}
                  className="bg-amber-400 h-full"
                  title={`Insufficient Data: ${distribution.insufficient} (${distribution.pctIns}%)`}
                />
              )}
            </div>

            {/* Legend with exact parcel counts */}
            <div className="grid grid-cols-3 gap-1 text-[10px] font-mono text-slate-600 pt-1">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <span>Tier 1 ({distribution.highPriority})</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-teal-500" />
                <span>Tier 2 ({distribution.moderatePriority})</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-700" />
                <span>Eligible ({distribution.eligibleRemaining})</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="py-4 text-center text-xs text-slate-500">
            <span>Run recommendations to view parcel tier distribution.</span>
          </div>
        )}
      </div>

      {/* Module C: Terrain & Stability Profile */}
      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col justify-between">
        <div className="flex items-center justify-between pb-2 border-b border-slate-200 mb-2.5">
          <div className="flex items-center gap-2">
            <Mountain className="w-4 h-4 text-amber-600" />
            <span className="text-xs font-bold font-display text-slate-900">Terrain & Stability Profile</span>
          </div>
          <span className="text-[10px] font-mono text-slate-500">
            {terrainProfile?.type === 'PARCEL' ? 'Selected Parcel' : 'Study Area'}
          </span>
        </div>

        {terrainProfile ? (
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between font-mono">
              <span className="text-slate-600">Mean Slope Gradient:</span>
              <span className="font-bold text-slate-900">{terrainProfile.slopeMean.toFixed(1)}°</span>
            </div>

            {terrainProfile.slopeMin !== undefined && terrainProfile.slopeMax !== undefined && (
              <div className="flex items-center justify-between font-mono text-[11px] text-slate-500">
                <span>Slope Range:</span>
                <span>
                  {terrainProfile.slopeMin.toFixed(1)}° – {terrainProfile.slopeMax.toFixed(1)}°
                </span>
              </div>
            )}

            {terrainProfile.baselineFs !== undefined && terrainProfile.reinforcedFs !== undefined && (
              <div className="flex items-center justify-between font-mono text-[11px] pt-1 border-t border-slate-200">
                <span className="text-slate-600">Factor of Safety:</span>
                <span className="text-emerald-700 font-bold">
                  FS {terrainProfile.baselineFs.toFixed(2)} → {terrainProfile.reinforcedFs.toFixed(2)}
                </span>
              </div>
            )}
          </div>
        ) : (
          <div className="py-4 text-center text-xs text-slate-500">
            <span>Terrain profile data currently unavailable.</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default BottomAnalyticsStrip;
