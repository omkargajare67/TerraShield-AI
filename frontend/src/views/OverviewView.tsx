import React, { useState, useMemo, useEffect } from 'react';
import type { ProjectMetadata, RecommendationRunResponse, CaseStudy } from '../api/types';
import { api } from '../api/client';
import { TextEffect } from '../components/motion-primitives/TextEffect';
import { InView } from '../components/motion-primitives/InView';
import { MetricCard } from '../components/common/MetricCard';
import { ProvenanceBanner } from '../components/common/ProvenanceBanner';
import { HelpTooltip } from '../components/common/HelpTooltip';
import { MapCanvas, type StudyAreaSelection } from '../components/map/MapCanvas';
import { calculatePolygonAreaHa } from '../utils/geo';
import { normalizeBounds } from '../utils/normalize';
import {
  ArrowRight,
  ShieldCheck,
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
} from 'lucide-react';

interface OverviewViewProps {
  activeProject: ProjectMetadata | null;
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

  // Case Studies and Observed Inventory state
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

  // Load registered Case Studies for Curated Library section
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

  // Fetch Observed Landslide Inventory for active project if it corresponds to a case study
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

  // Authoritative Study Area Calculation (Never displays 0 ha when boundary or bounds exist)
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

  // Active analysis run: current completed analysis, or latest project run
  const activeRun = isAnalyzing ? null : (completedAnalysis || latestRun);

