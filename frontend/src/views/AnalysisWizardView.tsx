import React, { useState } from 'react';
import type { ProjectMetadata, RecommendationRunResponse } from '../api/types';
import { api } from '../api/client';
import { TransitionPanel } from '../components/motion-primitives/TransitionPanel';
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
} from 'lucide-react';

interface AnalysisWizardViewProps {
  project: ProjectMetadata | null;
  onAnalysisComplete: (results: RecommendationRunResponse) => void;
  onNavigateTab?: (tab: any) => void;
}

export const AnalysisWizardView: React.FC<AnalysisWizardViewProps> = ({
  project,
  onAnalysisComplete,
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const bounds = project?.bounds || { minx: 76.0, miny: 11.55, maxx: 76.1, maxy: 11.65 };
  const layers = project?.layers || {};

  // Configuration State initialized from active project
  const [cellSize, setCellSize] = useState<number>(
    project?.recommendation_settings?.cell_size_m || 300
  );
  const maxSlope = project?.recommendation_settings?.eligibility_settings?.max_slope_deg || 45.0;
  const enableCanopy = project?.recommendation_settings?.eligibility_settings?.enable_ndvi_canopy_filter || false;
  const canopyThreshold = project?.recommendation_settings?.eligibility_settings?.ndvi_canopy_threshold || 0.65;
  const minPlantableArea = project?.recommendation_settings?.eligibility_settings?.min_plantable_area_ha || 0.25;

  // Scoring Weights
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

  // Geotechnical Parameters
  const gp = project?.geotechnical_parameters || {};
  const [cPrime, setCPrime] = useState<number>(gp.soil?.c_prime_kpa || 8.0);
  const [phiDeg, setPhiDeg] = useState<number>(gp.soil?.phi_deg || 26.0);
  const [gammaKn, setGammaKn] = useState<number>(gp.soil?.gamma_kn_m3 || 18.5);
  const [depthZ, setDepthZ] = useState<number>(gp.soil?.depth_m || 1.8);
  const waterM = gp.soil?.m_water_table || 0.5;

  const [trKpa, setTrKpa] = useState<number>(gp.root?.tensile_stress_kpa || 25000.0);
  const [rar, setRar] = useState<number>(gp.root?.rar || 0.002);
  const kFactor = gp.root?.k_factor || 1.2;
  const targetFs = gp.target_fs || 1.3;

  // Normalization & Budget
  const maxDeltaFsRef = 15.0;
  const missingPolicy = 'RENORMALIZE_AVAILABLE';
  const totalBudget = 500000;

  const steps = [
    { title: 'Study Area', icon: MapPin },
    { title: 'Data Layers', icon: FileCheck },
    { title: 'Parameters', icon: Sliders },
    { title: 'Prioritization', icon: ShieldCheck },
    { title: 'Review & Run', icon: Play },
  ];

  const handleExecute = async () => {
    if (!project) {
      setErrorMessage('Please select a project before running an analysis.');
      return;
    }

    setIsRunning(true);
    setErrorMessage(null);

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
        max_delta_fs_ref: maxDeltaFsRef,
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
      const results = await api.runRecommendations(payload);
      onAnalysisComplete(results);
    } catch (err: any) {
      setErrorMessage(err.message || 'Execution failed. Check backend connection.');
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-8 animate-fade-in">
      {/* Wizard Header */}
      <div className="p-6 rounded-3xl bg-terra-forest/40 border border-terra-border/40 backdrop-blur-xl space-y-4">
        <div>
          <h2 className="text-xl font-display font-semibold text-terra-ivory flex items-center gap-2">
            <Sliders className="w-5 h-5 text-terra-mint" />
            <span>Guided Analysis Configuration</span>
          </h2>
          <p className="text-xs text-terra-muted mt-1">
            Step-by-step guidance to discretize terrain, calibrate geotechnical stability, and score planting parcels.
          </p>
        </div>

        {/* Stepper Navigation Indicator */}
        <div className="flex items-center justify-between border-t border-terra-border/40 pt-4">
          {steps.map((s, idx) => {
            const isDone = currentStep > idx;
            const isCurrent = currentStep === idx;

            return (
              <button
                key={idx}
                onClick={() => setCurrentStep(idx)}
                className={`flex items-center gap-2 text-xs font-semibold transition cursor-pointer ${
                  isCurrent
                    ? 'text-terra-ivory'
                    : isDone
                    ? 'text-terra-mint'
                    : 'text-terra-slate hover:text-terra-muted'
                }`}
              >
                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-mono border ${
                    isCurrent
                      ? 'bg-terra-forest border-terra-mint text-terra-mint shadow-md'
                      : isDone
                      ? 'bg-terra-mint/20 border-terra-mint/40 text-terra-mint'
                      : 'bg-terra-deep/80 border-terra-border/40 text-terra-slate'
                  }`}
                >
                  {isDone ? <CheckCircle2 className="w-4 h-4" /> : idx + 1}
                </div>
                <span className="hidden md:inline">{s.title}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Step Panels */}
      <div className="rounded-3xl p-6 bg-terra-forest/30 border border-terra-border/40 backdrop-blur-xl min-h-[380px]">
        <TransitionPanel activeIndex={currentStep}>
          {/* STEP 1: Study Area */}
          <div className="space-y-4">
            <h3 className="text-base font-display font-semibold text-terra-ivory">
              1. Verify Study Area & Geographic Boundary
            </h3>
            <p className="text-xs text-terra-muted">
              Confirm the bounding coordinates for candidate parcel discretization.
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 rounded-xl bg-terra-deep/70 border border-terra-border/40">
                <span className="text-terra-slate block text-[11px]">West Longitude</span>
                <span className="font-mono text-terra-ivory font-semibold">{bounds.minx.toFixed(4)}°E</span>
              </div>
              <div className="p-3 rounded-xl bg-terra-deep/70 border border-terra-border/40">
                <span className="text-terra-slate block text-[11px]">South Latitude</span>
                <span className="font-mono text-terra-ivory font-semibold">{bounds.miny.toFixed(4)}°N</span>
              </div>
              <div className="p-3 rounded-xl bg-terra-deep/70 border border-terra-border/40">
                <span className="text-terra-slate block text-[11px]">East Longitude</span>
                <span className="font-mono text-terra-ivory font-semibold">{bounds.maxx.toFixed(4)}°E</span>
              </div>
              <div className="p-3 rounded-xl bg-terra-deep/70 border border-terra-border/40">
                <span className="text-terra-slate block text-[11px]">North Latitude</span>
                <span className="font-mono text-terra-ivory font-semibold">{bounds.maxy.toFixed(4)}°N</span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-terra-deep/60 border border-terra-border/40 text-xs text-terra-muted space-y-2">
              <div className="flex items-center gap-2 text-terra-ivory font-semibold">
                <MapPin className="w-4 h-4 text-terra-mint" />
                <span>Selected Project: {project?.name || 'No Project Selected'}</span>
              </div>
              <p>
                Spatial discretization produces ~{((cellSize * cellSize) / 10000).toFixed(2)} hectare parcels using
                WGS 84 ellipsoidal distance calculations.
              </p>
            </div>
          </div>

          {/* STEP 2: Data Layers */}
          <div className="space-y-4">
            <h3 className="text-base font-display font-semibold text-terra-ivory">
              2. Ingested Data Layers & Verification Status
            </h3>
            <p className="text-xs text-terra-muted">
              TerraShield AI performs multi-raster zonal statistics across attached inputs.
            </p>

            <div className="space-y-2 text-xs">
              {[
                { id: 'dem', name: 'Digital Elevation Model (DEM)', req: true },
                { id: 'slope', name: 'Continuous Slope Gradient (°)', req: true },
                { id: 'aspect', name: 'Topographic Compass Azimuth', req: false },
                { id: 'ndvi', name: 'Sentinel-2 Vegetation Index (NDVI)', req: false },
                { id: 'fs_baseline', name: 'Baseline Factor of Safety (FS₀)', req: false },
              ].map((l) => {
                const isAttached = Boolean(layers[l.id]?.path);

                return (
                  <div
                    key={l.id}
                    className="p-3 rounded-xl bg-terra-deep/70 border border-terra-border/40 flex items-center justify-between"
                  >
                    <div>
                      <span className="font-medium text-terra-ivory">{l.name}</span>
                      <span className="ml-2 text-[10px] text-terra-slate">
                        {l.req ? '(Required)' : '(Optional)'}
                      </span>
                    </div>
                    <span
                      className={`font-mono text-[11px] px-2.5 py-0.5 rounded-full ${
                        isAttached
                          ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                          : l.req
                          ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                          : 'bg-terra-slate/15 text-terra-slate'
                      }`}
                    >
                      {isAttached ? '✅ Ready' : l.req ? '❌ Missing' : '⚠️ Optional'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* STEP 3: Parameters */}
          <div className="space-y-4">
            <h3 className="text-base font-display font-semibold text-terra-ivory">
              3. Geotechnical Parameter Calibration
            </h3>
            <p className="text-xs text-terra-muted">
              Configure soil cohesion and Wu-Waldron root reinforcement parameters.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="space-y-2">
                <label className="text-terra-muted font-semibold block">Effective Cohesion c' (kPa)</label>
                <input
                  type="number"
                  value={cPrime}
                  onChange={(e) => setCPrime(parseFloat(e.target.value) || 0)}
                  className="w-full bg-terra-deep border border-terra-border/60 rounded-xl px-3 py-2 text-terra-ivory font-mono focus:outline-none focus:border-terra-mint"
                />
              </div>

              <div className="space-y-2">
                <label className="text-terra-muted font-semibold block">Effective Friction Angle φ' (°)</label>
                <input
                  type="number"
                  value={phiDeg}
                  onChange={(e) => setPhiDeg(parseFloat(e.target.value) || 0)}
                  className="w-full bg-terra-deep border border-terra-border/60 rounded-xl px-3 py-2 text-terra-ivory font-mono focus:outline-none focus:border-terra-mint"
                />
              </div>

              <div className="space-y-2">
                <label className="text-terra-muted font-semibold block">Soil Unit Weight γ (kN/m³)</label>
                <input
                  type="number"
                  value={gammaKn}
                  onChange={(e) => setGammaKn(parseFloat(e.target.value) || 0)}
                  className="w-full bg-terra-deep border border-terra-border/60 rounded-xl px-3 py-2 text-terra-ivory font-mono focus:outline-none focus:border-terra-mint"
                />
              </div>

              <div className="space-y-2">
                <label className="text-terra-muted font-semibold block">Soil Regolith Depth z (m)</label>
                <input
                  type="number"
                  value={depthZ}
                  onChange={(e) => setDepthZ(parseFloat(e.target.value) || 0)}
                  className="w-full bg-terra-deep border border-terra-border/60 rounded-xl px-3 py-2 text-terra-ivory font-mono focus:outline-none focus:border-terra-mint"
                />
              </div>

              <div className="space-y-2">
                <label className="text-terra-muted font-semibold block">Root Tensile Strength Tr (kPa)</label>
                <input
                  type="number"
                  value={trKpa}
                  onChange={(e) => setTrKpa(parseFloat(e.target.value) || 0)}
                  className="w-full bg-terra-deep border border-terra-border/60 rounded-xl px-3 py-2 text-terra-ivory font-mono focus:outline-none focus:border-terra-mint"
                />
              </div>

              <div className="space-y-2">
                <label className="text-terra-muted font-semibold block">Root Area Ratio (RAR)</label>
                <input
                  type="number"
                  step="0.0005"
                  value={rar}
                  onChange={(e) => setRar(parseFloat(e.target.value) || 0)}
                  className="w-full bg-terra-deep border border-terra-border/60 rounded-xl px-3 py-2 text-terra-ivory font-mono focus:outline-none focus:border-terra-mint"
                />
              </div>
            </div>
          </div>

          {/* STEP 4: Prioritization */}
          <div className="space-y-4">
            <h3 className="text-base font-display font-semibold text-terra-ivory">
              4. Multi-Criteria Prioritization Weights
            </h3>
            <p className="text-xs text-terra-muted">
              Tune spatial resolution and objective weights for parcel leverage scoring.
            </p>

            <div className="space-y-4 text-xs">
              <div>
                <div className="flex justify-between text-terra-muted font-semibold mb-1">
                  <span>Candidate Parcel Side Length: {cellSize} m</span>
                  <span>~{((cellSize * cellSize) / 10000).toFixed(2)} ha / parcel</span>
                </div>
                <input
                  type="range"
                  min="100"
                  max="1000"
                  step="100"
                  value={cellSize}
                  onChange={(e) => setCellSize(parseInt(e.target.value))}
                  className="w-full accent-terra-mint cursor-pointer"
                />
              </div>

              <div className="grid grid-cols-2 gap-4 pt-2">
                <div>
                  <label className="text-terra-muted font-semibold block mb-1">
                    Geotechnical Need Weight: {wNeed}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={wNeed}
                    onChange={(e) => setWNeed(parseFloat(e.target.value))}
                    className="w-full accent-terra-mint cursor-pointer"
                  />
                </div>
                <div>
                  <label className="text-terra-muted font-semibold block mb-1">
                    Stability Gain (ΔFS) Weight: {wGain}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={wGain}
                    onChange={(e) => setWGain(parseFloat(e.target.value))}
                    className="w-full accent-terra-mint cursor-pointer"
                  />
                </div>
                <div>
                  <label className="text-terra-muted font-semibold block mb-1">
                    Plantable Area Weight: {wArea}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={wArea}
                    onChange={(e) => setWArea(parseFloat(e.target.value))}
                    className="w-full accent-terra-mint cursor-pointer"
                  />
                </div>
                <div>
                  <label className="text-terra-muted font-semibold block mb-1">
                    Data Confidence Weight: {wConf}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={wConf}
                    onChange={(e) => setWConf(parseFloat(e.target.value))}
                    className="w-full accent-terra-mint cursor-pointer"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* STEP 5: Review & Run */}
          <div className="space-y-4">
            <h3 className="text-base font-display font-semibold text-terra-ivory">
              5. Review Configuration & Execute Analysis
            </h3>
            <p className="text-xs text-terra-muted">
              Verify analysis parameters before triggering the deterministic geospatial pipeline.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-3.5 rounded-xl bg-terra-deep/70 border border-terra-border/40 space-y-1">
                <span className="text-terra-slate block text-[11px]">Grid Discretization</span>
                <span className="text-terra-ivory font-semibold">{cellSize}m cells (~{((cellSize * cellSize) / 10000).toFixed(2)} ha)</span>
              </div>
              <div className="p-3.5 rounded-xl bg-terra-deep/70 border border-terra-border/40 space-y-1">
                <span className="text-terra-slate block text-[11px]">Max Slope Threshold</span>
                <span className="text-terra-ivory font-semibold">{maxSlope}° (Exclusion rule)</span>
              </div>
              <div className="p-3.5 rounded-xl bg-terra-deep/70 border border-terra-border/40 space-y-1">
                <span className="text-terra-slate block text-[11px]">Normalized Weights</span>
                <span className="text-terra-ivory font-semibold">
                  Need: {wNeed} | Gain: {wGain} | Area: {wArea} | Conf: {wConf}
                </span>
              </div>
              <div className="p-3.5 rounded-xl bg-terra-deep/70 border border-terra-border/40 space-y-1">
                <span className="text-terra-slate block text-[11px]">Planting Budget Allocation</span>
                <span className="text-terra-ivory font-semibold">₹{totalBudget.toLocaleString()} INR</span>
              </div>
            </div>

            {errorMessage && (
              <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            <div className="pt-2">
              <button
                onClick={handleExecute}
                disabled={isRunning}
                className="w-full py-3.5 rounded-xl bg-terra-mint hover:bg-terra-mint/90 disabled:opacity-50 text-terra-deep font-bold text-sm transition shadow-xl shadow-terra-mint/10 flex items-center justify-center gap-2 cursor-pointer"
              >
                {isRunning ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Executing Zonal Statistics & Ranking Algorithm...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-terra-deep" />
                    <span>Execute Multi-Criteria Prioritization Run</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </TransitionPanel>
      </div>

      {/* Wizard Footer Controls */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setCurrentStep((prev) => Math.max(0, prev - 1))}
          disabled={currentStep === 0 || isRunning}
          className="px-4 py-2 rounded-xl bg-terra-forest/60 border border-terra-border/40 text-xs font-semibold text-terra-muted hover:text-terra-ivory disabled:opacity-40 flex items-center gap-1.5 cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Previous Step</span>
        </button>

        {currentStep < steps.length - 1 && (
          <button
            onClick={() => setCurrentStep((prev) => Math.min(steps.length - 1, prev + 1))}
            className="px-4 py-2 rounded-xl bg-terra-forest hover:bg-terra-forest/80 text-xs font-semibold text-terra-ivory flex items-center gap-1.5 cursor-pointer border border-terra-border/50"
          >
            <span>Next Step</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
};
