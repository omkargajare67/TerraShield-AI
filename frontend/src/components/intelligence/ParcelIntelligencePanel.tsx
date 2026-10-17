import React, { useState, useEffect } from 'react';
import {
  Shield,
  Mountain,
  Award,
  AlertTriangle,
  Info,
  CheckCircle,
  XCircle,
  FileText,
  X,
  Loader2,
} from 'lucide-react';
import { api } from '../../api/client';

export interface ParcelIntelligenceData {
  parcel_id: string;
  rank?: number;
  priority_score_index?: number;
  priority_score?: number;
  plantable_area_ha?: number;
  total_area_ha?: number;
  slope_mean_deg?: number;
  fs_baseline_mean?: number;
  fs_reinforced_mean?: number;
  fs_delta_mean?: number;
  is_eligible?: boolean;
  is_excluded?: boolean;
  is_insufficient?: boolean;
  exclusion_reasons?: string[] | string;
  primary_driver?: string;
  estimated_required_stems?: number;
  terrain_coverage_pct?: number;
  elevation_mean_m?: number;
  ndvi_mean?: number;
}

interface ParcelIntelligencePanelProps {
  parcel: ParcelIntelligenceData | null;
  onClose?: () => void;
  onOpenReport?: () => void;
  className?: string;
}

