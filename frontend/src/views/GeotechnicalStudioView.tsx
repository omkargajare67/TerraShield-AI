import React, { useState, useMemo } from 'react';
import {
  Layers,
  Sliders,
  RefreshCw,
} from 'lucide-react';
import { api } from '../api/client';
import type { ProjectMetadata } from '../api/types';
import { ProvenanceBanner } from '../components/common/ProvenanceBanner';
import { HelpTooltip } from '../components/common/HelpTooltip';

interface GeotechnicalStudioViewProps {
  activeProject: ProjectMetadata | null;
  onRunComplete?: () => void;
}

interface SoilPreset {
  name: string;
  cohesion: number; // kPa
  frictionAngle: number; // degrees
  unitWeight: number; // kN/m³
  depth: number; // m
  waterTableRatio: number; // m/z (0 to 1)
  rootCohesion: number; // kPa
  description: string;
}

const PRESETS: Record<string, SoilPreset> = {
  wayanad: {
    name: 'Wayanad Monsoon Saprolite',
    cohesion: 6.5,
    frictionAngle: 26.0,
    unitWeight: 18.2,
    depth: 1.8,
    waterTableRatio: 0.65,
    rootCohesion: 5.5,
    description: 'High rainfall saturated laterite/saprolite over crystalline gneiss bedrock.',
  },
  claySilt: {
    name: 'Colluvial Clay-Silt',
    cohesion: 9.0,
    frictionAngle: 21.0,
    unitWeight: 19.0,
    depth: 2.2,
    waterTableRatio: 0.5,
    rootCohesion: 4.0,
    description: 'Plastic clayey silt colluvium with low hydraulic conductivity.',
  },
  sandyLoam: {
    name: 'Residual Sandy Loam',
    cohesion: 3.5,
    frictionAngle: 32.0,
    unitWeight: 17.5,
    depth: 1.5,
    waterTableRatio: 0.4,
    rootCohesion: 6.0,
    description: 'Coarse weathered granitic soil with high internal friction.',
  },
  cohesionless: {
    name: 'Debris Flow Colluvium (Cohesionless)',
    cohesion: 1.0,
    frictionAngle: 34.0,
    unitWeight: 18.0,
    depth: 1.2,
    waterTableRatio: 0.8,
    rootCohesion: 4.5,
    description: 'Granular steep slope deposits prone to rapid shallow translational failure.',
  },
};

