import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Award,
  Download,
  Search,
  ChevronRight,
  ShieldAlert,
  TreePine,
  TrendingUp,
  Layers,
  FileSpreadsheet,
  FileCode,
  FileText,
  X,
  Compass,
  Mountain,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import type { RecommendationRunResponse, RankedParcelSummary } from '../api/types';
import { api } from '../api/client';
import { MetricCard } from '../components/common/MetricCard';
import { ProvenanceBanner } from '../components/common/ProvenanceBanner';
import { HelpTooltip } from '../components/common/HelpTooltip';

interface ResultsViewProps {
  latestRun: RecommendationRunResponse | null;
  parcelsGeojson?: any;
  onNavigateToWizard: () => void;
  onNavigateToMap: () => void;
}

export const ResultsView: React.FC<ResultsViewProps> = ({
  latestRun,
  onNavigateToWizard,
  onNavigateToMap,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterEligibility, setFilterEligibility] = useState<'all' | 'eligible' | 'excluded'>('all');
  const [sortBy, setSortBy] = useState<'rank' | 'score' | 'delta_fs' | 'area'>('rank');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [selectedParcel, setSelectedParcel] = useState<RankedParcelSummary | null>(null);
  const [isTechDetailsOpen, setIsTechDetailsOpen] = useState(false);

  const parcels: RankedParcelSummary[] = useMemo(() => {
    return latestRun?.top_recommendations || latestRun?.ranked_parcels || [];
  }, [latestRun]);

  const getScore = (p: RankedParcelSummary): number => {
    if (p.priority_score !== undefined) return p.priority_score;
    if (p.priority_score_index !== undefined) return p.priority_score_index / 100;
    return 0;
  };

  const getDeltaFs = (p: RankedParcelSummary): number => {
    if (p.delta_fs !== undefined) return p.delta_fs;
    if (p.fs_delta_mean !== undefined) return p.fs_delta_mean;
    return 0;
  };

  const getAreaHa = (p: RankedParcelSummary): number => {
    if (p.plantable_area_ha !== undefined) return p.plantable_area_ha;
    if (p.total_area_ha !== undefined) return p.total_area_ha;
    if (p.area_sqm !== undefined) return p.area_sqm / 10000;
    return 0;
  };

  const getIsEligible = (p: RankedParcelSummary): boolean => {
    if (p.is_eligible !== undefined) return p.is_eligible;
    return (p.plantable_area_ha || 0) > 0;
  };

  const filteredAndSortedParcels = useMemo(() => {
    return parcels
      .filter((p) => {
        const matchesSearch = p.parcel_id.toLowerCase().includes(searchTerm.toLowerCase());
        const isEligible = getIsEligible(p);
        const matchesFilter =
          filterEligibility === 'all' ||
          (filterEligibility === 'eligible' && isEligible) ||
          (filterEligibility === 'excluded' && !isEligible);
        return matchesSearch && matchesFilter;
      })
      .sort((a, b) => {
        let valA = 0;
        let valB = 0;
        if (sortBy === 'rank') {
          valA = a.rank ?? 9999;
          valB = b.rank ?? 9999;
        } else if (sortBy === 'score') {
          valA = getScore(a);
          valB = getScore(b);
        } else if (sortBy === 'delta_fs') {
          valA = getDeltaFs(a);
          valB = getDeltaFs(b);
        } else if (sortBy === 'area') {
          valA = getAreaHa(a);
          valB = getAreaHa(b);
        }
        return sortOrder === 'asc' ? valA - valB : valB - valA;
      });
  }, [parcels, searchTerm, filterEligibility, sortBy, sortOrder]);

  const kpis = useMemo(() => {
    const total = latestRun?.total_parcels || parcels.length;
    const eligible = latestRun?.eligible_count || parcels.filter((p) => getIsEligible(p)).length;
    const excluded = latestRun?.excluded_count || total - eligible;
    const totalAreaHa =
      latestRun?.total_plantable_area_ha ||
      parcels.reduce((acc, p) => acc + getAreaHa(p), 0);
    const avgDeltaFs =
      eligible > 0
        ? parcels.filter((p) => getIsEligible(p)).reduce((acc, p) => acc + getDeltaFs(p), 0) / eligible
        : 0;

    return {
      total,
      eligible,
      excluded,
      totalAreaHa: parseFloat(totalAreaHa.toFixed(1)),
      avgDeltaFs: parseFloat(avgDeltaFs.toFixed(2)),
    };
  }, [parcels, latestRun]);

  // Clean empty state
  if (!latestRun && parcels.length === 0) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-16 animate-fade-in text-center space-y-6">
        <div className="p-10 rounded-3xl bg-terra-forest/40 border border-terra-border/50 backdrop-blur-xl shadow-2xl space-y-5">
          <div className="w-16 h-16 rounded-2xl bg-terra-mint/15 text-terra-mint border border-terra-mint/25 flex items-center justify-center mx-auto shadow-inner">
            <Award className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-display font-semibold text-terra-ivory">
            No Analysis Results Yet
          </h2>
          <p className="text-terra-muted text-sm max-w-md mx-auto leading-relaxed">
            Run a 5-step analysis to evaluate slope stability, calculate bio-reinforcement gains, and explore prioritized planting parcels.
          </p>
          <div className="pt-2 flex flex-wrap items-center justify-center gap-3">
            <button
              onClick={onNavigateToWizard}
              className="px-6 py-3 rounded-xl bg-terra-mint text-terra-deep font-semibold text-xs hover:bg-terra-mint/90 transition shadow-lg shadow-terra-mint/10"
            >
              Start New Analysis
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8 animate-fade-in">
      {/* Header & Meta */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-2 border-b border-terra-border/30">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono tracking-wider font-semibold uppercase bg-terra-mint/15 text-terra-mint border border-terra-mint/25">
              Run #{latestRun?.run_id?.slice(0, 8) || 'active'}
            </span>
            <span className="text-xs text-terra-slate font-mono">
              Provenance: {latestRun?.dem_source_provenance || 'Infinite-Slope LE + Multi-Criteria'}
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-display font-semibold text-terra-ivory">
            Recommendation & Prioritization Results
          </h1>
          <p className="text-sm text-terra-muted mt-1">
            Engineered bio-reinforcement priorities based on modeled stability gain (&Delta;FS) and terrain vulnerability.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={onNavigateToMap}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-terra-forest/80 hover:bg-terra-forest text-terra-ivory text-xs font-semibold border border-terra-border/40 transition shadow-sm cursor-pointer"
          >
            <Compass className="w-4 h-4 text-terra-mint" />
            <span>Inspect on Map</span>
          </button>

          {latestRun?.artifacts?.geojson && (
            <a
              href={api.getArtifactUrl(latestRun.artifacts.geojson)}
              download
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-terra-mint text-terra-deep hover:bg-terra-mint/90 text-xs font-semibold transition shadow-md shadow-terra-mint/10"
            >
              <Download className="w-4 h-4" />
              <span>Export GeoJSON</span>
            </a>
          )}
        </div>
      </div>

      <ProvenanceBanner />

      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <MetricCard
          label="Total Parcels Evaluated"
          value={kpis.total}
          icon={Layers}
          subtext="Processed polygons"
          color="slate"
        />
        <MetricCard
          label="Recommended for Planting"
          value={kpis.eligible}
          icon={TreePine}
          subtext={`${((kpis.eligible / (kpis.total || 1)) * 100).toFixed(0)}% pass safety rules`}
          badge="Actionable"
          color="emerald"
        />
        <MetricCard
          label="Excluded Locations"
          value={kpis.excluded}
          icon={ShieldAlert}
          subtext="Slope >45° or canopy"
          color="amber"
        />
        <MetricCard
          label="Total Plantable Area"
          value={kpis.totalAreaHa}
          suffix=" ha"
          icon={Mountain}
          subtext="Sum of eligible zones"
          color="emerald"
        />
        <MetricCard
          label="Avg Modeled ΔFS Gain"
          value={kpis.avgDeltaFs}
          decimals={2}
          icon={TrendingUp}
          prefix="+"
          subtext="Stability increase"
          badge="Modeled"
          color="emerald"
        />
      </div>

      {/* Artifact Downloads Grid */}
      {latestRun?.artifacts && (
        <div className="p-4 rounded-2xl bg-terra-forest/20 border border-terra-border/40 backdrop-blur-md flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-terra-mint/10 border border-terra-mint/20 flex items-center justify-center text-terra-mint shrink-0">
              <Download className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-xs font-semibold text-terra-ivory uppercase tracking-wider font-mono">
                Download Analysis Deliverables
              </h4>
              <p className="text-xs text-terra-slate">
                Export verified audit tables, metrics summaries, and spatial polygon layers.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {latestRun.artifacts.geojson && (
              <a
                href={api.getArtifactUrl(latestRun.artifacts.geojson)}
                download
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-terra-forest/60 hover:bg-terra-forest text-terra-ivory text-xs border border-terra-border/50 font-mono transition"
              >
                <FileCode className="w-3.5 h-3.5 text-terra-mint" />
                GeoJSON
              </a>
            )}
            {latestRun.artifacts.summary_csv && (
              <a
                href={api.getArtifactUrl(latestRun.artifacts.summary_csv)}
                download
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-terra-forest/60 hover:bg-terra-forest text-terra-ivory text-xs border border-terra-border/50 font-mono transition"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 text-terra-mint" />
                Rankings CSV
              </a>
            )}
            {latestRun.artifacts.metrics_csv && (
              <a
                href={api.getArtifactUrl(latestRun.artifacts.metrics_csv)}
                download
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-terra-forest/60 hover:bg-terra-forest text-terra-ivory text-xs border border-terra-border/50 font-mono transition"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 text-terra-mint" />
                Detailed Metrics CSV
              </a>
            )}
            {latestRun.artifacts.summary_json && (
              <a
                href={api.getArtifactUrl(latestRun.artifacts.summary_json)}
                download
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-terra-forest/60 hover:bg-terra-forest text-terra-ivory text-xs border border-terra-border/50 font-mono transition"
              >
                <FileText className="w-3.5 h-3.5 text-terra-mint" />
                Summary JSON
              </a>
            )}
          </div>
        </div>
      )}

      {/* Main Results Table & Filters */}
      <div className="rounded-3xl border border-terra-border/40 bg-terra-forest/30 backdrop-blur-xl overflow-hidden shadow-xl">
        {/* Table Toolbar */}
        <div className="p-4 md:p-6 border-b border-terra-border/30 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="relative w-full md:w-80">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-terra-slate" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by parcel ID..."
              className="w-full pl-10 pr-4 py-2 rounded-xl bg-terra-deep/70 border border-terra-border/60 text-terra-ivory text-xs placeholder:text-terra-slate focus:outline-none focus:border-terra-mint transition"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-terra-slate hover:text-terra-ivory"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            {/* Filter Toggle */}
            <div className="flex items-center p-1 rounded-xl bg-terra-deep/60 border border-terra-border/40 text-xs">
              <button
                onClick={() => setFilterEligibility('all')}
                className={`px-3 py-1.5 rounded-lg transition font-medium cursor-pointer ${
                  filterEligibility === 'all'
                    ? 'bg-terra-forest text-terra-mint font-semibold shadow-sm'
                    : 'text-terra-muted hover:text-terra-ivory'
                }`}
              >
                All ({parcels.length})
              </button>
              <button
                onClick={() => setFilterEligibility('eligible')}
                className={`px-3 py-1.5 rounded-lg transition font-medium cursor-pointer ${
                  filterEligibility === 'eligible'
                    ? 'bg-terra-forest text-terra-mint font-semibold shadow-sm'
                    : 'text-terra-muted hover:text-terra-ivory'
                }`}
              >
                Recommended ({kpis.eligible})
              </button>
              <button
                onClick={() => setFilterEligibility('excluded')}
                className={`px-3 py-1.5 rounded-lg transition font-medium cursor-pointer ${
                  filterEligibility === 'excluded'
                    ? 'bg-terra-forest text-terra-mint font-semibold shadow-sm'
                    : 'text-terra-muted hover:text-terra-ivory'
                }`}
              >
                Excluded ({kpis.excluded})
              </button>
            </div>

            {/* Sort Dropdown */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="px-3 py-2 rounded-xl bg-terra-deep/70 border border-terra-border/60 text-terra-ivory text-xs font-mono focus:outline-none focus:border-terra-mint"
            >
              <option value="rank">Sort: Rank Priority</option>
              <option value="score">Sort: Priority Score</option>
              <option value="delta_fs">Sort: Modeled ΔFS Gain</option>
              <option value="area">Sort: Plantable Area</option>
            </select>

            <button
              onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              className="p-2 rounded-xl bg-terra-deep/70 border border-terra-border/60 text-terra-slate hover:text-terra-ivory text-xs font-mono transition cursor-pointer"
              title="Toggle sort direction"
            >
              {sortOrder === 'asc' ? '▲ Asc' : '▼ Desc'}
            </button>
          </div>
        </div>

        {/* Table Content */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-terra-border/30 bg-terra-deep/40 text-terra-slate font-mono uppercase tracking-wider text-[11px]">
                <th className="py-3.5 px-4 font-medium">Rank</th>
                <th className="py-3.5 px-4 font-medium">Parcel ID</th>
                <th className="py-3.5 px-4 font-medium">
                  Priority Score
                  <HelpTooltip text="Normalized composite index (0-100%) indicating restoration priority." />
                </th>
                <th className="py-3.5 px-4 font-medium">
                  Baseline FS
                  <HelpTooltip text="Factor of Safety without tree roots." />
                </th>
                <th className="py-3.5 px-4 font-medium">
                  Modeled &Delta;FS
                  <HelpTooltip text="Modeled stability increase with root reinforcement." />
                </th>
                <th className="py-3.5 px-4 font-medium">Area (ha)</th>
                <th className="py-3.5 px-4 font-medium">Status</th>
                <th className="py-3.5 px-4 font-medium text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-terra-border/20 text-terra-ivory font-sans">
              {filteredAndSortedParcels.map((p) => {
                const isSelected = selectedParcel?.parcel_id === p.parcel_id;
                const scoreVal = getScore(p);
                const scoreText = (scoreVal * 100).toFixed(1);
                const baseFs = (p.baseline_fs ?? p.fs_baseline_mean)?.toFixed(2) || '—';
                const deltaVal = getDeltaFs(p);
                const deltaFs = deltaVal > 0 ? `+${deltaVal.toFixed(2)}` : '—';
                const areaHa = getAreaHa(p).toFixed(2);
                const isEligible = getIsEligible(p);

                return (
                  <tr
                    key={p.parcel_id}
                    onClick={() => setSelectedParcel(p)}
                    className={`cursor-pointer transition hover:bg-terra-forest/40 ${
                      isSelected ? 'bg-terra-mint/10 border-l-2 border-terra-mint' : ''
                    }`}
                  >
                    <td className="py-3.5 px-4 font-mono font-semibold">
                      {p.rank ? (
                        <span
                          className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-[11px] font-bold ${
                            p.rank === 1
                              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                              : p.rank <= 5
                              ? 'bg-terra-mint/20 text-terra-mint border border-terra-mint/30'
                              : 'text-terra-slate'
                          }`}
                        >
                          {p.rank}
                        </span>
                      ) : (
                        <span className="text-terra-slate">—</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 font-mono font-medium text-terra-ivory">
                      {p.parcel_id}
                    </td>
                    <td className="py-3.5 px-4 font-mono font-semibold text-terra-mint">
                      {scoreText}%
                    </td>
                    <td className="py-3.5 px-4 font-mono text-terra-muted">
                      {baseFs}
                    </td>
                    <td className="py-3.5 px-4 font-mono font-semibold text-emerald-400">
                      {deltaFs}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-terra-muted">
                      {areaHa}
                    </td>
                    <td className="py-3.5 px-4">
                      {isEligible ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/25">
                          Recommended
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-terra-slate/20 text-terra-slate border border-terra-slate/30">
                          Excluded
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedParcel(p);
                        }}
                        className="p-1 rounded-lg hover:bg-terra-mint/10 text-terra-slate hover:text-terra-mint transition"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}

              {filteredAndSortedParcels.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-terra-slate">
                    No parcels match the current filter or search criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Parcel Detail Drawer */}
      <AnimatePresence>
        {selectedParcel && (
          <div className="fixed inset-0 z-50 flex justify-end">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedParcel(null)}
              className="fixed inset-0 bg-terra-deep/75 backdrop-blur-sm"
            />

            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="relative w-full max-w-md h-full bg-terra-forest/95 border-l border-terra-border/50 p-6 overflow-y-auto shadow-2xl flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between pb-4 border-b border-terra-border/40 mb-6">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-terra-mint/20 text-terra-mint">
                        {selectedParcel.rank ? `Rank #${selectedParcel.rank}` : 'Unranked'}
                      </span>
                      {getIsEligible(selectedParcel) ? (
                        <span className="text-[10px] font-semibold text-emerald-400">
                          ● Recommended for Planting
                        </span>
                      ) : (
                        <span className="text-[10px] font-semibold text-terra-slate">
                          ● Excluded from Priority Planting
                        </span>
                      )}
                    </div>
                    <h3 className="text-xl font-display font-semibold text-terra-ivory">
                      {selectedParcel.parcel_id}
                    </h3>
                  </div>

                  <button
                    onClick={() => setSelectedParcel(null)}
                    className="p-1.5 rounded-xl bg-terra-deep/50 hover:bg-terra-deep text-terra-slate hover:text-terra-ivory border border-terra-border/40 transition"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {/* Score Spotlight */}
                <div className="p-4 rounded-2xl bg-terra-deep/70 border border-terra-border/40 mb-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-terra-slate">Priority Composite Score</span>
                    <span className="text-xl font-mono font-bold text-terra-mint">
                      {(getScore(selectedParcel) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-terra-border/40 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-terra-mint h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.min(100, Math.max(0, getScore(selectedParcel) * 100))}%`,
                      }}
                    />
                  </div>
                  <p className="text-[11px] text-terra-slate italic">
                    Primary Ranking Driver: {selectedParcel.primary_driver || 'Hillslope Stability Gain'}
                  </p>
                </div>

                {/* Plain Key Findings */}
                <div className="space-y-3 mb-5">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-terra-mint font-semibold">
                    Key Location Assessment
                  </h4>

                  <div className="grid grid-cols-2 gap-2.5 text-xs">
                    <div className="p-3 rounded-xl bg-terra-deep/50 border border-terra-border/30">
                      <span className="text-terra-slate block mb-1">Plantable Area</span>
                      <span className="font-mono text-sm font-semibold text-terra-ivory">
                        {getAreaHa(selectedParcel).toFixed(2)} ha
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-terra-deep/50 border border-terra-border/30">
                      <span className="text-terra-slate block mb-1">Modeled Stability Gain</span>
                      <span className="font-mono text-sm font-semibold text-emerald-400">
                        {getDeltaFs(selectedParcel) > 0 ? `+${getDeltaFs(selectedParcel).toFixed(2)} ΔFS` : '—'}
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-terra-deep/50 border border-terra-border/30">
                      <span className="text-terra-slate block mb-1">Baseline Stability</span>
                      <span className="font-mono text-sm font-semibold text-terra-ivory">
                        {(selectedParcel.baseline_fs ?? selectedParcel.fs_baseline_mean)?.toFixed(2) || '—'}
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-terra-deep/50 border border-terra-border/30">
                      <span className="text-terra-slate block mb-1">Mean Slope</span>
                      <span className="font-mono text-sm font-semibold text-terra-ivory">
                        {selectedParcel.slope_mean_deg !== undefined ? `${selectedParcel.slope_mean_deg.toFixed(1)}°` : '—'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Expandable Technical Diagnostics */}
                <div className="rounded-xl border border-terra-border/30 bg-terra-deep/30 overflow-hidden mb-5">
                  <button
                    type="button"
                    onClick={() => setIsTechDetailsOpen(!isTechDetailsOpen)}
                    className="w-full px-4 py-2.5 flex items-center justify-between text-xs text-terra-muted hover:text-terra-ivory font-mono transition"
                  >
                    <span>Technical Zonal Diagnostics</span>
                    {isTechDetailsOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>

                  {isTechDetailsOpen && (
                    <div className="p-4 border-t border-terra-border/20 space-y-1.5 text-[11px] font-mono text-terra-slate">
                      <div>Baseline FS (FS₀): {(selectedParcel.baseline_fs ?? selectedParcel.fs_baseline_mean)?.toFixed(3) || 'N/A'}</div>
                      <div>Reinforced FS: {selectedParcel.reinforced_fs !== undefined ? selectedParcel.reinforced_fs.toFixed(3) : 'N/A'}</div>
                      <div>Modeled ΔFS: {getDeltaFs(selectedParcel) > 0 ? `+${getDeltaFs(selectedParcel).toFixed(3)}` : 'N/A'}</div>
                      <div>Mean Slope: {selectedParcel.slope_mean_deg !== undefined ? `${selectedParcel.slope_mean_deg.toFixed(2)}°` : 'N/A'}</div>
                      <div>Sapling Estimate: {selectedParcel.estimated_required_stems ? `${Math.round(selectedParcel.estimated_required_stems).toLocaleString()} stems` : 'N/A'}</div>
                    </div>
                  )}
                </div>

                {/* Scientific Advisory Note */}
                <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-200/90 text-xs leading-relaxed">
                  <div className="flex items-center gap-1.5 font-semibold mb-1 text-amber-300">
                    <ShieldAlert className="w-3.5 h-3.5" />
                    Decision Support Advisory
                  </div>
                  Values represent modeled limit-equilibrium potential based on available remote sensing. Site geotechnical borehole calibration is required prior to ground engineering.
                </div>
              </div>

              {/* Drawer Footer Actions */}
              <div className="pt-4 border-t border-terra-border/40 mt-4">
                <button
                  onClick={onNavigateToMap}
                  className="w-full py-2.5 rounded-xl bg-terra-mint text-terra-deep font-semibold text-xs hover:bg-terra-mint/90 transition text-center shadow-lg shadow-terra-mint/10 flex items-center justify-center gap-2 cursor-pointer"
                >
                  <Compass className="w-4 h-4" />
                  <span>Inspect Location on Geospatial Map</span>
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ResultsView;
