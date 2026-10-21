import React, { useState, useMemo, useEffect, useRef } from 'react';
import type { ProjectMetadata, RecommendationRunResponse, CaseStudy } from '../api/types';
import { api } from '../api/client';
import { TextEffect } from '../components/motion-primitives/TextEffect';
import { InView } from '../components/motion-primitives/InView';
import { MetricCard } from '../components/common/MetricCard';
import { ProvenanceBanner } from '../components/common/ProvenanceBanner';
import { MapCanvas, type StudyAreaSelection } from '../components/map/MapCanvas';
import { calculatePolygonAreaHa } from '../utils/geo';
import { normalizeBounds } from '../utils/normalize';
import {
  ArrowRight,
  MapPin,
  Trees,
  Mountain,
  Sparkles,
  BarChart3,
  Compass,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Sliders,
  Layers,
  BookOpen,
  Calendar,
  FileText,
  PlayCircle,
  Activity,
  History,
  Info,
} from 'lucide-react';

interface OverviewViewProps {
  activeProject: ProjectMetadata | null;
  projects?: ProjectMetadata[];
  latestRun: RecommendationRunResponse | null;
  parcelsGeojson?: any;
  onStartAnalysis: () => void;
  onOpenDataLibrary: () => void;
  onSelectProject?: (id: string) => void;
  onOpenResults?: () => void;
  onOpenCreateModal?: () => void;
  onAnalysisComplete?: (results: RecommendationRunResponse, geojson?: any) => void;
  onNavigateTab?: (tab: string) => void;
  onExploreCaseStudy?: (caseId: string) => Promise<void>;
}

const STAGES = [
  { num: 1, title: 'Validating selected area', desc: 'Verifying coordinate limits and topology' },
  { num: 2, title: 'Searching public datasets', desc: 'Querying Microsoft Planetary Computer STAC' },
  { num: 3, title: 'Acquiring elevation data', desc: 'Downloading 30m Copernicus / NASA DEM' },
  { num: 4, title: 'Acquiring vegetation imagery', desc: 'Retrieving Sentinel-2 L2A Red & NIR bands' },
  { num: 5, title: 'Processing terrain derivatives', desc: "Calculating Horn's slope and compass aspect" },
  { num: 6, title: 'Modeling geotechnical stability', desc: 'Computing infinite-slope baseline & reinforced FS' },
  { num: 7, title: 'Evaluating candidate parcels', desc: 'Tessellating study area & applying eligibility filters' },
  { num: 8, title: 'Ranking restoration priority', desc: 'Multi-criteria composite scoring & Pareto ranking' },
  { num: 9, title: 'Preparing final results', desc: 'Generating GeoJSON polygons and metrics summary' },
];

