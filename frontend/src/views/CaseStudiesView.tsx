import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  BookOpen,
  MapPin,
  Calendar,
  AlertTriangle,
  ShieldCheck,
  ExternalLink,
  Layers,
  Database,
  ArrowRight,
  X,
  FileText,
  Scale,
  AlertCircle,
} from 'lucide-react';
import type {
  CaseStudy,
  CaseStudyComparisonResult,
} from '../api/types';
import { api } from '../api/client';

interface CaseStudiesViewProps {
  onExploreCaseStudy: (caseId: string) => Promise<void>;
  activeProjectId?: string | null;
  parcelsGeojson?: any;
  latestRunId?: string | null;
}

type FilterTag =
  | 'all'
  | 'western_ghats'
  | 'himalayas'
  | 'nepal'
  | 'historical'
  | 'recent'
  | 'analyzable'
  | 'awaiting_data'
  | 'offline_demo';

export const CaseStudiesView: React.FC<CaseStudiesViewProps> = ({
  onExploreCaseStudy,
  activeProjectId,
  parcelsGeojson,
  latestRunId,
}) => {
  const [caseStudies, setCaseStudies] = useState<CaseStudy[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<FilterTag>('all');
  const [selectedCase, setSelectedCase] = useState<CaseStudy | null>(null);
  const [isDossierOpen, setIsDossierOpen] = useState<boolean>(false);
  const [dossierTab, setDossierTab] = useState<'overview' | 'sources' | 'data' | 'inventory' | 'comparison' | 'limitations'>('overview');
  const [comparisonResult, setComparisonResult] = useState<CaseStudyComparisonResult | null>(null);
  const [isComparing, setIsComparing] = useState<boolean>(false);
  const [comparisonError, setComparisonError] = useState<string | null>(null);
  const [launchingCaseId, setLaunchingCaseId] = useState<string | null>(null);

  // Fetch initial case studies registry
  useEffect(() => {
    let isSubscribed = true;

    api
      .getCaseStudies()
      .then((data) => {
        if (isSubscribed) {
          setCaseStudies(data || []);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (isSubscribed) {
          setLoadError(err.message || 'Failed to load case studies registry.');
          setIsLoading(false);
        }
      });

    return () => {
      isSubscribed = false;
    };
  }, []);

  // Filter case studies based on active filter
  const filteredCases = useMemo(() => {
    if (activeFilter === 'all') return caseStudies;
    if (activeFilter === 'western_ghats') return caseStudies.filter((c) => c.region_tag === 'western_ghats');
    if (activeFilter === 'himalayas') return caseStudies.filter((c) => c.region_tag === 'himalayas');
    if (activeFilter === 'nepal') return caseStudies.filter((c) => c.region_tag === 'nepal');
    if (activeFilter === 'historical') return caseStudies.filter((c) => c.temporal_tag === 'historical');
    if (activeFilter === 'recent') return caseStudies.filter((c) => c.temporal_tag === 'recent');
    if (activeFilter === 'analyzable') return caseStudies.filter((c) => c.readiness === 'READY_TO_ANALYZE');
    if (activeFilter === 'awaiting_data') return caseStudies.filter((c) => c.readiness === 'AWAITING_ADDITIONAL_DATA');
    if (activeFilter === 'offline_demo') return caseStudies.filter((c) => c.region_tag === 'offline_demo');
    return caseStudies;
  }, [caseStudies, activeFilter]);

  // Handle Explore action
  const handleExplore = async (c: CaseStudy) => {
    try {
      setLaunchingCaseId(c.id);
      await onExploreCaseStudy(c.id);
    } catch (err: any) {
      alert(`Could not launch case study workspace: ${err.message}`);
    } finally {
      setLaunchingCaseId(null);
    }
  };

  // Open Dossier Modal
  const openDossier = (c: CaseStudy, initialTab: typeof dossierTab = 'overview') => {
    setSelectedCase(c);
    setDossierTab(initialTab);
    setIsDossierOpen(true);
    setComparisonResult(null);
    setComparisonError(null);
  };

  // Run spatial comparison between observed inventory and active parcels
  const handleRunComparison = async (caseId: string) => {
    setIsComparing(true);
    setComparisonError(null);
    try {
      const res = await api.compareCaseStudyResults(caseId, {
        parcels_geojson: parcelsGeojson || undefined,
        run_id: latestRunId || undefined,
        concern_fs_threshold: 1.3,
      });
      setComparisonResult(res);
    } catch (err: any) {
      setComparisonError(err.message || 'Spatial comparison could not be calculated.');
    } finally {
      setIsComparing(false);
    }
  };

  const getVerificationBadge = (status: string) => {
    switch (status) {
      case 'VERIFIED_OBSERVATION':
        return {
          label: 'Verified Observation',
          bg: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400',
          dot: 'bg-emerald-400',
        };
      case 'HISTORICAL_CATALOG':
        return {
          label: 'Historical Catalog',
          bg: 'bg-amber-500/15 border-amber-500/30 text-amber-300',
          dot: 'bg-amber-400',
        };
      case 'PROVISIONAL_RECENT':
        return {
          label: 'Provisional Recent',
          bg: 'bg-sky-500/15 border-sky-500/30 text-sky-300',
          dot: 'bg-sky-400 animate-pulse',
        };
      case 'OFFLINE_BENCHMARK':
      default:
        return {
          label: 'Offline Synthetic Benchmark',
          bg: 'bg-slate-500/20 border-slate-500/30 text-slate-300',
          dot: 'bg-slate-400',
        };
    }
  };

  const getReadinessBadge = (readiness: string) => {
    switch (readiness) {
      case 'READY_TO_ANALYZE':
        return {
          label: 'Full Analysis Ready',
          bg: 'bg-terra-mint/15 text-terra-mint border-terra-mint/30',
        };
      case 'CACHED_ANALYSIS_AVAILABLE':
        return {
          label: 'Pre-Computed Run Available',
          bg: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
        };
      case 'AWAITING_ADDITIONAL_DATA':
      default:
        return {
          label: 'Awaiting Additional Data',
          bg: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
        };
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header Banner */}
      <div className="glass-panel p-6 sm:p-8 rounded-2xl relative overflow-hidden border border-terra-border/50">
        <div className="absolute top-0 right-0 w-96 h-96 bg-terra-mint/5 rounded-full blur-3xl -z-10 pointer-events-none" />
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-lg bg-terra-forest border border-terra-mint/30 text-terra-mint">
                <BookOpen className="w-5 h-5" />
              </span>
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-terra-mint">
                Documented Geohazard Scenarios
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-terra-ivory font-serif tracking-tight">
              Real-World Landslide Case Studies
            </h1>
            <p className="text-xs sm:text-sm text-terra-muted max-w-3xl leading-relaxed">
              Curated library of historical and recent catastrophic mass-movement events across the Western Ghats
              and Himalayas. Grounded in authoritative field surveys from ISRO, GSI, and NDRRMA, each case provides
              verified event locations, authentic terrain baselines, and transparent evaluation through TerraShield’s
              infinite-slope bio-engineering model.
            </p>
          </div>
          <div className="flex flex-col items-end gap-1.5 shrink-0 self-stretch md:self-center">
            <div className="px-3.5 py-1.5 rounded-xl bg-terra-dark/80 border border-terra-border text-[11px] font-mono text-terra-slate flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-terra-mint animate-pulse" />
              <span>{caseStudies.length} Curated Scenarios</span>
            </div>
            <span className="text-[10px] text-terra-slate font-mono">Zero synthetic danger inflation</span>
          </div>
        </div>

        {/* Scientific Safeguards Callout */}
        <div className="mt-5 p-3.5 rounded-xl bg-terra-deep/70 border border-terra-mint/20 text-xs text-terra-slate flex items-start gap-3">
          <ShieldCheck className="w-4 h-4 text-terra-mint shrink-0 mt-0.5" />
          <div className="leading-snug">
            <span className="font-semibold text-terra-ivory">Scientific Integrity Rule: </span>
            TerraShield AI does not hardcode pre-determined risk scores for disaster locations. Stability and
            planting suitability are calculated strictly from terrain gradients, root cohesion, and soil mechanics.
            Documented historical slide scars are distinguished from modeled candidate planting zones.
          </div>
        </div>
      </div>

      {/* Filter Category Pills */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
        {[
          { id: 'all' as FilterTag, label: 'All Scenarios', count: caseStudies.length },
          { id: 'western_ghats' as FilterTag, label: 'Western Ghats', count: caseStudies.filter((c) => c.region_tag === 'western_ghats').length },
          { id: 'himalayas' as FilterTag, label: 'Himalayas', count: caseStudies.filter((c) => c.region_tag === 'himalayas').length },
          { id: 'nepal' as FilterTag, label: 'Nepal', count: caseStudies.filter((c) => c.region_tag === 'nepal').length },
          { id: 'recent' as FilterTag, label: 'Recent (2023–2026)', count: caseStudies.filter((c) => c.temporal_tag === 'recent').length },
          { id: 'historical' as FilterTag, label: 'Historical Benchmarks', count: caseStudies.filter((c) => c.temporal_tag === 'historical').length },
          { id: 'analyzable' as FilterTag, label: 'Fully Analyzable', count: caseStudies.filter((c) => c.readiness === 'READY_TO_ANALYZE').length },
          { id: 'awaiting_data' as FilterTag, label: 'Awaiting Data', count: caseStudies.filter((c) => c.readiness === 'AWAITING_ADDITIONAL_DATA').length },
          { id: 'offline_demo' as FilterTag, label: 'Offline Demo', count: caseStudies.filter((c) => c.region_tag === 'offline_demo').length },
        ].map((f) => {
          const isActive = activeFilter === f.id;
          return (
            <button
              key={f.id}
              onClick={() => setActiveFilter(f.id)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-all duration-200 border flex items-center gap-2 ${
                isActive
                  ? 'bg-terra-forest text-terra-ivory border-terra-mint/40 shadow-sm'
                  : 'bg-terra-dark/40 text-terra-muted border-terra-border/50 hover:bg-terra-forest/40 hover:text-terra-ivory'
              }`}
            >
              <span>{f.label}</span>
              <span
                className={`px-1.5 py-0.5 rounded-full text-[10px] font-mono ${
                  isActive ? 'bg-terra-mint/20 text-terra-mint' : 'bg-terra-border/50 text-terra-slate'
                }`}
              >
                {f.count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Loading & Error States */}
      {isLoading && (
        <div className="p-12 text-center glass-panel rounded-2xl border border-terra-border/50">
          <div className="w-8 h-8 border-2 border-terra-mint border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-xs text-terra-muted">Loading authoritative disaster case studies...</p>
        </div>
      )}

      {loadError && (
        <div className="p-6 rounded-2xl bg-red-950/20 border border-red-500/30 text-red-200 text-xs flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
          <div>{loadError}</div>
        </div>
      )}

      {/* Case Studies Grid */}
      {!isLoading && !loadError && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredCases.map((c) => {
            const vBadge = getVerificationBadge(c.verification_status);
            const rBadge = getReadinessBadge(c.readiness);
            const isOffline = c.region_tag === 'offline_demo';
            const isLaunching = launchingCaseId === c.id;
            const isActiveWorkspace = Boolean(
              activeProjectId &&
                (c.linked_project_id === activeProjectId ||
                  `proj_case_${c.id}` === activeProjectId)
            );

            return (
              <motion.div
                key={c.id}
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className={`glass-panel p-5 rounded-2xl border transition-all duration-200 flex flex-col justify-between group hover:shadow-lg hover:shadow-black/20 ${
                  isActiveWorkspace ? 'border-terra-mint/70 ring-1 ring-terra-mint/40 bg-terra-forest/30' : 'border-terra-border/60 hover:border-terra-mint/40'
                }`}
              >
                <div className="space-y-3.5">
                  {/* Top Badges */}
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <span
                      className={`px-2.5 py-1 rounded-full text-[10.5px] font-semibold border flex items-center gap-1.5 ${vBadge.bg}`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${vBadge.dot}`} />
                      {vBadge.label}
                    </span>
                    <div className="flex items-center gap-1.5">
                      {isActiveWorkspace && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-semibold flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                          Active
                        </span>
                      )}
                      <span
                        className={`px-2 py-0.5 rounded-md text-[10px] font-mono border ${rBadge.bg}`}
                      >
                        {rBadge.label}
                      </span>
                    </div>
                  </div>

                  {/* Title & Location */}
                  <div>
                    <h3 className="text-base font-bold text-terra-ivory group-hover:text-terra-mint transition-colors duration-150 font-serif leading-snug">
                      {c.name}
                    </h3>
                    <div className="flex items-center gap-1.5 text-xs text-terra-muted mt-1">
                      <MapPin className="w-3.5 h-3.5 text-terra-slate shrink-0" />
                      <span className="truncate">
                        {c.locality ? `${c.locality}, ` : ''}
                        {c.district ? `${c.district}, ` : ''}
                        {c.state_province}, {c.country}
                      </span>
                    </div>
                  </div>

                  {/* Key Metadata Table */}
                  <div className="p-3 rounded-xl bg-terra-deep/50 border border-terra-border/40 grid grid-cols-2 gap-2 text-[11px] font-mono">
                    <div>
                      <div className="text-terra-slate text-[9.5px] uppercase">Event Date</div>
                      <div className="text-terra-ivory font-medium flex items-center gap-1 mt-0.5 truncate">
                        <Calendar className="w-3 h-3 text-terra-mint shrink-0" />
                        <span className="truncate">{c.event_date}</span>
                      </div>
                    </div>
                    <div>
                      <div className="text-terra-slate text-[9.5px] uppercase">Disaster Type</div>
                      <div className="text-terra-ivory font-medium truncate mt-0.5" title={c.disaster_type}>
                        {c.disaster_type}
                      </div>
                    </div>
                  </div>

                  {/* Short Description */}
                  <p className="text-xs text-terra-slate line-clamp-3 leading-relaxed">
                    {c.short_description}
                  </p>

                  {/* Available Datasets Checklist */}
                  <div className="space-y-1.5 pt-1 border-t border-terra-border/40">
                    <div className="text-[10px] font-mono uppercase tracking-wider text-terra-slate">
                      Source Data Availability
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {c.terrain_datasets.map((td, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded-md bg-terra-dark/60 border border-terra-border text-[10px] font-mono text-terra-muted"
                          title={`${td.name} (${td.provider})`}
                        >
                          🏔 {td.resolution_m}m DEM ({td.status})
                        </span>
                      ))}
                      {c.vegetation_datasets.map((vd, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded-md bg-terra-dark/60 border border-terra-border text-[10px] font-mono text-terra-muted"
                          title={`${vd.name} (${vd.provider})`}
                        >
                          🌿 {vd.resolution_m}m NDVI
                        </span>
                      ))}
                      {c.observed_landslide_inventory ? (
                        <span className="px-2 py-0.5 rounded-md bg-emerald-950/40 border border-emerald-500/30 text-[10px] font-mono text-emerald-300">
                          📍 {c.observed_landslide_inventory.features?.length || 0} Observed Features
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-md bg-slate-900/40 border border-slate-700 text-[10px] font-mono text-slate-400">
                          {isOffline ? 'Synthetic Fixture' : 'Inventory Pending'}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Offline / Limitation Notice */}
                  {isOffline ? (
                    <div className="text-[10.5px] text-amber-300/80 bg-amber-950/20 border border-amber-500/20 p-2 rounded-lg leading-tight">
                      ⚠️ Purely synthetic test DEM for local offline benchmarking. Not observations from a real disaster.
                    </div>
                  ) : c.known_limitations?.length > 0 ? (
                    <div className="text-[10.5px] text-terra-slate bg-terra-dark/40 border border-terra-border/50 p-2 rounded-lg leading-tight line-clamp-2">
                      <span className="font-semibold text-terra-muted">Known Caveat: </span>
                      {c.known_limitations[0]}
                    </div>
                  ) : null}
                </div>

                {/* Actions */}
                <div className="pt-4 mt-4 border-t border-terra-border/40 flex items-center gap-2">
                  <button
                    onClick={() => handleExplore(c)}
                    disabled={isLaunching}
                    className="flex-1 py-2 px-3 rounded-xl bg-terra-forest hover:bg-terra-mint hover:text-terra-deep text-terra-ivory font-semibold text-xs transition-all duration-150 flex items-center justify-center gap-1.5 shadow-sm disabled:opacity-50"
                  >
                    {isLaunching ? (
                      <>
                        <div className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                        <span>Loading Workspace...</span>
                      </>
                    ) : (
                      <>
                        <span>Explore Case Study</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => openDossier(c)}
                    title="View Authoritative Dossier & Citations"
                    className="p-2 rounded-xl bg-terra-dark/60 hover:bg-terra-forest/40 border border-terra-border text-terra-muted hover:text-terra-ivory transition-colors text-xs flex items-center gap-1"
                  >
                    <FileText className="w-4 h-4" />
                    <span className="hidden sm:inline">Dossier</span>
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Scientific Dossier Modal */}
      <AnimatePresence>
        {isDossierOpen && selectedCase && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/75 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="glass-panel w-full max-w-4xl max-h-[90vh] rounded-2xl border border-terra-border shadow-2xl flex flex-col overflow-hidden bg-terra-deep/95"
            >
              {/* Modal Header */}
              <div className="p-5 sm:p-6 border-b border-terra-border/60 flex items-start justify-between gap-4 bg-terra-dark/80">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono border bg-terra-forest text-terra-mint border-terra-mint/30 uppercase">
                      Scientific Case Dossier
                    </span>
                    <span className="text-xs font-mono text-terra-slate">{selectedCase.id}</span>
                  </div>
                  <h2 className="text-lg sm:text-xl font-bold text-terra-ivory font-serif">
                    {selectedCase.name}
                  </h2>
                  <p className="text-xs text-terra-muted">
                    {selectedCase.locality}, {selectedCase.district}, {selectedCase.state_province}, {selectedCase.country}
                  </p>
                </div>
                <button
                  onClick={() => setIsDossierOpen(false)}
                  className="p-1.5 rounded-xl hover:bg-terra-forest text-terra-muted hover:text-terra-ivory transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Dossier Tabs */}
              <div className="flex border-b border-terra-border/50 px-6 bg-terra-dark/40 overflow-x-auto scrollbar-none text-xs">
                {[
                  { id: 'overview' as const, label: 'Overview & Geography', icon: MapPin },
                  { id: 'sources' as const, label: 'Authoritative Citations', icon: BookOpen },
                  { id: 'data' as const, label: 'Datasets & Licensing', icon: Database },
                  { id: 'inventory' as const, label: 'Observed Footprint', icon: Layers },
                  { id: 'comparison' as const, label: 'Historical Comparison', icon: Scale },
                  { id: 'limitations' as const, label: 'Caveats & Limitations', icon: AlertTriangle },
                ].map((t) => {
                  const Icon = t.icon;
                  const isActive = dossierTab === t.id;
                  return (
                    <button
                      key={t.id}
                      onClick={() => setDossierTab(t.id)}
                      className={`py-3 px-3.5 border-b-2 font-medium flex items-center gap-2 whitespace-nowrap transition-colors ${
                        isActive
                          ? 'border-terra-mint text-terra-ivory'
                          : 'border-transparent text-terra-slate hover:text-terra-muted'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      <span>{t.label}</span>
                    </button>
                  );
                })}
              </div>

              {/* Modal Body */}
              <div className="p-6 overflow-y-auto space-y-5 text-xs text-terra-slate max-h-[60vh]">
                {dossierTab === 'overview' && (
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-terra-mint mb-2">
                        Event Summary & Disaster Context
                      </h4>
                      <p className="text-terra-ivory leading-relaxed text-sm">
                        {selectedCase.short_description}
                      </p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                      <div className="p-3 rounded-xl bg-terra-dark/60 border border-terra-border space-y-1">
                        <div className="text-[10px] font-mono text-terra-slate uppercase">Documented Event Date</div>
                        <div className="text-sm font-bold text-terra-ivory flex items-center gap-1.5">
                          <Calendar className="w-4 h-4 text-terra-mint" />
                          <span>{selectedCase.event_date}</span>
                        </div>
                      </div>
                      <div className="p-3 rounded-xl bg-terra-dark/60 border border-terra-border space-y-1">
                        <div className="text-[10px] font-mono text-terra-slate uppercase">Disaster Classification</div>
                        <div className="text-sm font-bold text-terra-ivory truncate">{selectedCase.disaster_type}</div>
                      </div>
                      <div className="p-3 rounded-xl bg-terra-dark/60 border border-terra-border space-y-1">
                        <div className="text-[10px] font-mono text-terra-slate uppercase">Geometry Provenance</div>
                        <div className="text-xs text-terra-muted">{selectedCase.geometry_provenance}</div>
                        <div className="text-[10px] font-mono text-terra-mint">Confidence: {selectedCase.geometry_confidence}</div>
                      </div>
                      <div className="p-3 rounded-xl bg-terra-dark/60 border border-terra-border space-y-1">
                        <div className="text-[10px] font-mono text-terra-slate uppercase">Study Area Extent</div>
                        <div className="text-xs font-mono text-terra-ivory">
                          {selectedCase.study_area_ha ? `${selectedCase.study_area_ha.toLocaleString()} ha` : 'Regional AOI'}
                        </div>
                        <div className="text-[10px] font-mono text-terra-slate">
                          Bounds: [{selectedCase.bounds.minx.toFixed(2)}, {selectedCase.bounds.miny.toFixed(2)}, {selectedCase.bounds.maxx.toFixed(2)}, {selectedCase.bounds.maxy.toFixed(2)}]
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {dossierTab === 'sources' && (
                  <div className="space-y-3">
                    <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-terra-mint mb-2">
                      Authoritative Government & Scientific Citations ({selectedCase.source_references.length})
                    </h4>
                    {selectedCase.source_references.map((src, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 rounded-xl bg-terra-dark/60 border border-terra-border/70 space-y-1.5"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="font-bold text-terra-ivory text-xs sm:text-sm">{src.title}</div>
                          {src.publication_year && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-terra-forest text-terra-mint border border-terra-mint/20">
                              {src.publication_year}
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-terra-muted font-medium flex items-center gap-2">
                          <span>{src.organization}</span>
                          <span>•</span>
                          <span className="text-terra-slate italic">{src.document_type}</span>
                        </div>
                        {src.verification_notes && (
                          <div className="text-[11px] text-terra-slate bg-terra-deep/50 p-2 rounded-lg border border-terra-border/40">
                            <b>Verification Notes: </b> {src.verification_notes}
                          </div>
                        )}
                        {src.url && (
                          <a
                            href={src.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-[11px] text-terra-mint hover:underline font-mono"
                          >
                            <span>Official Source Reference</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {dossierTab === 'data' && (
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-terra-mint mb-2">
                        Acquisition Requirements & Open Data Licensing
                      </h4>
                      <p className="text-terra-muted leading-relaxed mb-3">
                        {selectedCase.data_acquisition_requirements}
                      </p>
                      <div className="p-3 rounded-xl bg-terra-deep/70 border border-terra-border text-xs text-terra-slate">
                        <span className="font-semibold text-terra-ivory">Licensing & Terms: </span>
                        {selectedCase.licensing_and_attribution}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <h5 className="text-[11px] font-mono text-terra-mint uppercase tracking-wider">
                        Available Terrain & Elevation Layers
                      </h5>
                      {selectedCase.terrain_datasets.map((td, idx) => (
                        <div key={idx} className="p-3 rounded-xl bg-terra-dark/60 border border-terra-border flex items-center justify-between gap-2">
                          <div>
                            <div className="font-semibold text-terra-ivory">{td.name}</div>
                            <div className="text-[11px] text-terra-muted">{td.provider} • Resolution: {td.resolution_m}m</div>
                            {td.notes && <div className="text-[10px] text-terra-slate mt-0.5">{td.notes}</div>}
                          </div>
                          <span className="px-2 py-1 rounded-md text-[10px] font-mono bg-terra-forest text-terra-mint border border-terra-mint/20">
                            {td.status}
                          </span>
                        </div>
                      ))}
                    </div>

                    <div className="space-y-2">
                      <h5 className="text-[11px] font-mono text-terra-mint uppercase tracking-wider">
                        Available Multispectral Vegetation Layers
                      </h5>
                      {selectedCase.vegetation_datasets.length > 0 ? (
                        selectedCase.vegetation_datasets.map((vd, idx) => (
                          <div key={idx} className="p-3 rounded-xl bg-terra-dark/60 border border-terra-border flex items-center justify-between gap-2">
                            <div>
                              <div className="font-semibold text-terra-ivory">{vd.name}</div>
                              <div className="text-[11px] text-terra-muted">{vd.provider} • Resolution: {vd.resolution_m}m</div>
                              {vd.notes && <div className="text-[10px] text-terra-slate mt-0.5">{vd.notes}</div>}
                            </div>
                            <span className="px-2 py-1 rounded-md text-[10px] font-mono bg-terra-forest text-terra-mint border border-terra-mint/20">
                              {vd.status}
                            </span>
                          </div>
                        ))
                      ) : (
                        <div className="p-3 rounded-xl bg-terra-dark/40 border border-terra-border/50 text-terra-slate text-xs italic">
                          No multispectral imagery bundled. Acquirable via Planetary Computer Sentinel-2 STAC.
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {dossierTab === 'inventory' && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-terra-mint">
                        Documented Disaster Event Features
                      </h4>
                      <span className="text-[11px] font-mono text-terra-slate">
                        {selectedCase.observed_landslide_inventory?.features?.length || 0} Features Mapped
                      </span>
                    </div>

                    <p className="text-terra-muted text-xs">
                      {selectedCase.inventory_summary}
                    </p>

                    {selectedCase.observed_landslide_inventory?.features?.map((f: any, idx: number) => {
                      const p = f.properties || {};
                      const isPoly = f.geometry?.type?.toLowerCase().includes('polygon');
                      return (
                        <div
                          key={idx}
                          className="p-3.5 rounded-xl bg-terra-dark/60 border border-terra-border/70 space-y-1"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div className="font-bold text-terra-ivory text-xs flex items-center gap-1.5">
                              <span>{isPoly ? '🗺' : '📍'}</span>
                              <span>{p.name || f.id || `Feature #${idx + 1}`}</span>
                            </div>
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/15 text-amber-300 border border-amber-500/30">
                              {p.feature_type || 'Observed Landslide'}
                            </span>
                          </div>
                          {p.description && (
                            <div className="text-xs text-terra-muted">{p.description}</div>
                          )}
                          <div className="flex items-center gap-3 text-[10px] font-mono text-terra-slate pt-1">
                            {p.elevation_m && <span>Elevation: {p.elevation_m}m</span>}
                            {p.runout_length_km && <span>Runout: {p.runout_length_km} km</span>}
                            {p.area_ha && <span>Area: {p.area_ha} ha</span>}
                            {p.source && <span className="truncate">Source: {p.source}</span>}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {dossierTab === 'comparison' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between gap-2">
                      <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-terra-mint">
                        Retrospective Co-Location Comparison
                      </h4>
                      {selectedCase.observed_landslide_inventory && (
                        <button
                          onClick={() => handleRunComparison(selectedCase.id)}
                          disabled={isComparing}
                          className="px-3 py-1.5 rounded-lg bg-terra-forest hover:bg-terra-mint hover:text-terra-deep text-terra-ivory text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
                        >
                          {isComparing ? (
                            <>
                              <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                              <span>Evaluating Overlay...</span>
                            </>
                          ) : (
                            <>
                              <Scale className="w-3.5 h-3.5" />
                              <span>Compute Spatial Overlay</span>
                            </>
                          )}
                        </button>
                      )}
                    </div>

                    <div className="p-3 rounded-xl bg-amber-950/20 border border-amber-500/30 text-[11px] text-amber-200 leading-snug">
                      <b>SCIENTIFIC MANDATE: </b> Retrospective spatial overlay between historical disaster
                      features and modelled stability concern zones evaluates physical co-location under baseline
                      geometry. It must NEVER be represented as predictive forecasting accuracy or true positive rates.
                    </div>

                    {comparisonError && (
                      <div className="p-3 rounded-xl bg-red-950/20 border border-red-500/30 text-red-300 text-xs">
                        {comparisonError}
                      </div>
                    )}

                    {comparisonResult ? (
                      <div className="space-y-3">
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center font-mono">
                          <div className="p-3 rounded-xl bg-terra-dark/60 border border-terra-border">
                            <div className="text-[10px] text-terra-slate">Observed Features</div>
                            <div className="text-base font-bold text-terra-ivory mt-0.5">
                              {comparisonResult.total_observed_features}
                            </div>
                          </div>
                          <div className="p-3 rounded-xl bg-terra-dark/60 border border-terra-border">
                            <div className="text-[10px] text-terra-slate">Intersecting Grid</div>
                            <div className="text-base font-bold text-terra-mint mt-0.5">
                              {comparisonResult.features_intersecting_grid} ({comparisonResult.grid_intersection_percentage}%)
                            </div>
                          </div>
                          <div className="p-3 rounded-xl bg-terra-dark/60 border border-terra-border">
                            <div className="text-[10px] text-terra-slate">In Concern Zone (FS &lt; 1.3)</div>
                            <div className="text-base font-bold text-amber-300 mt-0.5">
                              {comparisonResult.features_in_modeled_concern_zone} ({comparisonResult.concern_zone_overlap_percentage}%)
                            </div>
                          </div>
                          <div className="p-3 rounded-xl bg-terra-dark/60 border border-terra-border">
                            <div className="text-[10px] text-terra-slate">FS Threshold</div>
                            <div className="text-base font-bold text-terra-slate mt-0.5">
                              {comparisonResult.concern_fs_threshold_used}
                            </div>
                          </div>
                        </div>

                        {/* Feature Details Table */}
                        <div className="space-y-1.5">
                          <div className="text-[11px] font-mono text-terra-slate uppercase">Feature Co-Location Breakdown</div>
                          {comparisonResult.feature_details.map((fd, idx) => (
                            <div
                              key={idx}
                              className="p-2.5 rounded-lg bg-terra-dark/40 border border-terra-border/50 text-xs flex items-center justify-between gap-2"
                            >
                              <div>
                                <span className="font-semibold text-terra-ivory">{fd.feature_name}</span>
                                <span className="text-terra-slate text-[10px] ml-2 font-mono">({fd.feature_type})</span>
                              </div>
                              <div className="text-right font-mono text-[11px]">
                                {fd.within_stability_concern_zone ? (
                                  <span className="text-amber-300 font-semibold">In Concern Zone (FS₀: {fd.min_modeled_baseline_fs})</span>
                                ) : (
                                  <span className="text-terra-slate">Beyond Grid or FS &gt; 1.3</span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="p-6 text-center text-terra-slate bg-terra-dark/30 rounded-xl border border-terra-border/40">
                        {parcelsGeojson || latestRunId ? (
                          <span>Click "Compute Spatial Overlay" above to evaluate geometric intersection with the active analysis run.</span>
                        ) : (
                          <span>Launch and run this case study to generate candidate parcels before computing retrospective spatial overlay.</span>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {dossierTab === 'limitations' && (
                  <div className="space-y-3">
                    <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-terra-mint mb-2">
                      Documented Methodological Limitations & Known Constraints
                    </h4>
                    <p className="text-terra-muted text-xs leading-relaxed mb-3">
                      TerraShield AI transparently reports analytical constraints to prevent over-reliance on
                      regional numerical models during active geohazard management.
                    </p>
                    {selectedCase.known_limitations.map((lim, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl bg-terra-dark/60 border border-terra-border/60 flex items-start gap-2.5 text-xs text-terra-slate leading-relaxed"
                      >
                        <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                        <div>{lim}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div className="p-5 border-t border-terra-border/60 flex items-center justify-between bg-terra-dark/80">
                <button
                  onClick={() => setIsDossierOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs text-terra-muted hover:text-terra-ivory"
                >
                  Close Dossier
                </button>

                <button
                  onClick={() => {
                    setIsDossierOpen(false);
                    handleExplore(selectedCase);
                  }}
                  className="px-4 py-2 rounded-xl bg-terra-forest hover:bg-terra-mint hover:text-terra-deep text-terra-ivory font-semibold text-xs transition-colors flex items-center gap-1.5"
                >
                  <span>Open Dedicated Workspace</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