  // Handle One-Click Automatic Analysis Execution
  const handleExecuteAutoAnalyze = async () => {
    if (!selectedArea) {
      setAnalysisError('Please select or draw a target area on the map first.');
      return;
    }

    setIsAnalyzing(true);
    setAnalysisError(null);
    setCurrentStage(1);
    setStageTitle('Validating selected area');
    setStageMessage('Verifying coordinates, topology, and study area size...');
    // Clear stale results immediately so user is never misled
    setCompletedAnalysis(null);
    setActiveParcelsGeojson(null);

    try {
      // Launch asynchronous job with real-time polling
      const launchRes = await api.autoAnalyze({
        name: analysisName.trim() || undefined,
        bounds: selectedArea.bounds,
        boundary_geojson: selectedArea.boundaryGeojson,
        geotech_preset_id: geotechPreset,
        cell_size_m: cellSizeM,
        priority_preset: priorityPreset,
        async_job: true,
      });

      const jobId = launchRes.job_id;

      // Poll progress every 1.5 seconds
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

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8 animate-fade-in">
      {/* Hero Banner */}
      <div className="relative rounded-3xl overflow-hidden border border-terra-border/50 shadow-2xl bg-terra-forest/40 backdrop-blur-xl">
        <div
          className="absolute inset-0 bg-cover bg-bottom opacity-35 mix-blend-luminosity pointer-events-none"
          style={{ backgroundImage: `url('/backgrounds/hero-layered-peaks.svg')` }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-terra-deep/95 via-terra-deep/80 to-transparent pointer-events-none" />

        <div className="relative z-10 px-6 sm:px-8 py-8 md:py-10 max-w-3xl space-y-3.5">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-400/25 text-emerald-300 text-xs font-semibold backdrop-blur-md">
            <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            <span>GEOSPATIAL INTELLIGENCE & REFORESTATION DECISION SUPPORT</span>
          </div>

          <TextEffect
            as="h1"
            per="word"
            className="text-2xl sm:text-3xl md:text-4xl font-display font-bold text-white tracking-tight leading-tight"
          >
            Understand terrain. Identify restoration opportunities. Explore evidence.
          </TextEffect>

          <p className="text-slate-300 text-xs sm:text-sm leading-relaxed max-w-2xl">
            Select or draw any hillslope study area on the map. TerraShield connects Copernicus 30m elevation and Sentinel-2 vegetation bands to evaluate slope stability mechanics and rank root-reinforced reforestation parcels.
          </p>

          {/* 4 Quick Actions */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-2">
            <button
              onClick={onStartAnalysis}
              className="p-3 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-500 hover:to-teal-600 text-white font-semibold text-xs border border-emerald-400/40 transition flex flex-col gap-1 text-left cursor-pointer shadow-md shadow-emerald-950/60 group"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold">New Analysis</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
              </div>
              <span className="text-[10px] text-emerald-100 font-normal">Guided 5-step wizard</span>
            </button>

            <button
              onClick={() => onNavigateTab?.('case-studies')}
              className="p-3 rounded-xl bg-[#091f17]/90 hover:bg-emerald-900/40 text-emerald-300 font-semibold text-xs border border-emerald-500/25 transition flex flex-col gap-1 text-left cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-white">Case Studies</span>
                <BookOpen className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <span className="text-[10px] text-slate-400 font-normal">Historical disasters</span>
            </button>

            <button
              onClick={() => onNavigateTab?.('map')}
              className="p-3 rounded-xl bg-[#091f17]/90 hover:bg-emerald-900/40 text-emerald-300 font-semibold text-xs border border-emerald-500/25 transition flex flex-col gap-1 text-left cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-white">Map Explorer</span>
                <Compass className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <span className="text-[10px] text-slate-400 font-normal">Interactive parcels</span>
            </button>

            <button
              onClick={onOpenDataLibrary}
              className="p-3 rounded-xl bg-[#091f17]/90 hover:bg-emerald-900/40 text-emerald-300 font-semibold text-xs border border-emerald-500/25 transition flex flex-col gap-1 text-left cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-white">Recent Projects</span>
                <Layers className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <span className="text-[10px] text-slate-400 font-normal">Workspaces & data</span>
            </button>
          </div>
        </div>
      </div>

      <ProvenanceBanner />

      {/* Primary Feature: Interactive Area Selector & One-Click Analysis Console */}
      <div className="rounded-3xl p-6 sm:p-8 bg-terra-forest/40 border border-terra-border/50 backdrop-blur-xl shadow-2xl space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-terra-border/30">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-2.5 h-2.5 rounded-full bg-terra-mint animate-pulse" />
              <h2 className="text-xl sm:text-2xl font-display font-semibold text-terra-ivory">
                Interactive Area Selector
              </h2>
            </div>
            <p className="text-xs sm:text-sm text-terra-muted">
              Use the toolbar buttons on the map to draw a custom polygon, box, or select a disaster-prone corridor.
            </p>
          </div>

          {/* Quick Step Indicators */}
          <div className="flex items-center gap-2 text-xs font-mono text-terra-slate">
            <span className="px-2.5 py-1 rounded-lg bg-terra-deep/70 border border-terra-border/40 text-terra-mint">
              1. Draw Area
            </span>
            <span>→</span>
            <span className="px-2.5 py-1 rounded-lg bg-terra-deep/70 border border-terra-border/40 text-terra-ivory">
              2. One Click
            </span>
            <span>→</span>
            <span className="px-2.5 py-1 rounded-lg bg-terra-deep/70 border border-terra-border/40 text-terra-mint">
              3. View Results
            </span>
          </div>
        </div>

        {/* Map with Interactive Drawing Canvas & Direct Recommendations Overlay */}
        <div className="relative">
          <MapCanvas
            height="480px"
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

        {/* One-Click Action & Configuration Bar */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-2">
          {/* Selected Boundary Preview Card */}
          <div className="p-5 rounded-2xl bg-terra-deep/70 border border-terra-border/50 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-terra-slate font-mono flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-terra-mint" />
                Selected Boundary
              </span>
              {selectedArea ? (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                  Ready to Analyze
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                  Select on Map
                </span>
              )}
            </div>

            {selectedArea ? (
              <div className="space-y-2">
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-display font-bold text-terra-mint">
                    {selectedArea.areaHa.toLocaleString()} ha
                  </span>
                  <span className="text-xs text-terra-slate font-mono">
                    (~{(selectedArea.areaHa / 100).toFixed(2)} km²)
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-terra-forest/40 border border-terra-border/40 text-[11px] font-mono text-terra-slate space-y-0.5">
                  <div>
                    West: {selectedArea.bounds.minx.toFixed(4)}° | East: {selectedArea.bounds.maxx.toFixed(4)}°
                  </div>
                  <div>
                    South: {selectedArea.bounds.miny.toFixed(4)}° | North: {selectedArea.bounds.maxy.toFixed(4)}°
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-4 text-center space-y-2">
                <Compass className="w-8 h-8 text-terra-slate mx-auto opacity-50" />
                <p className="text-xs text-terra-muted max-w-xs mx-auto">
                  Click <strong>"Draw Polygon"</strong> or <strong>"Draw Box"</strong> in the top-left map toolbar to outline your study area.
                </p>
              </div>
            )}
          </div>

          {/* Analysis Settings Card */}
          <div className="p-5 rounded-2xl bg-terra-deep/70 border border-terra-border/50 space-y-3">
            <span className="text-xs font-bold uppercase tracking-wider text-terra-slate font-mono flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-terra-mint" />
              Settings & Priority
            </span>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="col-span-2">
                <label className="block text-[11px] text-terra-slate mb-1">Study Area Name (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. Munnar Catchment Pilot"
                  value={analysisName}
                  onChange={(e) => setAnalysisName(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-terra-forest/60 border border-terra-border/50 text-terra-ivory text-xs placeholder:text-terra-slate focus:outline-none focus:border-terra-mint font-sans"
                />
              </div>

              <div>
                <label className="block text-[11px] text-terra-slate mb-1">Priority Goal</label>
                <select
                  value={priorityPreset}
                  onChange={(e: any) => setPriorityPreset(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-terra-forest/60 border border-terra-border/50 text-terra-ivory text-xs focus:outline-none focus:border-terra-mint"
                >
                  <option value="balanced">Balanced (Recommended)</option>
                  <option value="landslide">Landslide Mitigation</option>
                  <option value="plantable">Plantable Area</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] text-terra-slate mb-1">Soil Mechanics</label>
                <select
                  value={geotechPreset}
                  onChange={(e) => setGeotechPreset(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-terra-forest/60 border border-terra-border/50 text-terra-ivory text-xs focus:outline-none focus:border-terra-mint"
                >
                  <option value="wayanad_saprolite">Monsoon Saprolite</option>
                  <option value="colluvial_clay_silt">Colluvial Clay-Silt</option>
                  <option value="residual_sandy_loam">Residual Sandy Loam</option>
                </select>
              </div>

              <div className="col-span-2">
                <label className="block text-[11px] text-terra-slate mb-1">
                  Parcel Grid Resolution ({cellSizeM}m)
                </label>
                <input
                  type="range"
                  min="150"
                  max="500"
                  step="50"
                  value={cellSizeM}
                  onChange={(e) => setCellSizeM(Number(e.target.value))}
                  className="w-full accent-terra-mint cursor-pointer"
                />
              </div>
            </div>
          </div>

          {/* Primary Action Button Card */}
          <div className="p-5 rounded-2xl bg-terra-deep/70 border border-terra-border/50 flex flex-col justify-between space-y-4">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-terra-slate font-mono">
                One-Click Pipeline
              </span>
              <p className="text-xs text-terra-muted mt-1 leading-relaxed">
                Discovers real NASA/Copernicus elevation and Sentinel-2 bands, derives slope, and prioritizes parcels.
              </p>
            </div>

            <button
              onClick={handleExecuteAutoAnalyze}
              disabled={!selectedArea || isAnalyzing}
              className={`w-full py-4 rounded-xl font-semibold text-xs sm:text-sm transition flex items-center justify-center gap-2 shadow-xl cursor-pointer ${
                !selectedArea || isAnalyzing
                  ? 'bg-terra-border/50 text-terra-slate cursor-not-allowed'
                  : 'bg-gradient-to-r from-terra-mint to-emerald-400 text-terra-deep font-bold hover:brightness-105 shadow-terra-mint/20 animate-pulse'
              }`}
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Analyzing Location...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  <span>Analyze This Area</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Real-time Analysis Progress Modal / Banner */}
        {isAnalyzing && (
          <div className="p-6 rounded-2xl bg-terra-deep/95 border border-terra-mint/50 shadow-2xl space-y-4 animate-fade-in">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Loader2 className="w-6 h-6 text-terra-mint animate-spin" />
                <div>
                  <h3 className="font-display font-semibold text-terra-ivory text-base">
                    Executing Geospatial & Geotechnical Pipeline
                  </h3>
                  <p className="text-xs text-terra-mint font-mono mt-0.5">
                    Step {currentStage} of 9: {stageTitle || STAGES[currentStage - 1]?.title}
                  </p>
                </div>
              </div>
              <span className="text-xs font-mono font-bold text-terra-mint">
                {Math.round((currentStage / 9) * 100)}%
              </span>
            </div>

            {/* Progress Bar */}
            <div className="w-full h-2 rounded-full bg-terra-forest/80 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-terra-mint to-emerald-400 transition-all duration-500"
                style={{ width: `${(currentStage / 9) * 100}%` }}
              />
            </div>

            <p className="text-xs text-terra-muted leading-relaxed">
              {stageMessage || STAGES[currentStage - 1]?.desc}
            </p>
          </div>
        )}

        {/* Error Banner */}
        {analysisError && (
          <div className="p-4 rounded-xl bg-rose-500/15 border border-rose-500/30 text-xs text-rose-200 flex items-start gap-3 animate-fade-in">
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-semibold block text-rose-300">Analysis Error</span>
              <p className="text-rose-200/90 leading-relaxed">{analysisError}</p>
            </div>
          </div>
        )}

        {/* Completion Success Card */}
        {completedAnalysis && (
          <div className="p-6 rounded-2xl bg-emerald-500/15 border border-emerald-500/40 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-fade-in">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 border border-emerald-500/30">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-display font-semibold text-terra-ivory text-base">
                  Analysis Successfully Completed!
                </h3>
                <p className="text-xs text-terra-muted mt-0.5">
                  Evaluated {completedAnalysis.total_parcels} candidate parcels ({completedAnalysis.eligible_count} eligible for planting).
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {onNavigateTab && (
                <button
                  onClick={() => onNavigateTab('map')}
                  className="px-4 py-2.5 rounded-xl bg-terra-forest text-terra-mint font-semibold text-xs border border-terra-mint/30 hover:bg-terra-forest/80 transition flex items-center gap-1.5 cursor-pointer shadow-sm"
                >
                  <Compass className="w-4 h-4" />
                  <span>Inspect on Map</span>
                </button>
              )}
              {onNavigateTab && (
                <button
                  onClick={() => onNavigateTab('results')}
                  className="px-4 py-2.5 rounded-xl bg-terra-mint text-terra-deep font-semibold text-xs hover:bg-terra-mint/90 transition flex items-center gap-1.5 cursor-pointer shadow-lg shadow-terra-mint/10"
                >
                  <BarChart3 className="w-4 h-4" />
                  <span>Open Results Dashboard</span>
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Honest Workspace Summary Cards */}
      <InView direction="up" delay={0.1}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Study Area Size"
            value={authoritativeStudyAreaHa}
            suffix=" ha"
            icon={MapPin}
            color="emerald"
            subtext={selectedArea ? "Active selected boundary" : "Project study boundary"}
            badge="Boundary"
          />
          <MetricCard
            label="Verified GIS Layers"
            value={Object.keys(activeProject?.layers || {}).length}
            icon={Layers}
            color="amber"
            subtext="Elevation, Slope & NDVI"
            badge="Workspace"
          />
          {activeRun ? (
            <>
              <MetricCard
                label="Evaluated Locations"
                value={activeRun.total_parcels ?? (activeRun as any).parcel_inventory?.total_evaluated ?? 0}
                icon={Mountain}
                color="blue"
                subtext={`Grid resolution ${activeRun.cell_size_m || cellSizeM || 300}m`}
                badge="Modeled"
              />
              <MetricCard
                label="Recommended for Planting"
                value={activeRun.eligible_count ?? (activeRun as any).parcel_inventory?.eligible_count ?? 0}
                icon={Trees}
                color="emerald"
                subtext={`${((activeRun.total_plantable_area_ha ?? (activeRun as any).parcel_inventory?.total_plantable_area_ha) ?? 0).toLocaleString()} ha eligible planting area`}
                badge="Actionable"
              />
            </>
          ) : (
            <>
              <MetricCard
                label="Analysis Status"
                value={isAnalyzing ? 1 : (hasRuns ? 1 : 0)}
                icon={Mountain}
                color="blue"
                subtext={isAnalyzing ? 'Computing candidate parcels...' : (hasRuns ? 'Prior run available' : 'Ready for first analysis')}
                badge={isAnalyzing ? 'Running' : (hasRuns ? 'Available' : 'Pending')}
              />
              <MetricCard
                label="Planting Candidates"
                value={hasRuns ? (activeProject?.saved_runs?.[0]?.eligible_count || 0) : 0}
                icon={Trees}
                color="emerald"
                subtext={hasRuns ? 'Eligible in saved run' : 'Run analysis to compute'}
                badge={hasRuns ? 'Candidate' : 'Ready'}
              />
            </>
          )}
        </div>
      </InView>

      {/* Active Project Card & Guided Steps */}
      <InView direction="up" delay={0.15}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Active Project Information */}
          <div className="lg:col-span-2 rounded-2xl p-6 bg-terra-forest/30 border border-terra-border/40 backdrop-blur-xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-terra-mint/15 text-terra-mint border border-terra-mint/25">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-display font-semibold text-terra-ivory text-base">
                    {activeProject?.name || 'Active Study Area'}
                  </h3>
                  <p className="text-xs text-terra-slate">
                    {activeProject?.description || 'Active environmental workspace for terrain modeling.'}
                  </p>
                </div>
              </div>
              <button
                onClick={onOpenDataLibrary}
                className="text-xs font-semibold text-terra-mint hover:underline cursor-pointer"
              >
                Manage Projects
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-xs">
              <div className="p-3 rounded-xl bg-terra-deep/60 border border-terra-border/40">
                <div className="flex items-center gap-1 text-terra-slate text-[11px] mb-1">
                  <span>Coordinate System</span>
                  <HelpTooltip
                    term="Coordinate System"
                    text="Defines how 3D geographic locations on Earth are represented on a 2D map."
                  />
                </div>
                <span className="font-mono text-terra-ivory font-semibold truncate block">
                  {activeProject?.native_crs || 'EPSG:4326 (WGS 84)'}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-terra-deep/60 border border-terra-border/40">
                <div className="flex items-center gap-1 text-terra-slate text-[11px] mb-1">
                  <span>Soil & Terrain Preset</span>
                  <HelpTooltip
                    term="Geotechnical Preset"
                    text="Pre-calibrated soil mechanics assumptions including effective cohesion and internal friction angle."
                  />
                </div>
                <span className="text-terra-ivory font-semibold truncate block">
                  {activeProject?.geotechnical_parameters?.name || 'Tropical Monsoon Saprolite'}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-terra-deep/60 border border-terra-border/40">
                <span className="text-terra-slate block text-[11px] mb-1">Saved Analyses</span>
                <span className="font-mono text-terra-ivory font-semibold">
                  {activeProject?.saved_runs?.length || 0} run{activeProject?.saved_runs?.length === 1 ? '' : 's'}
                </span>
              </div>
            </div>

            <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between text-xs text-terra-slate border-t border-terra-border/30 gap-2">
              <span className="font-mono text-[11px]">
                Extent: {bounds.minx.toFixed(2)}°E, {bounds.miny.toFixed(2)}°N to {bounds.maxx.toFixed(2)}°E, {bounds.maxy.toFixed(2)}°N
              </span>
              <button
                onClick={onStartAnalysis}
                className="font-semibold text-terra-mint hover:text-terra-ivory flex items-center gap-1 cursor-pointer"
              >
                <span>Advanced 5-Step Wizard</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Demonstration Corridor Card */}
          <div className="rounded-2xl p-6 bg-terra-forest/30 border border-terra-border/40 backdrop-blur-xl space-y-4 flex flex-col justify-between">
            <div className="space-y-3">
              <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-terra-mint">
                Benchmark Pilot
              </span>
              <h4 className="font-display font-semibold text-terra-ivory text-sm">
                Wayanad Watershed Pilot (Kerala, India)
              </h4>
              <p className="text-xs text-terra-muted leading-relaxed">
                Pre-calibrated benchmark using NASA SRTM NASADEM (30m) and Sentinel-2 L2A NDVI (10m)
                covering the Meppadi/Chooralmala landslide corridor.
              </p>
            </div>

            {onSelectProject && (
              <button
                onClick={() => onSelectProject('wayanad_pilot')}
                className="w-full py-2.5 rounded-xl bg-terra-forest/80 hover:bg-terra-forest text-terra-ivory font-semibold text-xs border border-terra-border/60 transition flex items-center justify-center gap-2 cursor-pointer shadow-sm"
              >
                <Sparkles className="w-4 h-4 text-terra-mint" />
                <span>Load Wayanad Benchmark</span>
              </button>
            )}
          </div>
        </div>
      </InView>

      {/* Real-World Case Studies Curated Showcase */}
      <InView direction="up" delay={0.2}>
        <div className="space-y-4 pt-2">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-terra-border/40 pb-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="p-1.5 rounded-lg bg-terra-forest text-terra-mint border border-terra-mint/30">
                  <BookOpen className="w-4 h-4" />
                </span>
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-terra-mint">
                  Real-World Landslide Case Studies
                </span>
              </div>
              <h3 className="text-lg font-bold text-terra-ivory font-serif mt-1">
                Curated Historical &amp; Recent Disaster Scenarios
              </h3>
              <p className="text-xs text-terra-muted max-w-2xl mt-0.5">
                Explore verified landslide footprints and run genuine slope-stability bio-engineering models
                across documented failure sites in the Western Ghats and Himalayas.
              </p>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => onNavigateTab?.('case-studies')}
                className="px-3.5 py-2 rounded-xl bg-terra-forest/80 hover:bg-terra-forest text-terra-mint hover:text-terra-ivory text-xs font-semibold border border-terra-mint/30 transition flex items-center gap-1.5 cursor-pointer shadow-sm"
              >
                <span>View Full Library ({caseStudies.length})</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none text-xs">
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
                className={`px-3 py-1.5 rounded-xl transition text-xs font-medium cursor-pointer ${
                  caseFilter === f.id
                    ? 'bg-terra-forest text-terra-mint font-semibold border border-terra-mint/40 shadow-sm'
                    : 'bg-terra-dark/50 text-terra-slate hover:text-terra-ivory border border-terra-border/50'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Cards Grid */}
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
                    className="p-5 rounded-2xl bg-terra-forest/25 border border-terra-border/50 hover:border-terra-mint/40 transition-all flex flex-col justify-between space-y-3 group"
                  >
                    <div className="space-y-2.5">
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-mono border ${
                            isVerified
                              ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400'
                              : isProvisional
                              ? 'bg-sky-500/15 border-sky-500/30 text-sky-300'
                              : isOffline
                              ? 'bg-slate-500/20 border-slate-500/30 text-slate-300'
                              : 'bg-amber-500/15 border-amber-500/30 text-amber-300'
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
                        <span className="text-[10px] font-mono text-terra-slate flex items-center gap-1">
                          <Calendar className="w-3 h-3 text-terra-mint" />
                          <span>{c.event_date}</span>
                        </span>
                      </div>

                      <div>
                        <h4 className="font-bold text-terra-ivory text-sm group-hover:text-terra-mint transition font-serif line-clamp-1">
                          {c.name}
                        </h4>
                        <div className="text-[11px] text-terra-muted flex items-center gap-1 mt-0.5 truncate">
                          <MapPin className="w-3 h-3 text-terra-slate shrink-0" />
                          <span className="truncate">{c.locality}, {c.state_province}</span>
                        </div>
                      </div>

                      <p className="text-xs text-terra-slate line-clamp-2 leading-relaxed">
                        {c.short_description}
                      </p>

                      <div className="flex flex-wrap gap-1 text-[10px] font-mono text-terra-slate pt-1">
                        {c.observed_landslide_inventory && (
                          <span className="px-2 py-0.5 rounded bg-emerald-950/40 border border-emerald-500/20 text-emerald-300">
                            📍 {c.observed_landslide_inventory.features?.length || 0} Observed Footprints
                          </span>
                        )}
                        <span className="px-2 py-0.5 rounded bg-terra-dark/60 border border-terra-border">
                          {c.disaster_type.split('&')[0].trim()}
                        </span>
                      </div>
                    </div>

                    <div className="pt-3 border-t border-terra-border/40 flex items-center gap-2">
                      <button
                        onClick={() => onExploreCaseStudy ? onExploreCaseStudy(c.id) : onNavigateTab?.('case-studies')}
                        className="w-full py-2 px-3 rounded-xl bg-terra-forest hover:bg-terra-mint hover:text-terra-deep text-terra-ivory text-xs font-semibold transition flex items-center justify-center gap-1.5 cursor-pointer shadow-sm"
                      >
                        <span>Explore Case Study</span>
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
  );
};

export default OverviewView;