export const GeotechnicalStudioView: React.FC<GeotechnicalStudioViewProps> = ({
  activeProject,
  onRunComplete,
}) => {
  const [selectedPresetKey, setSelectedPresetKey] = useState<string>('wayanad');
  const [cohesion, setCohesion] = useState<number>(PRESETS.wayanad.cohesion);
  const [frictionAngle, setFrictionAngle] = useState<number>(PRESETS.wayanad.frictionAngle);
  const [unitWeight, setUnitWeight] = useState<number>(PRESETS.wayanad.unitWeight);
  const [depth, setDepth] = useState<number>(PRESETS.wayanad.depth);
  const [waterTableRatio, setWaterTableRatio] = useState<number>(PRESETS.wayanad.waterTableRatio);
  const [rootCohesion, setRootCohesion] = useState<number>(PRESETS.wayanad.rootCohesion);
  const [selectedSlope, setSelectedSlope] = useState<number>(30); // degrees for instantaneous calc
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [processResult, setProcessResult] = useState<string | null>(null);

  const applyPreset = (key: string) => {
    setSelectedPresetKey(key);
    const p = PRESETS[key];
    if (p) {
      setCohesion(p.cohesion);
      setFrictionAngle(p.frictionAngle);
      setUnitWeight(p.unitWeight);
      setDepth(p.depth);
      setWaterTableRatio(p.waterTableRatio);
      setRootCohesion(p.rootCohesion);
    }
  };

  // Infinite Slope Stability Calculator
  // FS = [ c' + c_root + (gamma - m * gamma_w) * z * cos^2(beta) * tan(phi') ] / [ gamma * z * sin(beta) * cos(beta) ]
  const calculateFS = (
    slopeDeg: number,
    cEffective: number,
    cRoot: number,
    phiDeg: number,
    gamma: number,
    z: number,
    mRatio: number
  ): number => {
    const beta = (slopeDeg * Math.PI) / 180;
    const phi = (phiDeg * Math.PI) / 180;
    const gammaW = 9.81; // kN/m³

    if (slopeDeg <= 0) return 99;

    const cosBeta = Math.cos(beta);
    const sinBeta = Math.sin(beta);

    const normalStress = (gamma - mRatio * gammaW) * z * Math.pow(cosBeta, 2);
    const resistingShear = cEffective + cRoot + Math.max(0, normalStress) * Math.tan(phi);
    const drivingShear = gamma * z * sinBeta * cosBeta;

    if (drivingShear <= 0) return 99;
    return Math.max(0, resistingShear / drivingShear);
  };

  // Instantaneous single-slope comparison
  const currentFS0 = useMemo(
    () => calculateFS(selectedSlope, cohesion, 0, frictionAngle, unitWeight, depth, waterTableRatio),
    [selectedSlope, cohesion, frictionAngle, unitWeight, depth, waterTableRatio]
  );

  const currentFSRoot = useMemo(
    () => calculateFS(selectedSlope, cohesion, rootCohesion, frictionAngle, unitWeight, depth, waterTableRatio),
    [selectedSlope, cohesion, rootCohesion, frictionAngle, unitWeight, depth, waterTableRatio]
  );

  const deltaFS = useMemo(() => currentFSRoot - currentFS0, [currentFSRoot, currentFS0]);

  // Curve data points for slope 10 deg to 50 deg
  const curvePoints = useMemo(() => {
    const points: Array<{ slope: number; fs0: number; fsRoot: number }> = [];
    for (let s = 10; s <= 50; s += 2) {
      points.push({
        slope: s,
        fs0: calculateFS(s, cohesion, 0, frictionAngle, unitWeight, depth, waterTableRatio),
        fsRoot: calculateFS(s, cohesion, rootCohesion, frictionAngle, unitWeight, depth, waterTableRatio),
      });
    }
    return points;
  }, [cohesion, frictionAngle, unitWeight, depth, waterTableRatio, rootCohesion]);

  const handleRunGeotechRaster = async () => {
    if (!activeProject) return;
    setIsProcessing(true);
    setProcessResult(null);
    try {
      const res = await api.processGeotechnical(activeProject.id);
      setProcessResult(res.message || 'Geotechnical processing finished successfully.');
      if (onRunComplete) onRunComplete();
    } catch (err: any) {
      setProcessResult(`Error: ${err.message || 'Processing failed'}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // SVG dimensions for the curve chart
  const width = 640;
  const height = 280;
  const padLeft = 45;
  const padBottom = 35;
  const padTop = 20;
  const padRight = 20;

  const maxFS = 3.0;
  const minFS = 0.0;
  const minSlope = 10;
  const maxSlope = 50;

  const mapX = (slope: number) => padLeft + ((slope - minSlope) / (maxSlope - minSlope)) * (width - padLeft - padRight);
  const mapY = (fs: number) => {
    const clamped = Math.min(maxFS, Math.max(minFS, fs));
    return height - padBottom - ((clamped - minFS) / (maxFS - minFS)) * (height - padTop - padBottom);
  };

  const polylineFS0 = curvePoints.map((p) => `${mapX(p.slope)},${mapY(p.fs0)}`).join(' ');
  const polylineFSRoot = curvePoints.map((p) => `${mapX(p.slope)},${mapY(p.fsRoot)}`).join(' ');

  const yFS1 = mapY(1.0);
  const yFS13 = mapY(1.3);

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-2 border-b border-terra-border/30">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono tracking-wider font-semibold uppercase bg-terra-mint/15 text-terra-mint border border-terra-mint/25">
              Geotechnical Limit Equilibrium Studio
            </span>
            <span className="text-xs text-terra-slate font-mono">
              Mohr-Coulomb + Wu-Waldron Root Reinforcement
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-display font-semibold text-terra-ivory">
            Slope Stability Simulation & Root Cohesion
          </h1>
          <p className="text-sm text-terra-muted mt-1">
            Simulate 1D infinite slope stability gains (&Delta;FS) across soil parameters, saturation ratios, and vegetation root architectures.
          </p>
        </div>

        {activeProject && (
          <button
            onClick={handleRunGeotechRaster}
            disabled={isProcessing}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-terra-mint text-terra-deep font-semibold text-xs hover:bg-terra-mint/90 transition shadow-lg shadow-terra-mint/10 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isProcessing ? 'animate-spin' : ''}`} />
            {isProcessing ? 'Computing Grid Rasters...' : 'Execute Project Raster Processing'}
          </button>
        )}
      </div>

      <ProvenanceBanner />

      {processResult && (
        <div className="p-4 rounded-xl bg-terra-forest/40 border border-terra-mint/30 text-xs text-terra-ivory font-mono">
          {processResult}
        </div>
      )}

      {/* Main Grid: Parameters vs Simulation Curve */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Parameter Controls (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Preset Selector */}
          <div className="p-5 rounded-2xl bg-terra-forest/30 border border-terra-border/40 backdrop-blur-xl">
            <h3 className="text-xs font-mono uppercase tracking-wider text-terra-mint font-semibold mb-3 flex items-center gap-2">
              <Sliders className="w-4 h-4" />
              Soil & Lithology Presets
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {Object.entries(PRESETS).map(([key, preset]) => (
                <button
                  key={key}
                  onClick={() => applyPreset(key)}
                  className={`p-3 rounded-xl text-left border text-xs transition ${
                    selectedPresetKey === key
                      ? 'bg-terra-forest border-terra-mint text-terra-ivory shadow-sm'
                      : 'bg-terra-deep/50 border-terra-border/30 text-terra-muted hover:border-terra-border/60 hover:text-terra-ivory'
                  }`}
                >
                  <span className="font-semibold block">{preset.name}</span>
                  <span className="text-[10px] text-terra-slate line-clamp-1 mt-0.5">
                    c'={preset.cohesion}kPa, &phi;'={preset.frictionAngle}&deg;
                  </span>
                </button>
              ))}
            </div>
            <p className="text-[11px] text-terra-slate mt-3 italic">
              {PRESETS[selectedPresetKey]?.description}
            </p>
          </div>

          {/* Sliders for Geotechnical Parameters */}
          <div className="p-5 rounded-2xl bg-terra-forest/30 border border-terra-border/40 backdrop-blur-xl space-y-5">
            <h3 className="text-xs font-mono uppercase tracking-wider text-terra-mint font-semibold mb-1 flex items-center gap-2">
              <Layers className="w-4 h-4" />
              Effective Soil Shear & Hydrology
            </h3>

            {/* Effective Cohesion c' */}
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-terra-muted flex items-center gap-1">
                  <span>Effective Cohesion (c')</span>
                  <HelpTooltip term="Cohesion (c')" text="Electrostatic and particle cementation bonding resisting shear along the sliding plane." />
                </span>
                <span className="font-mono text-terra-mint font-semibold">{cohesion.toFixed(1)} kPa</span>
              </div>
              <input
                type="range"
                min="0"
                max="25"
                step="0.5"
                value={cohesion}
                onChange={(e) => setCohesion(parseFloat(e.target.value))}
                className="w-full accent-terra-mint bg-terra-deep/80 h-1.5 rounded-lg appearance-none cursor-pointer"
              />
              <span className="text-[10px] text-terra-slate">Soil particle cementation & electrostatic bonding</span>
            </div>

            {/* Internal Friction Angle phi' */}
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-terra-muted flex items-center gap-1">
                  <span>Internal Friction Angle (&phi;')</span>
                  <HelpTooltip term="Friction Angle (φ')" text="Inter-granular friction resisting shear displacement between soil grains." />
                </span>
                <span className="font-mono text-terra-mint font-semibold">{frictionAngle.toFixed(1)}&deg;</span>
              </div>
              <input
                type="range"
                min="15"
                max="45"
                step="0.5"
                value={frictionAngle}
                onChange={(e) => setFrictionAngle(parseFloat(e.target.value))}
                className="w-full accent-terra-mint bg-terra-deep/80 h-1.5 rounded-lg appearance-none cursor-pointer"
              />
              <span className="text-[10px] text-terra-slate">Inter-granular frictional resistance</span>
            </div>

            {/* Unit Weight gamma */}
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-terra-muted flex items-center gap-1">
                  <span>Bulk Unit Weight (&gamma;)</span>
                  <HelpTooltip term="Unit Weight (γ)" text="Bulk density of the regolith column exerting gravitational driving force." />
                </span>
                <span className="font-mono text-terra-mint font-semibold">{unitWeight.toFixed(1)} kN/m&sup3;</span>
              </div>
              <input
                type="range"
                min="14"
                max="22"
                step="0.2"
                value={unitWeight}
                onChange={(e) => setUnitWeight(parseFloat(e.target.value))}
                className="w-full accent-terra-mint bg-terra-deep/80 h-1.5 rounded-lg appearance-none cursor-pointer"
              />
            </div>

            {/* Shear Plane Depth z */}
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-terra-muted flex items-center gap-1">
                  <span>Regolith Depth to Failure Plane (z)</span>
                  <HelpTooltip term="Soil Depth (z)" text="Distance from ground surface to the potential translational failure slip surface." />
                </span>
                <span className="font-mono text-terra-mint font-semibold">{depth.toFixed(1)} m</span>
              </div>
              <input
                type="range"
                min="0.5"
                max="5.0"
                step="0.1"
                value={depth}
                onChange={(e) => setDepth(parseFloat(e.target.value))}
                className="w-full accent-terra-mint bg-terra-deep/80 h-1.5 rounded-lg appearance-none cursor-pointer"
              />
            </div>

            {/* Water Table Ratio m */}
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-terra-muted flex items-center gap-1">
                  <span>Water Table Saturation Ratio (m = h_w / z)</span>
                  <HelpTooltip term="Saturation Ratio (m)" text="Fraction of soil column saturated with groundwater (0% = dry, 100% = perched water table at ground surface)." />
                </span>
                <span className="font-mono text-terra-mint font-semibold">{(waterTableRatio * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={waterTableRatio}
                onChange={(e) => setWaterTableRatio(parseFloat(e.target.value))}
                className="w-full accent-terra-mint bg-terra-deep/80 h-1.5 rounded-lg appearance-none cursor-pointer"
              />
              <span className="text-[10px] text-terra-slate">0% = dry regolith, 100% = fully saturated monsoon perched water</span>
            </div>

            {/* Root Additional Cohesion c_root */}
            <div className="pt-2 border-t border-terra-border/30">
              <div className="flex justify-between text-xs mb-1">
                <span className="text-terra-ivory font-semibold flex items-center gap-1">
                  <span>Bio-Engineered Root Cohesion (c_root)</span>
                  <HelpTooltip term="Root Cohesion (c_root)" text="Additional shear strength provided by vegetative root fibers crossing the potential slip surface." />
                </span>
                <span className="font-mono text-emerald-400 font-bold">{rootCohesion.toFixed(1)} kPa</span>
              </div>
              <input
                type="range"
                min="0"
                max="15"
                step="0.5"
                value={rootCohesion}
                onChange={(e) => setRootCohesion(parseFloat(e.target.value))}
                className="w-full accent-emerald-400 bg-terra-deep/80 h-1.5 rounded-lg appearance-none cursor-pointer"
              />
              <span className="text-[10px] text-terra-slate">Wu-Waldron tensile reinforcement via root area ratio (RAR)</span>
            </div>
          </div>
        </div>

        {/* Right Column: Interactive Stability Curve & Instantaneous Calculator (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Instantaneous Gauge & Comparison Card */}
          <div className="p-6 rounded-2xl bg-terra-forest/40 border border-terra-border/40 backdrop-blur-xl space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-terra-ivory">
                  Instantaneous Stability at Selected Gradient
                </h3>
                <p className="text-xs text-terra-slate">
                  Evaluate limit-equilibrium factor of safety at a specific slope angle.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs text-terra-muted">Slope Angle (&beta;):</span>
                <select
                  value={selectedSlope}
                  onChange={(e) => setSelectedSlope(parseInt(e.target.value))}
                  className="px-3 py-1.5 rounded-xl bg-terra-deep border border-terra-border/60 text-terra-mint font-mono font-bold text-xs"
                >
                  {[15, 20, 25, 30, 35, 40, 45].map((ang) => (
                    <option key={ang} value={ang}>
                      {ang}&deg;
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* FS Metric Split */}
            <div className="grid grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-terra-deep/60 border border-terra-border/40 text-center">
                <span className="text-[11px] text-terra-slate uppercase font-mono block mb-1">
                  Baseline FS (Unreinforced)
                </span>
                <span
                  className={`text-2xl font-mono font-bold ${
                    currentFS0 < 1.0 ? 'text-rose-400' : currentFS0 < 1.3 ? 'text-amber-400' : 'text-terra-ivory'
                  }`}
                >
                  {currentFS0.toFixed(2)}
                </span>
                <span className="text-[10px] block mt-1 text-terra-slate">
                  {currentFS0 < 1.0 ? 'Unstable (Failure)' : currentFS0 < 1.3 ? 'Marginal Stability' : 'Stable'}
                </span>
              </div>

              <div className="p-4 rounded-xl bg-terra-deep/60 border border-terra-mint/30 text-center">
                <span className="text-[11px] text-terra-mint uppercase font-mono block mb-1">
                  Reinforced FS (With Roots)
                </span>
                <span
                  className={`text-2xl font-mono font-bold ${
                    currentFSRoot < 1.0 ? 'text-rose-400' : currentFSRoot < 1.3 ? 'text-amber-400' : 'text-emerald-400'
                  }`}
                >
                  {currentFSRoot.toFixed(2)}
                </span>
                <span className="text-[10px] block mt-1 text-terra-mint font-semibold">
                  {currentFSRoot < 1.0 ? 'Still Vulnerable' : currentFSRoot < 1.3 ? 'Improved' : 'Secure (FS &gt; 1.3)'}
                </span>
              </div>

              <div className="p-4 rounded-xl bg-terra-mint/10 border border-terra-mint/30 text-center">
                <span className="text-[11px] text-emerald-300 uppercase font-mono block mb-1">
                  Net Stability Gain (&Delta;FS)
                </span>
                <span className="text-2xl font-mono font-bold text-emerald-300">
                  +{deltaFS.toFixed(2)}
                </span>
                <span className="text-[10px] block mt-1 text-emerald-400/80">
                  +{((deltaFS / (currentFS0 || 1)) * 100).toFixed(0)}% safety margin
                </span>
              </div>
            </div>
          </div>

          {/* SVG Stability Curve */}
          <div className="p-6 rounded-2xl bg-terra-forest/30 border border-terra-border/40 backdrop-blur-xl">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-xs font-mono uppercase tracking-wider text-terra-mint font-semibold">
                  Factor of Safety vs. Slope Angle (&beta;)
                </h3>
                <p className="text-xs text-terra-slate">
                  Green curve shows stabilization envelope from vegetative root reinforcement.
                </p>
              </div>

              <div className="flex items-center gap-4 text-[11px] font-mono">
                <span className="flex items-center gap-1.5 text-terra-slate">
                  <span className="w-3 h-0.5 bg-terra-slate inline-block" /> Baseline FS
                </span>
                <span className="flex items-center gap-1.5 text-emerald-400">
                  <span className="w-3 h-0.5 bg-emerald-400 inline-block" /> Bio-Reinforced FS
                </span>
              </div>
            </div>

            {/* Curve Visualizer Canvas */}
            <div className="w-full overflow-x-auto">
              <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto max-h-[300px]">
                {/* Background Grid Lines */}
                {[0.5, 1.0, 1.3, 1.5, 2.0, 2.5].map((val) => {
                  const y = mapY(val);
                  return (
                    <g key={val}>
                      <line
                        x1={padLeft}
                        y1={y}
                        x2={width - padRight}
                        y2={y}
                        stroke={val === 1.0 ? '#ef4444' : val === 1.3 ? '#f59e0b' : '#334155'}
                        strokeWidth={val === 1.0 || val === 1.3 ? 1.5 : 0.5}
                        strokeDasharray={val === 1.0 || val === 1.3 ? '4 3' : undefined}
                        opacity={val === 1.0 || val === 1.3 ? 0.7 : 0.3}
                      />
                      <text
                        x={padLeft - 6}
                        y={y + 3}
                        fill={val === 1.0 ? '#ef4444' : val === 1.3 ? '#f59e0b' : '#94a3b8'}
                        fontSize="9"
                        textAnchor="end"
                        fontFamily="monospace"
                      >
                        {val.toFixed(1)}
                      </text>
                    </g>
                  );
                })}

                {/* X Axis slope labels */}
                {[10, 20, 30, 40, 50].map((deg) => {
                  const x = mapX(deg);
                  return (
                    <g key={deg}>
                      <line
                        x1={x}
                        y1={padTop}
                        x2={x}
                        y2={height - padBottom}
                        stroke="#334155"
                        strokeWidth="0.5"
                        opacity="0.3"
                      />
                      <text
                        x={x}
                        y={height - padBottom + 16}
                        fill="#94a3b8"
                        fontSize="10"
                        textAnchor="middle"
                        fontFamily="monospace"
                      >
                        {deg}&deg;
                      </text>
                    </g>
                  );
                })}

                {/* Critical Threshold Labels */}
                <text
                  x={width - padRight - 5}
                  y={yFS1 - 4}
                  fill="#ef4444"
                  fontSize="8"
                  textAnchor="end"
                  fontFamily="monospace"
                  opacity="0.8"
                >
                  FS = 1.0 (Critical Equilibrium)
                </text>
                <text
                  x={width - padRight - 5}
                  y={yFS13 - 4}
                  fill="#f59e0b"
                  fontSize="8"
                  textAnchor="end"
                  fontFamily="monospace"
                  opacity="0.8"
                >
                  FS = 1.3 (Target Factor of Safety)
                </text>

                {/* Polylines */}
                <polyline
                  fill="none"
                  stroke="#94a3b8"
                  strokeWidth="2"
                  strokeDasharray="4 2"
                  points={polylineFS0}
                />
                <polyline
                  fill="none"
                  stroke="#34d399"
                  strokeWidth="3"
                  points={polylineFSRoot}
                />

                {/* Current Selected Slope Cursor Line */}
                <line
                  x1={mapX(selectedSlope)}
                  y1={padTop}
                  x2={mapX(selectedSlope)}
                  y2={height - padBottom}
                  stroke="#A7E6C5"
                  strokeWidth="1.5"
                />
                {/* Dots at intersection */}
                <circle
                  cx={mapX(selectedSlope)}
                  cy={mapY(currentFS0)}
                  r="4"
                  fill="#94a3b8"
                />
                <circle
                  cx={mapX(selectedSlope)}
                  cy={mapY(currentFSRoot)}
                  r="5"
                  fill="#34d399"
                />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