export const OverviewView: React.FC<OverviewViewProps> = ({
  activeProject,
  projects = [],
  latestRun,
  parcelsGeojson,
  onStartAnalysis,
  onOpenDataLibrary,
  onSelectProject,
  onOpenResults,
  onAnalysisComplete,
  onNavigateTab,
  onExploreCaseStudy,
}) => {
  // Area selection state
  const [selectedArea, setSelectedArea] = useState<StudyAreaSelection | null>(null);
  const [analysisName, setAnalysisName] = useState<string>('');
  const [geotechPreset, setGeotechPreset] = useState<string>('wayanad_saprolite');
  const [priorityPreset, setPriorityPreset] = useState<'balanced' | 'landslide' | 'plantable'>('balanced');
  const [cellSizeM, setCellSizeM] = useState<number>(250);

  // Case Studies state
  const [caseStudies, setCaseStudies] = useState<CaseStudy[]>([]);
  const [caseFilter, setCaseFilter] = useState<'all' | 'western_ghats' | 'himalayas' | 'nepal' | 'recent'>('all');
  const [fetchedInventory, setFetchedInventory] = useState<{ caseId: string; data: any } | null>(null);

  // Analysis execution state
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [currentStage, setCurrentStage] = useState<number>(1);
  const [stageTitle, setStageTitle] = useState<string>('');
  const [stageMessage, setStageMessage] = useState<string>('');
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [completedAnalysis, setCompletedAnalysis] = useState<RecommendationRunResponse | null>(null);
  const [activeParcelsGeojson, setActiveParcelsGeojson] = useState<any>(null);

  // Ref for smooth scrolling to the area analyzer
  const areaAnalyzerRef = useRef<HTMLDivElement>(null);

  // Load Case Studies
  useEffect(() => {
    let isSubscribed = true;
    api
      .getCaseStudies()
      .then((data) => {
        if (isSubscribed) setCaseStudies(data || []);
      })
      .catch(() => {});
    return () => {
      isSubscribed = false;
    };
  }, []);

  const activeCaseId = useMemo(() => {
    if (!activeProject) return null;
    if (activeProject.id === 'wayanad_pilot') return 'wayanad_2024';
    if (activeProject.id === 'cascade_demo') return 'cascade_demo';
    if (activeProject.id.startsWith('proj_case_')) return activeProject.id.replace('proj_case_', '');
    return null;
  }, [activeProject]);

  const observedInventory = fetchedInventory?.caseId === activeCaseId ? fetchedInventory.data : null;

  useEffect(() => {
    if (!activeCaseId) return;
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

  const bounds = useMemo(() => normalizeBounds(activeProject?.bounds), [activeProject?.bounds]);
  const hasRuns = (activeProject?.saved_runs && activeProject.saved_runs.length > 0) || Boolean(latestRun);

  // Authoritative Study Area Calculation
  const authoritativeStudyAreaHa = useMemo(() => {
    if (selectedArea && selectedArea.areaHa > 0) {
      return selectedArea.areaHa;
    }
    if (activeProject?.boundary_geojson?.features?.length) {
      try {
        const coords = activeProject.boundary_geojson.features[0]?.geometry?.coordinates?.[0];
        if (coords && coords.length >= 3) {
          const a = calculatePolygonAreaHa(coords);
          if (a > 0) return Math.round(a * 100) / 100;
        }
      } catch {
        // ignore
      }
    }
    const b = activeProject?.bounds || (bounds.maxx > bounds.minx ? bounds : null);
    if (b && b.maxx > b.minx && b.maxy > b.miny) {
      const midLatRad = ((b.miny + b.maxy) / 2) * (Math.PI / 180);
      const mPerDegLat = 111132.954;
      const mPerDegLon = 111412.84 * Math.cos(midLatRad);
      const widthM = (b.maxx - b.minx) * mPerDegLon;
      const heightM = (b.maxy - b.miny) * mPerDegLat;
      const areaHa = (widthM * heightM) / 10000;
      return Math.round(areaHa * 100) / 100;
    }
    return 0;
  }, [selectedArea, activeProject, bounds]);

  const activeRun = isAnalyzing ? null : (completedAnalysis || latestRun);

  // Handle execution of analysis
  const handleExecuteAutoAnalyze = async () => {
    // If no boundary drawn and no project selected, scroll to map
    const targetBounds = selectedArea?.bounds || activeProject?.bounds || (bounds.maxx > bounds.minx ? bounds : null);
    const targetGeojson = selectedArea?.boundaryGeojson || activeProject?.boundary_geojson;

    if (!targetBounds && !targetGeojson) {
      setAnalysisError('Please select or draw a target study area on the map canvas below first.');
      areaAnalyzerRef.current?.scrollIntoView({ behavior: 'smooth' });
      return;
    }

    setIsAnalyzing(true);
    setAnalysisError(null);
    setCurrentStage(1);
    setStageTitle('Validating selected area');
    setStageMessage('Verifying coordinates, topology, and study area size...');
    setCompletedAnalysis(null);
    setActiveParcelsGeojson(null);

    // Scroll to interactive analyzer so user sees progress
    areaAnalyzerRef.current?.scrollIntoView({ behavior: 'smooth' });

    try {
      const launchRes = await api.autoAnalyze({
        name: analysisName.trim() || activeProject?.name || undefined,
        project_id: activeProject?.id,
        bounds: targetBounds || undefined,
        boundary_geojson: targetGeojson,
        geotech_preset_id: geotechPreset,
        cell_size_m: cellSizeM,
        priority_preset: priorityPreset,
        async_job: true,
      });

      const jobId = launchRes.job_id;

      let consecutiveErrors = 0;
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await api.getAutoAnalyzeStatus(jobId);
          consecutiveErrors = 0;
          if (statusRes.stage_number) {
            setCurrentStage(statusRes.stage_number);
          }
          if (statusRes.stage_title) {
            setStageTitle(statusRes.stage_title);
          }
          if (statusRes.stage_message) {
            setStageMessage(statusRes.stage_message);
          }

          if (statusRes.status === 'COMPLETED') {
            clearInterval(pollInterval);
            setIsAnalyzing(false);
            const recRun = statusRes.result?.recommendation_run;
            const directGeo = statusRes.result?.parcels_geojson;

            if (directGeo) {
              setActiveParcelsGeojson(directGeo);
              if (recRun) {
                setCompletedAnalysis(recRun);
                onAnalysisComplete?.(recRun, directGeo);
              }
            } else if (recRun) {
              setCompletedAnalysis(recRun);
              const artId = recRun.artifacts?.parcels_geojson || recRun.artifacts?.geojson;
              if (artId) {
                api
                  .fetchArtifactJson(artId)
                  .then((geo) => {
                    setActiveParcelsGeojson(geo);
                    onAnalysisComplete?.(recRun, geo);
                  })
                  .catch((e) => {
                    console.warn('Could not load artifact GeoJSON:', e);
                    onAnalysisComplete?.(recRun);
                  });
              } else {
                onAnalysisComplete?.(recRun);
              }
            }

            if (statusRes.result?.project_id && onSelectProject) {
              onSelectProject(statusRes.result.project_id);
            }
          } else if (statusRes.status === 'FAILED') {
            clearInterval(pollInterval);
            setIsAnalyzing(false);
            setActiveParcelsGeojson(null);
            setCompletedAnalysis(null);
            setAnalysisError(statusRes.error || 'Automated analysis pipeline failed.');
          }
        } catch (pollErr: any) {
          consecutiveErrors++;
          console.warn('Job polling error:', pollErr);
          if (consecutiveErrors >= 5) {
            clearInterval(pollInterval);
            setIsAnalyzing(false);
            setActiveParcelsGeojson(null);
            setAnalysisError(pollErr.message || 'Connection lost while polling analysis job.');
          }
        }
      }, 1500);
    } catch (err: any) {
      setIsAnalyzing(false);
      setActiveParcelsGeojson(null);
      setAnalysisError(err.message || 'Failed to start automated analysis.');
    }
  };

  const scrollToAnalyzer = () => {
    areaAnalyzerRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="space-y-10 pb-16 animate-fade-in text-slate-800">
      {/* ========================================================
          1. CINEMATIC NATURE HERO SECTION
          Matches the reference image with misty peaks, deep forest,
          refined typography, and floating analysis panel.
      ======================================================== */}
      <section className="relative w-full rounded-2xl sm:rounded-3xl overflow-hidden shadow-2xl border border-white/10 min-h-[580px] sm:min-h-[620px] flex flex-col justify-between">
        {/* Mountain Landscape Background */}
        <div
          className="absolute inset-0 bg-cover bg-center transition-transform duration-1000 scale-[1.01]"
          style={{
            backgroundImage: `url('/backgrounds/cinematic-terrain-hero.jpg')`,
            backgroundPosition: 'center 40%',
          }}
        />

        {/* Refined Teal / Dark Forest Nature Gradient Overlay */}
        <div className="absolute inset-0 bg-gradient-to-b from-[#061d17]/85 via-[#082b22]/55 to-[#071c17]/95" />

        {/* Subtle Atmospheric Top Light Texture */}
        <div className="absolute top-0 inset-x-0 h-40 bg-gradient-to-b from-white/10 to-transparent pointer-events-none" />

        {/* Hero Content Center */}
        <div className="relative z-10 px-6 sm:px-10 lg:px-14 pt-12 sm:pt-16 pb-6 max-w-4xl space-y-5">
          {/* Nature Intel Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/15 backdrop-blur-md border border-white/20 text-white text-xs font-semibold shadow-xs">
            <Sparkles className="w-3.5 h-3.5 text-emerald-300" />
            <span className="font-mono tracking-wider text-[11px] uppercase">
              GEOSPATIAL INTELLIGENCE &amp; LANDSCAPE RESTORATION
            </span>
          </div>

          {/* Suggested Hero Headline */}
          <TextEffect
            as="h1"
            per="word"
            className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-display font-extrabold text-white tracking-tight leading-[1.12]"
          >
            Find Where Restoration Can Make the Greatest Difference.
          </TextEffect>

          {/* Supporting Text */}
          <p className="text-emerald-100/90 text-sm sm:text-base md:text-lg leading-relaxed max-w-2xl font-normal">
            Analyse terrain, evaluate modelled slope stability, and prioritise candidate restoration sites using geospatial intelligence.
          </p>

          {/* Two Carefully Styled Action Buttons */}
          <div className="flex flex-wrap items-center gap-3 pt-3">
            <button
              onClick={scrollToAnalyzer}
              className="px-6 py-3.5 rounded-full bg-emerald-500 hover:bg-emerald-400 text-[#071d17] font-bold text-xs sm:text-sm transition-all shadow-lg shadow-emerald-950/40 flex items-center gap-2 cursor-pointer group active:scale-95"
            >
              <span>Analyse a Site</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>

            <button
              onClick={() => onNavigateTab?.('map')}
              className="px-6 py-3.5 rounded-full bg-white/15 hover:bg-white/25 backdrop-blur-md text-white font-semibold text-xs sm:text-sm border border-white/25 transition-all flex items-center gap-2 cursor-pointer active:scale-95 shadow-xs"
            >
              <Compass className="w-4 h-4 text-emerald-300" />
              <span>Explore the Map</span>
            </button>
          </div>
        </div>

        {/* ========================================================
            2. THE FLOATING ANALYSIS PANEL
            Directly inspired by the search bar in the reference image.
            Horizontal, clean, pill-shaped with real application fields.
        ======================================================== */}
        <div className="relative z-20 px-4 sm:px-6 lg:px-8 pb-6 sm:pb-8">
          <div className="max-w-5xl mx-auto rounded-2xl sm:rounded-full bg-white/95 backdrop-blur-xl border border-slate-200/90 shadow-[0_20px_50px_rgba(0,0,0,0.35)] p-3 sm:p-2.5 transition-all">
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 sm:gap-2">
              {/* Field 1: STUDY AREA */}
              <div className="flex-1 px-3 py-1.5 sm:border-r border-slate-200/80">
                <span className="block text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 mb-0.5">
                  1. Study Area
                </span>
                <div className="flex items-center gap-2">
                  <MapPin className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  <select
                    value={selectedArea ? 'custom' : (activeProject?.id || '')}
                    onChange={(e) => {
                      if (e.target.value === 'custom') {
                        scrollToAnalyzer();
                      } else if (onSelectProject) {
                        setSelectedArea(null);
                        onSelectProject(e.target.value);
                      }
                    }}
                    className="w-full bg-transparent text-slate-800 text-xs sm:text-sm font-semibold focus:outline-none cursor-pointer truncate"
                  >
                    {selectedArea && (
                      <option value="custom" className="text-emerald-700 font-bold">
                        Custom Boundary ({selectedArea.areaHa.toLocaleString()} ha)
                      </option>
                    )}
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} {p.id === 'wayanad_pilot' ? '(Demonstration AOI)' : ''}
                      </option>
                    ))}
                    {projects.length === 0 && (
                      <option value="">Wayanad Catchment Corridor</option>
                    )}
                  </select>
                </div>
              </div>

              {/* Field 2: ANALYSIS MODE */}
              <div className="flex-1 px-3 py-1.5 sm:border-r border-slate-200/80">
                <span className="block text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 mb-0.5">
                  2. Analysis Mode
                </span>
                <div className="flex items-center gap-2">
                  <Sliders className="w-3.5 h-3.5 text-teal-600 shrink-0" />
                  <select
                    value={priorityPreset}
                    onChange={(e: any) => setPriorityPreset(e.target.value)}
                    className="w-full bg-transparent text-slate-800 text-xs sm:text-sm font-semibold focus:outline-none cursor-pointer"
                  >
                    <option value="balanced">Balanced Multi-Objective</option>
                    <option value="landslide">Landslide Risk Mitigation</option>
                    <option value="plantable">Plantable Area Priority</option>
                  </select>
                </div>
              </div>

              {/* Field 3: GRID RESOLUTION */}
              <div className="flex-1 px-3 py-1.5 sm:border-r border-slate-200/80">
                <span className="block text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 mb-0.5">
                  3. Grid Resolution
                </span>
                <div className="flex items-center gap-2">
                  <Layers className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  <select
                    value={cellSizeM}
                    onChange={(e) => setCellSizeM(Number(e.target.value))}
                    className="w-full bg-transparent text-slate-800 text-xs sm:text-sm font-semibold focus:outline-none cursor-pointer"
                  >
                    <option value="250">250m (Balanced - Recommended)</option>
                    <option value="150">150m (High Detail)</option>
                    <option value="300">300m (Standard Regional)</option>
                    <option value="500">500m (Catchment Level)</option>
                  </select>
                </div>
              </div>

              {/* Field 4: PRIMARY ACTION */}
              <div className="sm:pl-2 shrink-0">
                <button
                  onClick={handleExecuteAutoAnalyze}
                  disabled={isAnalyzing}
                  className={`w-full sm:w-auto px-7 py-3.5 rounded-full font-bold text-xs sm:text-sm transition-all flex items-center justify-center gap-2 shadow-md cursor-pointer ${
                    isAnalyzing
                      ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                      : 'bg-[#0d3b32] hover:bg-[#124d42] text-white active:scale-95 shadow-[#0d3b32]/25'
                  }`}
                >
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin text-white" />
                      <span>Running Pipeline...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 text-emerald-300" />
                      <span>Start Analysis</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Provenance & Scientific Disclosure Banner */}
      <ProvenanceBanner />

      {/* ========================================================
          3. REAL PRODUCT DASHBOARD (BELOW HERO)
          Sections A, B, C, D as defined in requirements.
      ======================================================== */}
      <div className="space-y-8">
        {/* Header Label for Dashboard Area */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200">
          <div>
            <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-emerald-700">
              ENVIRONMENTAL OBSERVATION &amp; MODEL STATUS
            </span>
            <h2 className="text-xl sm:text-2xl font-display font-bold text-slate-900 mt-0.5">
              Study Area Intelligence &amp; Modelled Outputs
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 text-xs font-semibold border border-emerald-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Workspace: {activeProject?.name || 'Active Study Area'}</span>
            </span>
          </div>
        </div>

        {/* SECTION A & B: Summary Metrics Cards */}
        <InView direction="up" delay={0.1}>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Section A: Study Area Size */}
            <MetricCard
              label="Study Area Size"
              value={authoritativeStudyAreaHa}
              suffix=" ha"
              icon={MapPin}
              color="emerald"
              subtext={selectedArea ? "Custom active boundary" : "Project watershed boundary"}
              badge="Boundary"
            />

            {/* Section A: Available Geospatial Layers */}
            <MetricCard
              label="Available GIS Layers"
              value={Object.keys(activeProject?.layers || {}).length}
              icon={Layers}
              color="amber"
              subtext="DEM (30m), NDVI & Slope"
              badge="STAC"
            />

            {/* Section B: Latest Analysis Run Metrics */}
            {activeRun ? (
              <>
                <MetricCard
                  label="Evaluated Parcels"
                  value={activeRun.total_parcels ?? (activeRun as any).parcel_inventory?.total_evaluated ?? 0}
                  icon={Mountain}
                  color="blue"
                  subtext={`Grid cell size ${activeRun.cell_size_m || cellSizeM}m`}
                  badge="Modeled"
                />
                <MetricCard
                  label="Eligible Candidates"
                  value={activeRun.eligible_count ?? (activeRun as any).parcel_inventory?.eligible_count ?? 0}
                  icon={Trees}
                  color="emerald"
                  subtext={`${((activeRun.total_plantable_area_ha ?? (activeRun as any).parcel_inventory?.total_plantable_area_ha) ?? 0).toLocaleString()} ha plantable`}
                  badge="Actionable"
                />
              </>
            ) : (
              <>
                <MetricCard
                  label="Analysis Status"
                  value={isAnalyzing ? 1 : (hasRuns ? 1 : 0)}
                  icon={Activity}
                  color="blue"
                  subtext={isAnalyzing ? 'Computing stability...' : (hasRuns ? 'Prior run ready' : 'No run yet')}
                  badge={isAnalyzing ? 'Running' : (hasRuns ? 'Available' : 'Pending')}
                />
                <MetricCard
                  label="Planting Candidates"
                  value={hasRuns ? (activeProject?.saved_runs?.[0]?.eligible_count || 0) : 0}
                  icon={Trees}
                  color="emerald"
                  subtext={hasRuns ? 'Eligible in saved run' : 'Run analysis to compute'}
                  badge={hasRuns ? 'Available' : 'Pending'}
                />
              </>
            )}
          </div>
        </InView>

        {/* SECTION C: Quick Access Navigation Cards */}
        <InView direction="up" delay={0.15}>
          <div className="space-y-3">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-500">
              Quick Access Modules
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <button
                onClick={() => onNavigateTab?.('map')}
                className="p-5 rounded-2xl bg-white border border-slate-200/90 hover:border-emerald-500/50 hover:shadow-lg transition-all text-left flex flex-col justify-between group cursor-pointer"
              >
                <div className="space-y-2">
                  <div className="w-10 h-10 rounded-xl bg-sky-50 text-sky-700 border border-sky-200 flex items-center justify-center group-hover:scale-105 transition-transform">
                    <Compass className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="font-display font-bold text-slate-900 text-sm group-hover:text-emerald-700 transition-colors">
                      Map Explorer
                    </h4>
                    <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                      Inspect geographic layers, terrain slope, NDVI, and parcel rankings on Leaflet.
                    </p>
                  </div>
                </div>
                <div className="pt-4 flex items-center gap-1.5 text-xs font-semibold text-emerald-700 group-hover:translate-x-1 transition-transform">
                  <span>Open Map</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </button>

              <button
                onClick={() => onNavigateTab?.('results')}
                className="p-5 rounded-2xl bg-white border border-slate-200/90 hover:border-emerald-500/50 hover:shadow-lg transition-all text-left flex flex-col justify-between group cursor-pointer"
              >
                <div className="space-y-2">
                  <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-700 border border-purple-200 flex items-center justify-center group-hover:scale-105 transition-transform">
                    <BarChart3 className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="font-display font-bold text-slate-900 text-sm group-hover:text-emerald-700 transition-colors">
                      Results Dashboard
                    </h4>
                    <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                      Review multi-criteria composite rankings, Pareto frontiers, and eligible parcels.
                    </p>
                  </div>
                </div>
                <div className="pt-4 flex items-center gap-1.5 text-xs font-semibold text-emerald-700 group-hover:translate-x-1 transition-transform">
                  <span>View Results</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </button>

              <button
                onClick={() => onNavigateTab?.('geotech')}
                className="p-5 rounded-2xl bg-white border border-slate-200/90 hover:border-emerald-500/50 hover:shadow-lg transition-all text-left flex flex-col justify-between group cursor-pointer"
              >
                <div className="space-y-2">
                  <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-700 border border-amber-200 flex items-center justify-center group-hover:scale-105 transition-transform">
                    <Sliders className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="font-display font-bold text-slate-900 text-sm group-hover:text-emerald-700 transition-colors">
                      Geotechnical Studio
                    </h4>
                    <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                      Fine-tune cohesion, friction angle, root reinforcement, and Factor of Safety models.
                    </p>
                  </div>
                </div>
                <div className="pt-4 flex items-center gap-1.5 text-xs font-semibold text-emerald-700 group-hover:translate-x-1 transition-transform">
                  <span>Studio Mechanics</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </button>

              <button
                onClick={() => onNavigateTab?.('reports')}
                className="p-5 rounded-2xl bg-white border border-slate-200/90 hover:border-emerald-500/50 hover:shadow-lg transition-all text-left flex flex-col justify-between group cursor-pointer"
              >
                <div className="space-y-2">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-700 border border-blue-200 flex items-center justify-center group-hover:scale-105 transition-transform">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="font-display font-bold text-slate-900 text-sm group-hover:text-emerald-700 transition-colors">
                      Reports &amp; Exports
                    </h4>
                    <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                      Download audit summaries, parcel GeoJSON, CSV metrics, and technical reports.
                    </p>
                  </div>
                </div>
                <div className="pt-4 flex items-center gap-1.5 text-xs font-semibold text-emerald-700 group-hover:translate-x-1 transition-transform">
                  <span>Generate Report</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </button>
            </div>
          </div>
        </InView>

        {/* SECTION D & SECTION B (Details): Latest Analysis Run Details or Empty State */}
        <InView direction="up" delay={0.2}>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Latest Analysis Run Details */}
            <div className="lg:col-span-2 p-6 rounded-3xl bg-white border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <Activity className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="font-display font-bold text-slate-900 text-base">
                      Latest Analysis Execution
                    </h3>
                    <p className="text-xs text-slate-500">
                      {activeRun ? `Run ID: ${activeRun.run_id}` : 'No completed run yet for this workspace'}
                    </p>
                  </div>
                </div>
                {activeRun && onOpenResults && (
                  <button
                    onClick={onOpenResults}
                    className="px-3.5 py-1.5 rounded-full bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-xs font-semibold border border-emerald-200 transition flex items-center gap-1 cursor-pointer"
                  >
                    <span>View Rankings</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                )}
              </div>

              {activeRun ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                      <span className="text-[10.5px] font-mono text-slate-500 block mb-0.5">Execution Date</span>
                      <span className="font-semibold text-slate-900">
                        {activeRun.timestamp ? new Date(activeRun.timestamp).toLocaleDateString() : 'Recent'}
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                      <span className="text-[10.5px] font-mono text-slate-500 block mb-0.5">Parcels Evaluated</span>
                      <span className="font-semibold text-slate-900 font-mono">
                        {activeRun.total_parcels} units
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                      <span className="text-[10.5px] font-mono text-slate-500 block mb-0.5">Eligible Candidates</span>
                      <span className="font-semibold text-emerald-700 font-mono">
                        {activeRun.eligible_count} parcels
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
                      <span className="text-[10.5px] font-mono text-slate-500 block mb-0.5">Plantable Area</span>
                      <span className="font-semibold text-emerald-700 font-mono">
                        {activeRun.total_plantable_area_ha ? `${activeRun.total_plantable_area_ha.toLocaleString()} ha` : '—'}
                      </span>
                    </div>
                  </div>

                  {/* Top Recommendations Preview */}
                  {activeRun.top_recommendations && activeRun.top_recommendations.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-500">
                        Top Ranked Parcels Preview
                      </span>
                      <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden bg-white text-xs">
                        {activeRun.top_recommendations.slice(0, 3).map((rec: any, idx: number) => (
                          <div key={idx} className="p-3 flex items-center justify-between gap-3 hover:bg-slate-50 transition">
                            <div className="flex items-center gap-2.5">
                              <span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-mono font-bold flex items-center justify-center">
                                #{rec.rank || idx + 1}
                              </span>
                              <span className="font-mono font-medium text-slate-900">
                                {rec.parcel_id}
                              </span>
                            </div>
                            <div className="flex items-center gap-4 text-xs font-mono text-slate-600">
                              <span>Score: {(rec.priority_score ?? rec.composite_score ?? 0).toFixed(2)}</span>
                              <span>Area: {rec.area_ha ? `${rec.area_ha.toFixed(1)} ha` : '—'}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* Honest Empty State (No Fabricated Data) */
                <div className="py-8 text-center space-y-3">
                  <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
                    <Info className="w-6 h-6" />
                  </div>
                  <div className="space-y-1">
                    <h4 className="font-semibold text-slate-800 text-sm">
                      No Completed Analysis Yet
                    </h4>
                    <p className="text-xs text-slate-500 max-w-sm mx-auto">
                      Use the floating panel above or the interactive area selector below to run your first geotechnical and reforestation assessment.
                    </p>
                  </div>
                  <button
                    onClick={scrollToAnalyzer}
                    className="px-4 py-2 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs transition inline-flex items-center gap-1.5 cursor-pointer shadow-xs"
                  >
                    <PlayCircle className="w-3.5 h-3.5" />
                    <span>Run Analysis Now</span>
                  </button>
                </div>
              )}
            </div>

            {/* Right: Section D Project History / Saved Runs */}
            <div className="p-6 rounded-3xl bg-white border border-slate-200 shadow-sm space-y-4 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                  <div className="flex items-center gap-2">
                    <History className="w-4 h-4 text-emerald-700" />
                    <h3 className="font-display font-bold text-slate-900 text-sm">
                      Saved Workspace Runs
                    </h3>
                  </div>
                  <span className="text-xs font-mono text-slate-500">
                    {activeProject?.saved_runs?.length || 0} run(s)
                  </span>
                </div>

                {activeProject?.saved_runs && activeProject.saved_runs.length > 0 ? (
                  <div className="space-y-2">
                    {activeProject.saved_runs.slice(0, 4).map((r, i) => (
                      <div
                        key={r.run_id || i}
                        className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs flex items-center justify-between gap-2"
                      >
                        <div>
                          <div className="font-mono font-semibold text-slate-900 truncate max-w-[130px]">
                            {r.run_id}
                          </div>
                          <div className="text-[10.5px] text-slate-500">
                            {r.timestamp ? new Date(r.timestamp).toLocaleDateString() : 'Saved'} • {r.eligible_count} candidates
                          </div>
                        </div>
                        {onOpenResults && (
                          <button
                            onClick={onOpenResults}
                            className="p-1 text-emerald-700 hover:text-emerald-900 hover:bg-emerald-50 rounded-lg transition"
                            title="Load results"
                          >
                            <ArrowRight className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 leading-relaxed py-4 text-center">
                    Saved runs from previous analyses will appear here for one-click review.
                  </p>
                )}
              </div>

              {/* Wayanad Benchmark Corridor Shortcut */}
              <div className="p-3.5 rounded-2xl bg-emerald-50/70 border border-emerald-200 text-xs space-y-2">
                <div className="flex items-center gap-1.5 text-emerald-900 font-bold">
                  <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Wayanad Pilot Benchmark</span>
                </div>
                <p className="text-[11px] text-emerald-800 leading-relaxed">
                  Pre-calibrated 2024 monsoon disaster zone (Meppadi, Kerala) with Copernicus 30m DEM and Sentinel-2 vegetation bands.
                </p>
                {onSelectProject && (
                  <button
                    onClick={() => onSelectProject('wayanad_pilot')}
                    className="w-full py-1.5 rounded-xl bg-white hover:bg-emerald-100/60 text-emerald-900 font-semibold text-xs border border-emerald-200 transition text-center cursor-pointer shadow-2xs"
                  >
                    Load Wayanad Demo
                  </button>
                )}
              </div>
            </div>
          </div>
        </InView>

        {/* ========================================================
            4. AUTONOMOUS AREA ANALYSIS CONSOLE & INTERACTIVE MAP
            Preserves 100% of real Leaflet polygon/box drawing,
            STAC acquisition, and 9-stage pipeline execution.
        ======================================================== */}
        <div
          ref={areaAnalyzerRef}
          className="rounded-3xl p-6 sm:p-8 bg-white border border-slate-200 shadow-md space-y-6 scroll-mt-6"
        >
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                <h3 className="text-xl sm:text-2xl font-display font-bold text-slate-900">
                  Autonomous Area Analysis &amp; Boundary Selector
                </h3>
              </div>
              <p className="text-xs sm:text-sm text-slate-600">
                Use the map toolbar to outline a custom polygon or bounding box, or run analysis across the selected catchment corridor.
              </p>
            </div>

            <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
              <span className="px-2.5 py-1 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 font-semibold">
                1. Select Area
              </span>
              <span>→</span>
              <span className="px-2.5 py-1 rounded-lg bg-teal-50 border border-teal-200 text-teal-800 font-semibold">
                2. Run Pipeline
              </span>
              <span>→</span>
              <span className="px-2.5 py-1 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 font-semibold">
                3. Inspect Results
              </span>
            </div>
          </div>

          {/* Leaflet MapCanvas with Real Interactive Drawing */}
          <div className="relative rounded-2xl overflow-hidden border border-slate-200 shadow-inner">
            <MapCanvas
              height="500px"
              enableDrawing={true}
              bounds={bounds}
              onBoundarySelected={(sel) => setSelectedArea(sel)}
              boundaryGeojson={selectedArea?.boundaryGeojson || activeProject?.boundary_geojson}
              observedInventoryGeojson={observedInventory}
              parcelsGeojson={activeParcelsGeojson || parcelsGeojson}
              studyAreaHa={authoritativeStudyAreaHa}
              onOpenResults={onOpenResults}
            />
          </div>

          {/* Interactive Parameters & Launch Controls */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 pt-2">
            {/* Selected Boundary Card */}
            <div className="p-5 rounded-2xl bg-slate-50/80 border border-slate-200 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-emerald-600" />
                  Boundary Selection
                </span>
                {selectedArea ? (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                    Custom Polygon Ready
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-200/80 text-slate-700">
                    Active AOI: {activeProject?.name || 'Wayanad'}
                  </span>
                )}
              </div>

              {selectedArea ? (
                <div className="space-y-2">
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-display font-bold text-emerald-800">
                      {selectedArea.areaHa.toLocaleString()} ha
                    </span>
                    <span className="text-xs text-slate-500 font-mono">
                      (~{(selectedArea.areaHa / 100).toFixed(2)} km²)
                    </span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-white border border-slate-200 text-[11px] font-mono text-slate-600 space-y-0.5">
                    <div>W: {selectedArea.bounds.minx.toFixed(4)}° | E: {selectedArea.bounds.maxx.toFixed(4)}°</div>
                    <div>S: {selectedArea.bounds.miny.toFixed(4)}° | N: {selectedArea.bounds.maxy.toFixed(4)}°</div>
                  </div>
                </div>
              ) : (
                <div className="py-2 space-y-1.5">
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Use the <strong>Draw Polygon</strong> or <strong>Draw Box</strong> toolbar on the map to define a custom catchment, or analyze the full study area directly.
                  </p>
                  <div className="text-[11px] font-mono text-emerald-800 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
                    Study Area Extent: {authoritativeStudyAreaHa.toLocaleString()} ha
                  </div>
                </div>
              )}
            </div>

            {/* Geotechnical & Model Parameters */}
            <div className="p-5 rounded-2xl bg-slate-50/80 border border-slate-200 space-y-3">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-teal-600" />
                Geotechnical &amp; Soil Calibration
              </span>

              <div className="space-y-2.5 text-xs">
                <div>
                  <label className="block text-[11px] text-slate-600 font-medium mb-1">Study Area Custom Label</label>
                  <input
                    type="text"
                    placeholder="e.g. Meppadi Catchment Trial"
                    value={analysisName}
                    onChange={(e) => setAnalysisName(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-800 text-xs placeholder:text-slate-400 focus:outline-none focus:border-emerald-600"
                  />
                </div>

                <div>
                  <label className="block text-[11px] text-slate-600 font-medium mb-1">Soil Lithology Preset</label>
                  <select
                    value={geotechPreset}
                    onChange={(e) => setGeotechPreset(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-800 text-xs focus:outline-none focus:border-emerald-600"
                  >
                    <option value="wayanad_saprolite">Monsoon Saprolite (Western Ghats)</option>
                    <option value="colluvial_clay_silt">Colluvial Clay-Silt (Himalayan)</option>
                    <option value="residual_sandy_loam">Residual Sandy Loam</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Execution & Advanced Options */}
            <div className="p-5 rounded-2xl bg-slate-50/80 border border-slate-200 flex flex-col justify-between space-y-4">
              <div className="space-y-1">
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-500">
                  Execution &amp; Workflows
                </span>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Triggers STAC querying of Copernicus 30m DEM and Sentinel-2 vegetation bands to compute reinforced Factor of Safety.
                </p>
              </div>

              <div className="space-y-2">
                <button
                  onClick={handleExecuteAutoAnalyze}
                  disabled={isAnalyzing}
                  className={`w-full py-3 rounded-xl font-bold text-xs transition flex items-center justify-center gap-2 shadow-xs cursor-pointer ${
                    isAnalyzing
                      ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                      : 'bg-[#0d3b32] hover:bg-[#124d42] text-white shadow-md'
                  }`}
                >
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin text-white" />
                      <span>Processing...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 text-emerald-300" />
                      <span>Run Pipeline On This Area</span>
                    </>
                  )}
                </button>

                <div className="flex items-center justify-between text-xs pt-1">
                  <button
                    onClick={onStartAnalysis}
                    className="text-emerald-800 hover:text-emerald-950 font-semibold flex items-center gap-1 cursor-pointer"
                  >
                    <span>Guided 5-Step Wizard</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                  <button
                    onClick={onOpenDataLibrary}
                    className="text-slate-500 hover:text-slate-800 font-medium cursor-pointer"
                  >
                    Data Library
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Real-time 9-Stage Progress Tracker */}
          {isAnalyzing && (
            <div className="p-6 rounded-2xl bg-emerald-50/80 border border-emerald-300 shadow-xl space-y-4 animate-fade-in text-slate-900">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Loader2 className="w-6 h-6 text-emerald-700 animate-spin" />
                  <div>
                    <h4 className="font-display font-bold text-slate-900 text-base">
                      Executing Geospatial &amp; Geotechnical Pipeline
                    </h4>
                    <p className="text-xs text-emerald-800 font-mono mt-0.5">
                      Stage {currentStage} of 9: {stageTitle || STAGES[currentStage - 1]?.title}
                    </p>
                  </div>
                </div>
                <span className="text-sm font-mono font-bold text-emerald-800">
                  {Math.round((currentStage / 9) * 100)}%
                </span>
              </div>

              {/* Animated Progress Bar */}
              <div className="w-full h-2.5 rounded-full bg-emerald-200/60 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-emerald-600 to-teal-500 transition-all duration-500 rounded-full"
                  style={{ width: `${(currentStage / 9) * 100}%` }}
                />
              </div>

              <p className="text-xs text-slate-700 leading-relaxed font-mono">
                {stageMessage || STAGES[currentStage - 1]?.desc}
              </p>
            </div>
          )}

          {/* Error Banner */}
          {analysisError && (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-300 text-xs text-rose-800 flex items-start gap-3 animate-fade-in">
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <span className="font-semibold block text-rose-900">Analysis Notice</span>
                <p className="text-rose-700 leading-relaxed">{analysisError}</p>
              </div>
            </div>
          )}

          {/* Completion Success Card */}
          {completedAnalysis && (
            <div className="p-6 rounded-2xl bg-emerald-50 border border-emerald-300 shadow-lg flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-fade-in">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center shrink-0 border border-emerald-200">
                  <CheckCircle2 className="w-6 h-6 text-emerald-600" />
                </div>
                <div>
                  <h4 className="font-display font-bold text-slate-900 text-base">
                    Analysis Completed Successfully!
                  </h4>
                  <p className="text-xs text-slate-600 mt-0.5">
                    Evaluated {completedAnalysis.total_parcels} candidate parcels ({completedAnalysis.eligible_count} eligible for planting).
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                {onNavigateTab && (
                  <button
                    onClick={() => onNavigateTab('map')}
                    className="px-4 py-2.5 rounded-full bg-white hover:bg-slate-50 text-slate-800 font-semibold text-xs border border-slate-200 transition flex items-center gap-1.5 cursor-pointer shadow-xs"
                  >
                    <Compass className="w-4 h-4 text-emerald-600" />
                    <span>Inspect on Map</span>
                  </button>
                )}
                {onNavigateTab && (
                  <button
                    onClick={() => onNavigateTab('results')}
                    className="px-4 py-2.5 rounded-full bg-[#0d3b32] hover:bg-[#124d42] text-white font-semibold text-xs transition flex items-center gap-1.5 cursor-pointer shadow-md"
                  >
                    <BarChart3 className="w-4 h-4 text-emerald-300" />
                    <span>Open Results Dashboard</span>
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ========================================================
            5. CURATED REAL-WORLD CASE STUDIES SHOWCASE
        ======================================================== */}
        <InView direction="up" delay={0.25}>
          <div className="space-y-4 pt-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="p-1.5 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200">
                    <BookOpen className="w-4 h-4 text-emerald-700" />
                  </span>
                  <span className="text-xs font-mono font-bold uppercase tracking-wider text-emerald-800">
                    Real-World Disaster Scenarios
                  </span>
                </div>
                <h3 className="text-lg sm:text-xl font-bold text-slate-900 font-display mt-1">
                  Historical &amp; Recent Landslide Case Studies
                </h3>
                <p className="text-xs text-slate-600 max-w-2xl mt-0.5">
                  Explore documented disaster footprints and verify slope-stability bio-engineering models across the Western Ghats and Himalayas.
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => onNavigateTab?.('case-studies')}
                  className="px-4 py-2 rounded-full bg-white hover:bg-slate-50 text-slate-800 text-xs font-semibold border border-slate-200 transition flex items-center gap-1.5 cursor-pointer shadow-xs"
                >
                  <span>Full Library ({caseStudies.length})</span>
                  <ArrowRight className="w-3.5 h-3.5 text-emerald-700" />
                </button>
              </div>
            </div>

            {/* Region Filter Buttons */}
            <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
              {[
                { id: 'all' as const, label: 'All Cases' },
                { id: 'western_ghats' as const, label: 'Western Ghats' },
                { id: 'himalayas' as const, label: 'Himalayas' },
                { id: 'nepal' as const, label: 'Nepal' },
                { id: 'recent' as const, label: 'Recent (2023–2026)' },
              ].map((f) => (
                <button
                  key={f.id}
                  onClick={() => setCaseFilter(f.id)}
                  className={`px-3.5 py-1.5 rounded-full transition text-xs font-medium cursor-pointer ${
                    caseFilter === f.id
                      ? 'bg-[#0d3b32] text-white font-semibold shadow-xs'
                      : 'bg-white text-slate-600 hover:text-slate-900 border border-slate-200'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            {/* Case Studies Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {caseStudies
                .filter((c) => {
                  if (caseFilter === 'western_ghats') return c.region_tag === 'western_ghats';
                  if (caseFilter === 'himalayas') return c.region_tag === 'himalayas';
                  if (caseFilter === 'nepal') return c.region_tag === 'nepal';
                  if (caseFilter === 'recent') return c.temporal_tag === 'recent';
                  return true;
                })
                .slice(0, 6)
                .map((c) => {
                  const isOffline = c.region_tag === 'offline_demo';
                  const isProvisional = c.verification_status === 'PROVISIONAL_RECENT';
                  const isVerified = c.verification_status === 'VERIFIED_OBSERVATION';

                  return (
                    <div
                      key={c.id}
                      className="p-5 rounded-2xl bg-white border border-slate-200 hover:border-emerald-500/50 hover:shadow-md transition-all flex flex-col justify-between space-y-3 group"
                    >
                      <div className="space-y-2.5">
                        <div className="flex items-center justify-between gap-2 flex-wrap">
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono border ${
                              isVerified
                                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                                : isProvisional
                                ? 'bg-sky-50 border-sky-200 text-sky-800'
                                : isOffline
                                ? 'bg-slate-100 border-slate-200 text-slate-700'
                                : 'bg-amber-50 border-amber-200 text-amber-800'
                            }`}
                          >
                            {isOffline
                              ? 'Offline Benchmark'
                              : isProvisional
                              ? 'Provisional Recent'
                              : isVerified
                              ? 'Verified Observation'
                              : 'Historical Catalog'}
                          </span>
                          <span className="text-[10px] font-mono text-slate-500 flex items-center gap-1">
                            <Calendar className="w-3 h-3 text-emerald-700" />
                            <span>{c.event_date}</span>
                          </span>
                        </div>

                        <div>
                          <h4 className="font-bold text-slate-900 text-sm group-hover:text-emerald-700 transition font-display line-clamp-1">
                            {c.name}
                          </h4>
                          <div className="text-[11px] text-slate-500 flex items-center gap-1 mt-0.5 truncate">
                            <MapPin className="w-3 h-3 text-slate-400 shrink-0" />
                            <span className="truncate">{c.locality}, {c.state_province}</span>
                          </div>
                        </div>

                        <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                          {c.short_description}
                        </p>

                        <div className="flex flex-wrap gap-1 text-[10px] font-mono text-slate-500 pt-1">
                          {c.observed_landslide_inventory && (
                            <span className="px-2 py-0.5 rounded bg-emerald-50 border border-emerald-200 text-emerald-800">
                              📍 {c.observed_landslide_inventory.features?.length || 0} Observed Footprints
                            </span>
                          )}
                          <span className="px-2 py-0.5 rounded bg-slate-50 border border-slate-200">
                            {c.disaster_type.split('&')[0].trim()}
                          </span>
                        </div>
                      </div>

                      <div className="pt-3 border-t border-slate-100 flex items-center gap-2">
                        <button
                          onClick={() => onExploreCaseStudy ? onExploreCaseStudy(c.id) : onNavigateTab?.('case-studies')}
                          className="w-full py-2 px-3 rounded-full bg-slate-50 hover:bg-[#0d3b32] hover:text-white text-slate-800 text-xs font-semibold border border-slate-200 transition flex items-center justify-center gap-1.5 cursor-pointer shadow-2xs"
                        >
                          <span>Explore Scenario</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>
        </InView>
      </div>
    </div>
  );
};

export default OverviewView;