export const ParcelIntelligencePanel: React.FC<ParcelIntelligencePanelProps> = ({
  parcel,
  onClose,
  onOpenReport,
  className = '',
}) => {
  const [activeTab, setActiveTab] = useState<'OVERVIEW' | 'GEOTECHNICAL' | 'VEGETATION' | 'RECOMMENDATIONS'>('OVERVIEW');
  const [speciesData, setSpeciesData] = useState<{ status: string; disclaimer?: string; recommendations?: any[] } | null>(null);
  const [isLoadingSpecies, setIsLoadingSpecies] = useState(false);

  // Fetch verified species constraint query for the selected parcel
  useEffect(() => {
    if (!parcel?.parcel_id) {
      setSpeciesData(null);
      return;
    }

    let isSubscribed = true;
    setIsLoadingSpecies(true);

    api
      .queryParcelSpecies(parcel.parcel_id, parcel.elevation_mean_m, parcel.slope_mean_deg)
      .then((data) => {
        if (isSubscribed) {
          setSpeciesData(data);
          setIsLoadingSpecies(false);
        }
      })
      .catch(() => {
        if (isSubscribed) {
          setSpeciesData({
            status: 'PENDING_LOCAL_ECOLOGICAL_DATA',
            disclaimer:
              'Species selection requires verified local nursery availability and ground survey.',
          });
          setIsLoadingSpecies(false);
        }
      });

    return () => {
      isSubscribed = false;
    };
  }, [parcel?.parcel_id, parcel?.elevation_mean_m, parcel?.slope_mean_deg]);

  if (!parcel) {
    return (
      <div
        className={`glass-panel-deep rounded-2xl p-6 flex flex-col justify-between border border-emerald-500/20 text-slate-300 ${className}`}
      >
        <div className="space-y-4">
          <div className="flex items-center gap-2.5 pb-3 border-b border-emerald-500/15">
            <div className="w-8 h-8 rounded-xl bg-emerald-950/60 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Shield className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-display font-bold text-sm text-white">Geospatial Intelligence</h3>
              <p className="text-[10px] font-mono text-slate-400">Parcel Geotechnical Inspection</p>
            </div>
          </div>

          <div className="py-8 text-center space-y-3">
            <div className="w-14 h-14 mx-auto rounded-2xl bg-emerald-950/40 border border-dashed border-emerald-500/30 flex items-center justify-center text-emerald-400/70">
              <Mountain className="w-7 h-7" />
            </div>
            <div className="space-y-1">
              <h4 className="text-xs font-semibold text-white">No Parcel Selected</h4>
              <p className="text-[11px] text-slate-400 max-w-xs mx-auto leading-relaxed">
                Click any candidate parcel polygon or tree marker on the interactive map to inspect its stability metrics, slope gradient, and restoration score.
              </p>
            </div>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/50 border border-emerald-500/15 text-[10.5px] text-slate-400 space-y-1">
          <span className="font-bold text-emerald-300 block">Pro Tip:</span>
          <span>
            Parcels with tree icons represent eligible candidates prioritized for root-system reinforcement.
          </span>
        </div>
      </div>
    );
  }

  // Derive eligibility attributes
  const isExcluded = parcel.is_excluded || (!parcel.is_eligible && !parcel.is_insufficient);
  const isInsufficient = parcel.is_insufficient;
  const isEligible = !isExcluded && !isInsufficient;

  const baselineFs = parcel.fs_baseline_mean;
  const reinforcedFs = parcel.fs_reinforced_mean;
  const deltaFs = parcel.fs_delta_mean !== undefined ? parcel.fs_delta_mean : (reinforcedFs && baselineFs ? reinforcedFs - baselineFs : null);

  const isTop1 = parcel.rank === 1;
  const isTopTier = parcel.rank !== undefined && parcel.rank <= 5;

  return (
    <div
      className={`bg-white rounded-2xl p-4 sm:p-5 flex flex-col justify-between border border-slate-200 shadow-xs text-slate-800 ${className}`}
    >
      <div>
        {/* Header: ID, Rank Badge, Status Pill */}
        <div className="flex items-start justify-between pb-3 border-b border-slate-200 mb-3">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-mono font-bold text-base text-slate-900 tracking-tight">
                {parcel.parcel_id}
              </h3>
              {parcel.rank && (
                <span
                  className={`px-2 py-0.5 rounded-md text-[10px] font-mono font-bold uppercase tracking-wider flex items-center gap-1 ${
                    isTop1
                      ? 'bg-amber-50 text-amber-800 border border-amber-200'
                      : isTopTier
                      ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                      : 'bg-slate-100 text-slate-700 border border-slate-200'
                  }`}
                >
                  <Award className="w-3 h-3 text-amber-500" />
                  Rank #{parcel.rank}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2 mt-1">
              {isEligible && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-50 text-emerald-800 border border-emerald-200">
                  <CheckCircle className="w-3 h-3 text-emerald-600" />
                  Eligible Candidate
                </span>
              )}
              {isInsufficient && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono bg-amber-50 text-amber-800 border border-amber-200">
                  <AlertTriangle className="w-3 h-3 text-amber-600" />
                  Insufficient Data
                </span>
              )}
              {isExcluded && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono bg-rose-50 text-rose-800 border border-rose-200">
                  <XCircle className="w-3 h-3 text-rose-600" />
                  Excluded Area
                </span>
              )}
              <span className="text-[10.5px] text-slate-500 font-mono">
                {parcel.total_area_ha ? `${parcel.total_area_ha.toFixed(2)} ha total` : 'AOI Parcel'}
              </span>
            </div>
          </div>

          {onClose && (
            <button
              onClick={onClose}
              className="p-1 rounded-lg text-slate-400 hover:text-slate-800 hover:bg-slate-100 transition cursor-pointer"
              title="Close panel"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Key Metrics Strip (KPIs) */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-[9.5px] font-mono uppercase text-slate-500 block font-medium">Plantable Area</span>
            <span className="text-sm font-bold text-slate-900 font-mono">
              {parcel.plantable_area_ha !== undefined ? `${parcel.plantable_area_ha.toFixed(2)} ha` : 'Unavailable'}
            </span>
          </div>

          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-[9.5px] font-mono uppercase text-slate-500 block font-medium">Mean Slope</span>
            <span className="text-sm font-bold text-slate-900 font-mono">
              {parcel.slope_mean_deg !== undefined ? `${parcel.slope_mean_deg.toFixed(1)}°` : 'Unavailable'}
            </span>
          </div>

          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-[9.5px] font-mono uppercase text-slate-500 block font-medium">Baseline FS</span>
            <span className="text-sm font-bold font-mono text-slate-900">
              {baselineFs !== undefined ? baselineFs.toFixed(2) : 'Unavailable'}
            </span>
          </div>

          <div className="p-2.5 rounded-xl bg-emerald-50 border border-emerald-200">
            <span className="text-[9.5px] font-mono uppercase text-emerald-800 block font-medium">+ΔFS Gain</span>
            <span className="text-sm font-bold text-emerald-700 font-mono">
              {deltaFs !== null && deltaFs !== undefined ? `+${deltaFs.toFixed(2)}` : 'Unavailable'}
            </span>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 mb-3" role="tablist">
          {(['OVERVIEW', 'GEOTECHNICAL', 'VEGETATION', 'RECOMMENDATIONS'] as const).map((tab) => (
            <button
              key={tab}
              role="tab"
              aria-selected={activeTab === tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-2 px-2.5 text-[10.5px] font-mono font-semibold transition-all relative ${
                activeTab === tab
                  ? 'text-emerald-700 border-b-2 border-emerald-600 font-bold'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab Content Panels */}
        <div className="space-y-3 text-xs leading-relaxed max-h-[340px] overflow-y-auto pr-1">
          {activeTab === 'OVERVIEW' && (
            <div className="space-y-3">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                <span className="text-[10px] font-mono uppercase text-slate-500 font-medium block">Primary Driver</span>
                <p className="font-semibold text-slate-900 text-xs">
                  {parcel.primary_driver || 'Multi-criteria composite stability need'}
                </p>
                <div className="text-[11px] text-slate-600">
                  {parcel.priority_score_index !== undefined ? (
                    <div className="flex justify-between items-center pt-1 border-t border-slate-200">
                      <span>Composite Index Score:</span>
                      <span className="font-mono font-bold text-slate-900">
                        {parcel.priority_score_index.toFixed(1)} / 100
                      </span>
                    </div>
                  ) : null}
                </div>
              </div>

              {(() => {
                const reasons = Array.isArray(parcel.exclusion_reasons)
                  ? parcel.exclusion_reasons
                  : parcel.exclusion_reasons
                  ? [String(parcel.exclusion_reasons)]
                  : [];
                if (reasons.length === 0) return null;
                return (
                  <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs space-y-1">
                    <span className="font-bold flex items-center gap-1.5 text-[11px]">
                      <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                      Exclusion Triggers:
                    </span>
                    <ul className="list-disc list-inside space-y-0.5 text-[11px] text-rose-800 font-mono">
                      {reasons.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                );
              })()}

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                  <span className="text-[9.5px] font-mono uppercase text-slate-500 font-medium block">Terrain Coverage</span>
                  <span className="font-mono text-slate-900 font-semibold">
                    {parcel.terrain_coverage_pct !== undefined ? `${parcel.terrain_coverage_pct.toFixed(1)}%` : '100%'}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                  <span className="text-[9.5px] font-mono uppercase text-slate-500 font-medium block">Required Stems</span>
                  <span className="font-mono text-emerald-700 font-semibold">
                    {parcel.estimated_required_stems !== undefined ? `${parcel.estimated_required_stems.toLocaleString()} stems` : 'Calibrated on Density'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'GEOTECHNICAL' && (
            <div className="space-y-3">
              {/* Factor of Safety Comparison Bar */}
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-900">Factor of Safety Evolution</span>
                  <span className="font-mono text-[10px] text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">Target FS: 1.30</span>
                </div>

                <div className="space-y-2 pt-1">
                  <div>
                    <div className="flex justify-between text-[10.5px] text-slate-600 font-mono mb-1">
                      <span>Baseline FS (Bare / Current):</span>
                      <span className="text-slate-900 font-bold">{baselineFs !== undefined ? baselineFs.toFixed(2) : 'Unavailable'}</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                      <div
                        className="h-full bg-amber-500 rounded-full"
                        style={{ width: `${Math.min(100, ((baselineFs || 1) / 2.5) * 100)}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-[10.5px] text-slate-600 font-mono mb-1">
                      <span>Root Reinforced FS:</span>
                      <span className="text-emerald-700 font-bold">{reinforcedFs !== undefined ? reinforcedFs.toFixed(2) : 'Unavailable'}</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                      <div
                        className="h-full bg-emerald-600 rounded-full"
                        style={{ width: `${Math.min(100, ((reinforcedFs || 1) / 2.5) * 100)}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Scientific Methodology Note */}
              <div className="p-3 rounded-xl bg-slate-100 border border-slate-200 text-[10.5px] text-slate-600 space-y-1.5">
                <div className="flex items-center gap-1.5 font-bold text-slate-800">
                  <Info className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  <span>Geotechnical Limitations & Scenario Note:</span>
                </div>
                <p className="leading-relaxed">
                  Factor of safety values use standard infinite-slope limit equilibrium equations. Soil parameters represent exploratory baseline presets, not localized borehole surveys.
                </p>
              </div>
            </div>
          )}

          {activeTab === 'VEGETATION' && (
            <div className="space-y-3">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                <span className="text-[10px] font-mono uppercase text-slate-500 font-medium block">Vegetation Coverage & NDVI</span>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-700">Sentinel-2 BOA NDVI Mean:</span>
                  <span className="font-mono font-bold text-emerald-700">
                    {parcel.ndvi_mean !== undefined ? parcel.ndvi_mean.toFixed(3) : 'Evaluated via Imagery'}
                  </span>
                </div>
                <div className="text-[11px] text-slate-600 pt-1 border-t border-slate-200">
                  Wu-Waldron root reinforcement models additional shear strength (Δc) contributed by vegetative root tensile network.
                </div>
              </div>
            </div>
          )}

          {activeTab === 'RECOMMENDATIONS' && (
            <div className="space-y-3">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono uppercase text-emerald-700 font-bold block">
                    Restoration Planting Guidance
                  </span>
                  {isLoadingSpecies && <Loader2 className="w-3 h-3 text-emerald-600 animate-spin" />}
                </div>
                <p className="text-xs text-slate-700">
                  {speciesData?.disclaimer ||
                    'Species-level planting recommendations require validated local ecological data and ground forestry assessment.'}
                </p>
                <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-[10.5px] text-emerald-800 space-y-0.5 font-mono">
                  <div>Status: {speciesData?.status || 'PENDING_LOCAL_ECOLOGICAL_DATA'}</div>
                  <div>Certified forestry validation required prior to planting.</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Action Footer */}
      <div className="pt-3 border-t border-slate-200 flex items-center justify-between mt-3">
        <span className="text-[10px] font-mono text-slate-500 truncate">
          Coordinates EPSG:4326
        </span>
        {onOpenReport && (
          <button
            onClick={onOpenReport}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs transition cursor-pointer"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Audit Report</span>
          </button>
        )}
      </div>
    </div>
  );
};

export default ParcelIntelligencePanel;
