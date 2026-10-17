import React, { useState } from 'react';
import type { ProjectMetadata, RecommendationRunResponse } from '../api/types';
import { api } from '../api/client';
import { TransitionPanel } from '../components/motion-primitives/TransitionPanel';
import { HelpTooltip } from '../components/common/HelpTooltip';
import {
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Loader2,
  MapPin,
  FileCheck,
  Sliders,
  ShieldCheck,
  AlertCircle,
  Play,
  ChevronDown,
  ChevronUp,
  Compass,
  BarChart3,
} from 'lucide-react';

interface AnalysisWizardViewProps {
  project: ProjectMetadata | null;
  projects?: ProjectMetadata[];
  onSelectProject?: (id: string) => void;
  onAnalysisComplete: (results: RecommendationRunResponse) => void;
  onNavigateTab?: (tab: any) => void;
}

export const AnalysisWizardView: React.FC<AnalysisWizardViewProps> = ({
  project,
  projects = [],
  onSelectProject,
  onAnalysisComplete,
  onNavigateTab,
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [runProgressStage, setRunProgressStage] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);
  const [isDataDetailsOpen, setIsDataDetailsOpen] = useState(false);
  const [completedResults, setCompletedResults] = useState<RecommendationRunResponse | null>(null);

  // Bounds & layers from project
  const bounds = project?.bounds || { minx: 76.0, miny: 11.55, maxx: 76.1, maxy: 11.65 };
  const dlon = Math.abs(bounds.maxx - bounds.minx);
  const dlat = Math.abs(bounds.maxy - bounds.miny);
  const approxHa = Math.round(dlon * 111 * dlat * 111 * 100);
  const layers = project?.layers || {};

  // Discretization Cell Size (m)
  const [cellSize, setCellSize] = useState<number>(
    project?.recommendation_settings?.cell_size_m || 300
  );

  // Priority Goal Preset
  const [priorityPreset, setPriorityPreset] = useState<'balanced' | 'landslide' | 'plantable'>('balanced');

  // Scoring Weights (defaults matched to balanced preset)
  const [wNeed, setWNeed] = useState<number>(
    project?.recommendation_settings?.scoring_weights?.weight_geotechnical_need || 0.35
  );
  const [wGain, setWGain] = useState<number>(
    project?.recommendation_settings?.scoring_weights?.weight_stability_gain || 0.30
  );
  const [wArea, setWArea] = useState<number>(
    project?.recommendation_settings?.scoring_weights?.weight_plantable_area || 0.20
  );
  const [wConf, setWConf] = useState<number>(
    project?.recommendation_settings?.scoring_weights?.weight_data_confidence || 0.15
  );

  const applyPriorityPreset = (preset: 'balanced' | 'landslide' | 'plantable') => {
    setPriorityPreset(preset);
    if (preset === 'balanced') {
      setWNeed(0.35);
      setWGain(0.30);
      setWArea(0.20);
      setWConf(0.15);
    } else if (preset === 'landslide') {
      setWNeed(0.50);
      setWGain(0.35);
      setWArea(0.10);
      setWConf(0.05);
    } else if (preset === 'plantable') {
      setWNeed(0.20);
      setWGain(0.20);
      setWArea(0.50);
      setWConf(0.10);
    }
  };

  // Eligibility Thresholds
  const [maxSlope, setMaxSlope] = useState<number>(
    project?.recommendation_settings?.eligibility_settings?.max_slope_deg || 45.0
  );
  const enableCanopy = project?.recommendation_settings?.eligibility_settings?.enable_ndvi_canopy_filter || false;
  const canopyThreshold = project?.recommendation_settings?.eligibility_settings?.ndvi_canopy_threshold || 0.65;
  const minPlantableArea = project?.recommendation_settings?.eligibility_settings?.min_plantable_area_ha || 0.25;

  // Geotechnical Parameters
  const gp = project?.geotechnical_parameters || {};
  const [cPrime, setCPrime] = useState<number>(gp.soil?.c_prime_kpa || 8.0);
  const [phiDeg, setPhiDeg] = useState<number>(gp.soil?.phi_deg || 26.0);
  const [gammaKn, setGammaKn] = useState<number>(gp.soil?.gamma_kn_m3 || 18.5);
  const [depthZ, setDepthZ] = useState<number>(gp.soil?.depth_m || 1.8);
  const [waterM, setWaterM] = useState<number>(gp.soil?.m_water_table || 0.5);

  const [trKpa, setTrKpa] = useState<number>(gp.root?.tensile_stress_kpa || 25000.0);
  const [rar, setRar] = useState<number>(gp.root?.rar || 0.002);
  const kFactor = gp.root?.k_factor || 1.2;
  const [targetFs, setTargetFs] = useState<number>(gp.target_fs || 1.3);

  // Missing data policy (using human readable options)
  const [missingPolicy, setMissingPolicy] = useState<string>(
    project?.recommendation_settings?.missing_data_policy || 'RENORMALIZE_AVAILABLE'
  );
  const [totalBudget, setTotalBudget] = useState<number>(500000);

  const steps = [
    { title: '1. Choose Area', subtitle: 'Select boundary', icon: MapPin },
    { title: '2. Add Data', subtitle: 'Verify elevation & vegetation', icon: FileCheck },
    { title: '3. Review Settings', subtitle: 'Priority goals & soil', icon: Sliders },
    { title: '4. Run Analysis', subtitle: 'Execute decision model', icon: Play },
    { title: '5. Explore Results', subtitle: 'View rankings & GIS maps', icon: ShieldCheck },
  ];

  // Pre-flight validation
  const hasDem = Boolean(layers.dem?.path);
  const validationError = !hasDem
    ? 'Elevation data (DEM) is required. Please attach a DEM GeoTIFF before running.'
    : cellSize < 50 || cellSize > 2000
    ? 'Cell size must be between 50m and 2000m.'
    : cPrime < 0 || phiDeg <= 0 || phiDeg >= 90 || depthZ <= 0
    ? 'Soil parameters must be positive physical values.'
    : null;

  const handleExecute = async () => {
    if (!project) {
      setErrorMessage('Please select a project before running an analysis.');
      return;
    }

    if (validationError) {
      setErrorMessage(validationError);
      return;
    }

    setIsRunning(true);
    setErrorMessage(null);
    setRunProgressStage('Discretizing study area into equal ellipsoidal grid parcels...');

    const payload = {
      project_id: project.id,
      cell_size_m: cellSize,
      eligibility_override: {
        min_terrain_coverage_pct: 50.0,
        max_slope_deg: maxSlope,
        enable_ndvi_canopy_filter: enableCanopy,
        ndvi_canopy_threshold: canopyThreshold,
        min_plantable_area_ha: minPlantableArea,
      },
      scoring_weights_override: {
        weight_geotechnical_need: wNeed,
        weight_stability_gain: wGain,
        weight_plantable_area: wArea,
        weight_data_confidence: wConf,
      },
      geotechnical_override: {
        soil: {
          c_prime_kpa: cPrime,
          phi_deg: phiDeg,
          gamma_kn_m3: gammaKn,
          depth_m: depthZ,
          m_water_table: waterM,
        },
        root: {
          tensile_stress_kpa: trKpa,
          rar: rar,
          k_factor: kFactor,
        },
        target_fs: targetFs,
      },
      normalization_override: {
        fs_target: targetFs,
        critical_fs: 1.0,
        max_delta_fs_ref: 15.0,
        max_area_ref_ha: 15.0,
      },
      missing_data_policy: missingPolicy,
      budget_constraints: {
        total_budget_inr: totalBudget,
        cost_per_seedling_inr: 45.0,
        labor_cost_per_ha_inr: 8500.0,
      },
    };

    try {
      setRunProgressStage('Sampling elevation, slope gradients, and vegetation indices...');
      const results = await api.runRecommendations(payload);
      setRunProgressStage('Calculating limit-equilibrium safety factors and ranking parcels...');
      setCompletedResults(results);
      onAnalysisComplete(results);
      // Advance to Step 5 (Explore Results)
      setCurrentStep(4);
    } catch (err: any) {
      setErrorMessage(err.message || 'Execution failed. Check backend connection.');
    } finally {
      setIsRunning(false);
      setRunProgressStage('');
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-8 animate-fade-in">
      {/* Wizard Header */}
      <div className="p-6 rounded-3xl bg-terra-forest/40 border border-terra-border/40 backdrop-blur-xl space-y-5 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-xl font-display font-semibold text-terra-ivory flex items-center gap-2">
              <Sliders className="w-5 h-5 text-terra-mint" />
              <span>Step-by-Step Analysis Workflow</span>
            </h2>
            <p className="text-xs text-terra-muted mt-1">
              Select your study area, verify elevation data, pick your restoration goal, and compute prioritized parcels.
            </p>
          </div>

          <div className="text-xs font-mono text-slate-700 bg-slate-100 px-3 py-1.5 rounded-xl border border-slate-200 self-start">
            Step {currentStep + 1} of 5
          </div>
        </div>

        {/* Stepper Navigation Indicator */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 border-t border-slate-100 pt-4">
          {steps.map((s, idx) => {
            const isDone = currentStep > idx;
            const isCurrent = currentStep === idx;

            return (
              <button
                key={idx}
                type="button"
                onClick={() => !isRunning && setCurrentStep(idx)}
                disabled={isRunning}
                className={`p-2.5 rounded-2xl flex items-center gap-2.5 text-xs font-semibold transition text-left cursor-pointer border ${
                  isCurrent
                    ? 'bg-emerald-50 border-emerald-400 text-slate-900 shadow-xs'
                    : isDone
                    ? 'bg-emerald-50/50 border-emerald-200 text-emerald-800'
                    : 'bg-slate-50 border-slate-200 text-slate-400 hover:text-slate-700'
                }`}
              >
                <div
                  className={`w-6 h-6 rounded-lg flex items-center justify-center text-[11px] font-mono shrink-0 ${
                    isCurrent
                      ? 'bg-emerald-600 text-white font-bold'
                      : isDone
                      ? 'bg-emerald-200 text-emerald-800'
                      : 'bg-slate-200 text-slate-500'
                  }`}
                >
                  {isDone ? <CheckCircle2 className="w-3.5 h-3.5" /> : idx + 1}
                </div>
                <div className="min-w-0">
                  <span className="block truncate text-[11px] leading-tight text-slate-900">{s.title}</span>
                  <span className="text-[10px] text-slate-500 font-normal truncate hidden md:block">
                    {s.subtitle}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Step Panels */}
      <div className="rounded-3xl p-6 sm:p-8 bg-terra-forest/30 border border-terra-border/40 backdrop-blur-xl min-h-[420px] shadow-2xl">
        <TransitionPanel activeIndex={currentStep}>
          {/* STEP 1: CHOOSE YOUR AREA */}
          <div className="space-y-6">
            <div>
              <span className="text-[11px] font-mono uppercase tracking-wider text-terra-mint font-semibold">
                Step 1 of 5
              </span>
              <h3 className="text-lg font-display font-semibold text-terra-ivory mt-0.5">
                Choose Your Study Area
              </h3>
              <p className="text-xs text-terra-muted mt-1">
                Select the watershed or geographic boundary you want to analyze for hillslope stability and reforestation.
              </p>
            </div>

            {/* Project Selection / Switching */}
            {projects.length > 1 && onSelectProject && (
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
                <label className="block text-xs font-semibold text-slate-800">
                  Select Active Workspace:
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {projects.map((p) => {
                    const isSelected = p.id === project?.id;
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => onSelectProject(p.id)}
                        className={`p-3 rounded-xl border text-left text-xs transition cursor-pointer flex items-center justify-between ${
                          isSelected
                            ? 'bg-white border-emerald-400 text-slate-900 shadow-xs'
                            : 'bg-white border-slate-200 text-slate-600 hover:text-slate-900 hover:border-slate-300'
                        }`}
                      >
                        <div>
                          <span className="font-semibold block">{p.name}</span>
                          <span className="text-[10px] text-slate-500">
                            {p.id === 'wayanad_pilot' ? 'Demo Watershed (Western Ghats)' : (p.study_area_type || 'Custom Area')}
                          </span>
                        </div>
                        {isSelected && <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Active Area Summary */}
            <div className="p-5 rounded-2xl bg-terra-deep/60 border border-terra-border/40 space-y-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-terra-mint/15 text-terra-mint border border-terra-mint/25 flex items-center justify-center">
                    <MapPin className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-terra-ivory">
                      {project?.name || 'Selected Study Corridor'}
                    </h4>
                    <p className="text-xs text-terra-slate">
                      Estimated area extent: <span className="font-mono text-terra-ivory font-semibold">{approxHa.toLocaleString()} hectares</span>
                    </p>
                  </div>
                </div>

                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/25">
                  Boundary Defined
                </span>
              </div>

              {/* Coordinates Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs pt-2">
                <div className="p-3 rounded-xl bg-terra-forest/40 border border-terra-border/40">
                  <span className="text-terra-slate block text-[11px]">West Longitude</span>
                  <span className="font-mono text-terra-ivory font-semibold">{bounds.minx.toFixed(4)}°E</span>
                </div>
                <div className="p-3 rounded-xl bg-terra-forest/40 border border-terra-border/40">
                  <span className="text-terra-slate block text-[11px]">South Latitude</span>
                  <span className="font-mono text-terra-ivory font-semibold">{bounds.miny.toFixed(4)}°N</span>
                </div>
                <div className="p-3 rounded-xl bg-terra-forest/40 border border-terra-border/40">
                  <span className="text-terra-slate block text-[11px]">East Longitude</span>
                  <span className="font-mono text-terra-ivory font-semibold">{bounds.maxx.toFixed(4)}°E</span>
                </div>
                <div className="p-3 rounded-xl bg-terra-forest/40 border border-terra-border/40">
                  <span className="text-terra-slate block text-[11px]">North Latitude</span>
                  <span className="font-mono text-terra-ivory font-semibold">{bounds.maxy.toFixed(4)}°N</span>
                </div>
              </div>

              <p className="text-xs text-terra-slate leading-relaxed">
                TerraShield AI will discretize this geographic domain into uniform parcel polygons using ellipsoidal geodetic formulas for unbiased zonal aggregation.
              </p>
            </div>
          </div>

          {/* STEP 2: ADD YOUR DATA */}
          <div className="space-y-6">
            <div>
              <span className="text-[11px] font-mono uppercase tracking-wider text-terra-mint font-semibold">
                Step 2 of 5
              </span>
              <h3 className="text-lg font-display font-semibold text-terra-ivory mt-0.5">
                Verify Geospatial Datasets
              </h3>
              <p className="text-xs text-terra-muted mt-1">
                Confirm available elevation and vegetation rasters. Missing optional layers will be handled gracefully.
              </p>
            </div>

            {/* Layer Checklist */}
            <div className="space-y-3">
              {[
                {
                  id: 'dem',
                  name: 'Elevation Model (DEM)',
                  role: 'Used to calculate continuous terrain slope gradients, aspects, and gravitational forces.',
                  required: true,
                  isReady: Boolean(layers.dem?.path),
                  actionText: 'Attach DEM in Data Library',
                },
                {
                  id: 'slope',
                  name: 'Terrain Slope Gradient (°)',
                  role: 'Used to determine driving shear stresses along hillslope regolith planes.',
                  required: true,
                  isReady: Boolean(layers.slope?.path),
                  actionText: 'Process Slope in Data Library',
                },
                {
                  id: 'aspect',
                  name: 'Topographic Aspect (Compass Azimuth)',
                  role: 'Used to evaluate hillslope orientation, moisture retention, and solar exposure.',
                  required: false,
                  isReady: Boolean(layers.aspect?.path),
                  actionText: 'Derived automatically during terrain processing',
                },
                {
                  id: 'ndvi',
                  name: 'Vegetation Index (NDVI)',
                  role: 'Derived from Sentinel-2 satellite imagery to indicate existing vegetation canopy density.',
                  required: false,
                  isReady: Boolean(layers.ndvi?.path),
                  actionText: 'Upload Sentinel-2 GeoTIFF',
                },
                {
                  id: 'fs_baseline',
                  name: 'Baseline Slope Stability (FS₀)',
                  role: 'Initial factor of safety without tree roots; computed automatically by infinite-slope solver.',
                  required: false,
                  isReady: Boolean(layers.fs_baseline?.path),
                  actionText: 'Computed on demand by solver',
                },
              ].map((item) => (
                <div
                  key={item.id}
                  className="p-4 rounded-2xl bg-terra-deep/60 border border-terra-border/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-terra-ivory text-xs sm:text-sm">
                        {item.name}
                      </span>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
                          item.required
                            ? 'bg-amber-500/15 text-amber-300 border border-amber-500/25'
                            : 'bg-terra-slate/15 text-terra-slate'
                        }`}
                      >
                        {item.required ? 'Required' : 'Optional'}
                      </span>
                    </div>
                    <p className="text-xs text-terra-slate leading-relaxed">{item.role}</p>
                  </div>

                  <div className="shrink-0">
                    {item.isReady ? (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-mono font-semibold">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        Ready
                      </span>
                    ) : item.required ? (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-mono font-semibold">
                        <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                        Missing Required
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-terra-slate/15 border border-terra-slate/30 text-terra-slate text-xs font-mono">
                        Optional (Auto-filled)
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Expandable Technical Data Details */}
            <div className="rounded-2xl border border-terra-border/40 overflow-hidden bg-terra-deep/40">
              <button
                type="button"
                onClick={() => setIsDataDetailsOpen(!isDataDetailsOpen)}
                className="w-full px-4 py-3 flex items-center justify-between text-xs text-terra-muted hover:text-terra-ivory transition cursor-pointer"
              >
                <span className="font-mono font-semibold">
                  Technical Data Details & Diagnostics (CRS, Resolution, NoData)
                </span>
                {isDataDetailsOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>

              {isDataDetailsOpen && (
                <div className="p-4 border-t border-terra-border/30 text-xs text-terra-slate space-y-2 font-mono">
                  <div>Coordinate System: <span className="text-terra-ivory">{project?.native_crs || 'EPSG:4326 (WGS 84)'}</span></div>
                  <div>DEM Source: <span className="text-terra-ivory">NASA SRTM NASADEM Global 1 Arc-Second (~30m resolution)</span></div>
                  <div>NDVI Sensor: <span className="text-terra-ivory">Sentinel-2 BOA Surface Reflectance Band 4 (Red) + Band 8 (NIR) (~10m)</span></div>
                  <div>NoData Handling: <span className="text-terra-ivory">Filtered using NaN masking and valid pixel coverage threshold (≥50%)</span></div>
                </div>
              )}
            </div>
          </div>

          {/* STEP 3: REVIEW SETTINGS */}
          <div className="space-y-6">
            <div>
              <span className="text-[11px] font-mono uppercase tracking-wider text-terra-mint font-semibold">
                Step 3 of 5
              </span>
              <h3 className="text-lg font-display font-semibold text-terra-ivory mt-0.5">
                Review Modeling Settings
              </h3>
              <p className="text-xs text-terra-muted mt-1">
                Choose your restoration focus and check parameters. Pre-configured defaults are ready to run.
              </p>
            </div>

            {/* Basic Settings: 1. Priority Focus Preset */}
            <div className="space-y-3">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-terra-ivory">
                <span>1. Choose Restoration Priority Goal</span>
                <HelpTooltip
                  term="Priority Focus"
                  text="Determines the mathematical weight given to slope stability need, modeled stability gain, plantable area, and data reliability."
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {[
                  {
                    id: 'balanced' as const,
                    title: 'Balanced Restoration (Recommended)',
                    desc: 'Balanced focus on slope risk (35%), stability improvement (30%), and plantable area (20%).',
                  },
                  {
                    id: 'landslide' as const,
                    title: 'Critical Landslide Protection',
                    desc: 'Prioritizes steep, vulnerable hillslopes with high geotechnical instability risk (50% need, 35% gain).',
                  },
                  {
                    id: 'plantable' as const,
                    title: 'Maximum Plantable Hectares',
                    desc: 'Prioritizes large contiguous plantable zones with verified data confidence (50% area, 20% gain).',
                  },
                ].map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => applyPriorityPreset(item.id)}
                    className={`p-4 rounded-2xl border text-left text-xs transition cursor-pointer flex flex-col justify-between ${
                      priorityPreset === item.id
                        ? 'bg-terra-forest/80 border-terra-mint text-terra-ivory shadow-lg shadow-terra-mint/5'
                        : 'bg-terra-deep/60 border-terra-border/40 text-terra-muted hover:text-terra-ivory'
                    }`}
                  >
                    <div>
                      <span className="font-semibold block text-terra-ivory mb-1">{item.title}</span>
                      <p className="text-[11px] text-terra-slate leading-relaxed">{item.desc}</p>
                    </div>
                    {priorityPreset === item.id && (
                      <span className="mt-2 text-[10px] font-mono text-terra-mint font-semibold">
                        ● Selected
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Basic Settings: 2. Parcel Size Slider */}
            <div className="p-5 rounded-2xl bg-terra-deep/60 border border-terra-border/40 space-y-2">
              <div className="flex justify-between items-center text-xs">
                <div className="flex items-center gap-1.5 font-semibold text-terra-ivory">
                  <span>2. Target Parcel Side Length</span>
                  <HelpTooltip
                    term="Parcel Discretization"
                    text="Divides the study terrain into uniform square evaluation blocks for ranking."
                  />
                </div>
                <span className="font-mono text-terra-mint font-semibold">
                  {cellSize} meters (~{((cellSize * cellSize) / 10000).toFixed(1)} ha / parcel)
                </span>
              </div>
              <input
                type="range"
                min="100"
                max="600"
                step="50"
                value={cellSize}
                onChange={(e) => setCellSize(parseInt(e.target.value))}
                className="w-full accent-terra-mint cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-terra-slate font-mono">
                <span>100m (Fine ~1 ha)</span>
                <span>300m (Recommended ~9 ha)</span>
                <span>600m (Broad ~36 ha)</span>
              </div>
            </div>

            {/* Expandable Advanced Geotechnical Settings */}
            <div className="rounded-2xl border border-terra-border/40 overflow-hidden bg-terra-deep/40">
              <button
                type="button"
                onClick={() => setIsAdvancedOpen(!isAdvancedOpen)}
                className="w-full px-5 py-3.5 flex items-center justify-between text-xs text-terra-muted hover:text-terra-ivory transition cursor-pointer"
              >
                <div className="flex items-center gap-2 font-mono font-semibold">
                  <Sliders className="w-4 h-4 text-terra-mint" />
                  <span>Advanced Geotechnical Parameters & Scoring Weights</span>
                </div>
                {isAdvancedOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>

              {isAdvancedOpen && (
                <div className="p-5 border-t border-terra-border/30 space-y-5 text-xs">
                  {/* Soil Mechanics */}
                  <div>
                    <h5 className="font-semibold text-terra-ivory mb-2 font-mono text-[11px] uppercase tracking-wider text-terra-mint">
                      Soil Shear Strength Parameters (Mohr-Coulomb)
                    </h5>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                      <div>
                        <label className="text-terra-muted block mb-1">
                          Effective Cohesion c' (kPa)
                          <HelpTooltip text="Electrostatic and cementation bonding resisting shear." />
                        </label>
                        <input
                          type="number"
                          step="0.5"
                          value={cPrime}
                          onChange={(e) => setCPrime(parseFloat(e.target.value) || 0)}
                          className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 font-mono focus:outline-none focus:border-emerald-500 focus:bg-white"
                        />
                      </div>

                      <div>
                        <label className="text-terra-muted block mb-1">
                          Internal Friction Angle φ' (°)
                          <HelpTooltip text="Inter-granular friction angle between soil particles." />
                        </label>
                        <input
                          type="number"
                          step="0.5"
                          value={phiDeg}
                          onChange={(e) => setPhiDeg(parseFloat(e.target.value) || 0)}
                          className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 font-mono focus:outline-none focus:border-emerald-500 focus:bg-white"
                        />
                      </div>

                      <div>
                        <label className="text-terra-muted block mb-1">
                          Unit Weight γ (kN/m³)
                          <HelpTooltip text="Bulk density of the regolith." />
                        </label>
                        <input
                          type="number"
                          step="0.5"
                          value={gammaKn}
                          onChange={(e) => setGammaKn(parseFloat(e.target.value) || 0)}
                          className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 font-mono focus:outline-none focus:border-emerald-500 focus:bg-white"
                        />
                      </div>

                      <div>
                        <label className="text-terra-muted block mb-1">
                          Soil Depth z (m)
                          <HelpTooltip text="Depth from ground surface to potential sliding plane." />
                        </label>
                        <input
                          type="number"
                          step="0.1"
                          value={depthZ}
                          onChange={(e) => setDepthZ(parseFloat(e.target.value) || 0)}
                          className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 font-mono focus:outline-none focus:border-emerald-500 focus:bg-white"
                        />
                      </div>

                      <div>
                        <label className="text-terra-muted block mb-1">
                          Water Table Saturation Ratio m (0 to 1)
                          <HelpTooltip text="Relative saturation of the regolith layer (0 = dry, 1 = fully saturated monsoon condition)." />
                        </label>
                        <input
                          type="number"
                          step="0.05"
                          min="0"
                          max="1"
                          value={waterM}
                          onChange={(e) => setWaterM(parseFloat(e.target.value) || 0)}
                          className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 font-mono focus:outline-none focus:border-emerald-500 focus:bg-white"
                        />
                      </div>

                      <div>
                        <label className="text-terra-muted block mb-1">
                          Target Factor of Safety
                          <HelpTooltip text="Standard geotechnical threshold (1.3) designating acceptable stability margin." />
                        </label>
                        <input
                          type="number"
                          step="0.1"
                          value={targetFs}
                          onChange={(e) => setTargetFs(parseFloat(e.target.value) || 1.3)}
                          className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 font-mono focus:outline-none focus:border-emerald-500 focus:bg-white"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Root Reinforcement */}
                  <div className="pt-3 border-t border-terra-border/30">
                    <h5 className="font-semibold text-terra-ivory mb-2 font-mono text-[11px] uppercase tracking-wider text-terra-mint">
                      Root Reinforcement (Wu-Waldron Model)
                    </h5>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="text-terra-muted block mb-1">
                          Root Tensile Strength Tr (kPa)
                          <HelpTooltip text="Tensile resistance of root fibers crossing shear plane." />
                        </label>
                        <input
                          type="number"
                          step="1000"
                          value={trKpa}
                          onChange={(e) => setTrKpa(parseFloat(e.target.value) || 0)}
                          className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 font-mono focus:outline-none focus:border-emerald-500 focus:bg-white"
                        />
                      </div>

                      <div>
                        <label className="text-terra-muted block mb-1">
                          Root Area Ratio (RAR)
                          <HelpTooltip text="Fraction of soil shear plane cross-section occupied by root fibers." />
                        </label>
                        <input
                          type="number"
                          step="0.0005"
                          value={rar}
                          onChange={(e) => setRar(parseFloat(e.target.value) || 0)}
                          className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 font-mono focus:outline-none focus:border-emerald-500 focus:bg-white"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Missing Data Policy */}
                  <div className="pt-3 border-t border-terra-border/30">
                    <label className="text-terra-muted block mb-1 font-semibold">
                      Missing Data Handling Policy:
                    </label>
                    <select
                      value={missingPolicy}
                      onChange={(e) => setMissingPolicy(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 text-xs font-mono focus:outline-none focus:border-emerald-500"
                    >
                      <option value="RENORMALIZE_AVAILABLE">
                        Adjust Scores Using Available Data (Recommended — redistributes weights)
                      </option>
                      <option value="ZERO_FILL">
                        Treat Missing Scores as Zero (Lowers overall rank if layer missing)
                      </option>
                      <option value="BLOCK_UNAVAILABLE">
                        Exclude Results with Missing Required Inputs (Strict data policy)
                      </option>
                    </select>
                  </div>

                  {/* Safety & Budget Constraints */}
                  <div className="pt-3 border-t border-terra-border/30 grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="text-terra-muted block mb-1">
                        Max Slope Threshold (°)
                        <HelpTooltip text="Excludes slopes steeper than this angle from planting recommendations." />
                      </label>
                      <input
                        type="number"
                        min="20"
                        max="60"
                        value={maxSlope}
                        onChange={(e) => setMaxSlope(parseFloat(e.target.value) || 45.0)}
                        className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 font-mono focus:outline-none focus:border-emerald-500 focus:bg-white"
                      />
                    </div>
                    <div>
                      <label className="text-terra-muted block mb-1">
                        Total Planting Budget (INR ₹)
                        <HelpTooltip text="Allocates seedlings and labor constraints across prioritized parcels." />
                      </label>
                      <input
                        type="number"
                        step="50000"
                        value={totalBudget}
                        onChange={(e) => setTotalBudget(parseFloat(e.target.value) || 500000)}
                        className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 font-mono focus:outline-none focus:border-emerald-500 focus:bg-white"
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* STEP 4: RUN ANALYSIS */}
          <div className="space-y-6">
            <div>
              <span className="text-[11px] font-mono uppercase tracking-wider text-terra-mint font-semibold">
                Step 4 of 5
              </span>
              <h3 className="text-lg font-display font-semibold text-terra-ivory mt-0.5">
                Review Summary & Execute Analysis
              </h3>
              <p className="text-xs text-terra-muted mt-1">
                Confirm your configuration before initiating deterministic zonal analysis and ranking.
              </p>
            </div>

            {/* Pre-flight Execution Summary */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1">
                <span className="text-slate-500 block text-[11px] font-mono uppercase">Study Area</span>
                <span className="text-slate-900 font-semibold block">{project?.name || 'Active Study Area'}</span>
                <span className="text-slate-600 text-[11px]">~{approxHa.toLocaleString()} hectares</span>
              </div>

              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1">
                <span className="text-slate-500 block text-[11px] font-mono uppercase">Resolution</span>
                <span className="text-slate-900 font-semibold block">{cellSize}m Grid Parcels</span>
                <span className="text-slate-600 text-[11px]">~{((cellSize * cellSize) / 10000).toFixed(1)} ha per evaluation unit</span>
              </div>

              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1">
                <span className="text-slate-500 block text-[11px] font-mono uppercase">Priority Goal</span>
                <span className="text-slate-900 font-semibold block capitalize">
                  {priorityPreset === 'balanced'
                    ? 'Balanced Restoration'
                    : priorityPreset === 'landslide'
                    ? 'Landslide Hazard Mitigation'
                    : 'Maximum Plantable Coverage'}
                </span>
                <span className="text-slate-600 text-[11px]">
                  Need: {wNeed} | Gain: {wGain} | Area: {wArea} | Conf: {wConf}
                </span>
              </div>

              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1">
                <span className="text-slate-500 block text-[11px] font-mono uppercase">Safety Threshold</span>
                <span className="text-slate-900 font-semibold block">Max Slope {maxSlope}°</span>
                <span className="text-slate-600 text-[11px]">Target Stability Margin FS ≥ {targetFs}</span>
              </div>
            </div>

            {/* Error or Validation Notification */}
            {errorMessage && (
              <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Execution Action Button */}
            <div className="pt-2">
              <button
                type="button"
                onClick={handleExecute}
                disabled={isRunning || Boolean(validationError)}
                className="w-full py-4 rounded-2xl bg-terra-mint hover:bg-terra-mint/90 disabled:opacity-50 text-terra-deep font-bold text-sm transition shadow-xl shadow-terra-mint/15 flex items-center justify-center gap-2 cursor-pointer"
              >
                {isRunning ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>{runProgressStage || 'Executing Geospatial Pipeline...'}</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-terra-deep" />
                    <span>Run Analysis</span>
                  </>
                )}
              </button>

              {validationError && (
                <p className="text-xs text-rose-400 mt-2 text-center">{validationError}</p>
              )}
            </div>
          </div>

          {/* STEP 5: EXPLORE RESULTS */}
          <div className="space-y-6">
            <div className="text-center py-4 space-y-2">
              <div className="w-14 h-14 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mx-auto shadow-inner">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <h3 className="text-xl font-display font-semibold text-terra-ivory">
                Analysis Completed Successfully
              </h3>
              <p className="text-xs text-terra-muted max-w-md mx-auto">
                Candidate parcels have been ranked by multi-criteria priority scores and stability improvement.
              </p>
            </div>

            {completedResults && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-center">
                  <span className="text-slate-500 block text-[11px] mb-1">Evaluated Parcels</span>
                  <span className="text-lg font-mono font-bold text-slate-900">
                    {completedResults.total_parcels}
                  </span>
                </div>
                <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-center">
                  <span className="text-emerald-800 block text-[11px] mb-1 font-semibold">Recommended</span>
                  <span className="text-lg font-mono font-bold text-emerald-700">
                    {completedResults.eligible_count}
                  </span>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-center">
                  <span className="text-slate-500 block text-[11px] mb-1">Excluded</span>
                  <span className="text-lg font-mono font-bold text-slate-400">
                    {completedResults.excluded_count}
                  </span>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-center">
                  <span className="text-slate-500 block text-[11px] mb-1">Plantable Area</span>
                  <span className="text-lg font-mono font-bold text-slate-900">
                    {(completedResults.total_plantable_area_ha || 0).toFixed(0)} ha
                  </span>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
              <button
                type="button"
                onClick={() => onNavigateTab && onNavigateTab('results')}
                className="py-3 px-4 rounded-xl bg-terra-mint text-terra-deep font-semibold text-xs hover:bg-terra-mint/90 transition shadow-lg shadow-terra-mint/10 flex items-center justify-center gap-2 cursor-pointer"
              >
                <BarChart3 className="w-4 h-4" />
                <span>View Full Results & Rankings</span>
              </button>

              <button
                type="button"
                onClick={() => onNavigateTab && onNavigateTab('map')}
                className="py-3 px-4 rounded-xl bg-terra-forest text-terra-ivory font-semibold text-xs border border-terra-border/60 hover:bg-terra-forest/80 transition flex items-center justify-center gap-2 cursor-pointer"
              >
                <Compass className="w-4 h-4 text-terra-mint" />
                <span>Inspect on Geospatial Map</span>
              </button>
            </div>
          </div>
        </TransitionPanel>
      </div>

      {/* Wizard Footer Controls */}
      <div className="flex items-center justify-between pt-2">
        <button
          type="button"
          onClick={() => setCurrentStep((prev) => Math.max(0, prev - 1))}
          disabled={currentStep === 0 || isRunning}
          className="px-4 py-2.5 rounded-xl bg-terra-forest/60 border border-terra-border/40 text-xs font-semibold text-terra-muted hover:text-terra-ivory disabled:opacity-40 flex items-center gap-1.5 cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Previous Step</span>
        </button>

        {currentStep < steps.length - 1 && (
          <button
            type="button"
            onClick={() => setCurrentStep((prev) => Math.min(steps.length - 1, prev + 1))}
            disabled={isRunning}
            className="px-5 py-2.5 rounded-xl bg-terra-forest hover:bg-terra-forest/80 text-xs font-semibold text-terra-ivory flex items-center gap-1.5 cursor-pointer border border-terra-border/50 shadow-sm"
          >
            <span>Next Step</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
};

export default AnalysisWizardView;
