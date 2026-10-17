import React, { useState } from 'react';
import type { ProjectMetadata } from '../api/types';
import { API_BASE_URL } from '../api/client';
import {
  Sliders,
  Shield,
  CheckCircle2,
  Server,
  RefreshCw,
} from 'lucide-react';

interface SettingsViewProps {
  activeProject: ProjectMetadata | null;
  onRefreshProjects?: () => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  activeProject,
  onRefreshProjects,
}) => {
  const [targetFs, setTargetFs] = useState(1.3);
  const [cPrime, setCPrime] = useState(12.5);
  const [phiDeg, setPhiDeg] = useState(28.0);
  const [gammaKn, setGammaKn] = useState(18.5);
  const [depthM, setDepthM] = useState(2.0);
  const [isSaved, setIsSaved] = useState(false);

  const handleSave = () => {
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2500);
  };

  return (
    <div className="space-y-6 pb-12 animate-fade-in max-w-5xl mx-auto px-4 sm:px-6">
      {/* Header */}
      <div className="p-5 rounded-2xl glass-panel-deep border border-emerald-500/20 backdrop-blur-xl shadow-lg flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-emerald-950/60 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
            <Sliders className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-base font-display font-bold text-white tracking-tight">
              Platform & Geotechnical Settings
            </h2>
            <p className="text-xs text-slate-400">
              {activeProject ? `Active Workspace: ${activeProject.name} • ` : ''}
              Configure geotechnical scenario baselines, limit equilibrium criteria, and API connections.
            </p>
          </div>
        </div>

        {onRefreshProjects && (
          <button
            onClick={onRefreshProjects}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-950/60 hover:bg-emerald-900/40 text-emerald-300 border border-emerald-500/20 text-xs font-mono transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reload Presets</span>
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Geotechnical Calibration Parameters */}
        <div className="lg:col-span-2 space-y-4">
          <div className="p-5 rounded-2xl glass-panel-deep border border-emerald-500/20 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-emerald-500/15">
              <span className="text-xs font-bold text-white uppercase font-mono">
                Slope Mechanics Baseline Preset
              </span>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/25">
                Infinite Slope + Wu-Waldron
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium block">Target Factor of Safety (FS)</label>
                <input
                  type="number"
                  step="0.05"
                  value={targetFs}
                  onChange={(e) => setTargetFs(parseFloat(e.target.value) || 1.3)}
                  className="w-full px-3 py-2 rounded-xl bg-[#091a13] border border-emerald-500/20 text-white font-mono text-xs focus:outline-none focus:border-emerald-400"
                />
                <span className="text-[10px] text-slate-400 block font-mono">
                  Default: 1.30 standard engineering design threshold
                </span>
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium block">Effective Cohesion c' (kPa)</label>
                <input
                  type="number"
                  step="0.5"
                  value={cPrime}
                  onChange={(e) => setCPrime(parseFloat(e.target.value) || 12.5)}
                  className="w-full px-3 py-2 rounded-xl bg-[#091a13] border border-emerald-500/20 text-white font-mono text-xs focus:outline-none focus:border-emerald-400"
                />
                <span className="text-[10px] text-slate-400 block font-mono">
                  Baseline Tropical Monsoon Saprolite
                </span>
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium block">Internal Friction Angle φ' (deg)</label>
                <input
                  type="number"
                  step="0.5"
                  value={phiDeg}
                  onChange={(e) => setPhiDeg(parseFloat(e.target.value) || 28.0)}
                  className="w-full px-3 py-2 rounded-xl bg-[#091a13] border border-emerald-500/20 text-white font-mono text-xs focus:outline-none focus:border-emerald-400"
                />
                <span className="text-[10px] text-slate-400 block font-mono">
                  Standard sheared residual soils
                </span>
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium block">Saturated Unit Weight γ (kN/m³)</label>
                <input
                  type="number"
                  step="0.5"
                  value={gammaKn}
                  onChange={(e) => setGammaKn(parseFloat(e.target.value) || 18.5)}
                  className="w-full px-3 py-2 rounded-xl bg-[#091a13] border border-emerald-500/20 text-white font-mono text-xs focus:outline-none focus:border-emerald-400"
                />
                <span className="text-[10px] text-slate-400 block font-mono">
                  Monsoon saturated soil density
                </span>
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium block">Failure Plane Depth D (m)</label>
                <input
                  type="number"
                  step="0.2"
                  value={depthM}
                  onChange={(e) => setDepthM(parseFloat(e.target.value) || 2.0)}
                  className="w-full px-3 py-2 rounded-xl bg-[#091a13] border border-emerald-500/20 text-white font-mono text-xs focus:outline-none focus:border-emerald-400"
                />
                <span className="text-[10px] text-slate-400 block font-mono">
                  Critical slip surface depth
                </span>
              </div>
            </div>

            <div className="pt-3 border-t border-emerald-500/15 flex items-center justify-between">
              <span className="text-[11px] text-slate-400">
                Preset: Tropical Monsoon Saprolite (Wayanad Baseline)
              </span>
              <button
                onClick={handleSave}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-500 hover:to-teal-600 text-white text-xs font-semibold border border-emerald-400/30 transition cursor-pointer shadow-md"
              >
                {isSaved ? <CheckCircle2 className="w-3.5 h-3.5" /> : null}
                <span>{isSaved ? 'Settings Saved' : 'Update Baseline'}</span>
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: System Assurance & Backend API Details */}
        <div className="space-y-4">
          <div className="p-5 rounded-2xl glass-panel-deep border border-emerald-500/20 space-y-3">
            <div className="flex items-center gap-2 pb-2 border-b border-emerald-500/15">
              <Server className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-bold text-white uppercase font-mono">API Architecture</span>
            </div>

            <div className="space-y-2 text-xs font-mono">
              <div className="flex justify-between items-center text-slate-300">
                <span className="text-slate-400">API Gateway:</span>
                <span className="text-emerald-300 truncate max-w-[170px]">{API_BASE_URL}</span>
              </div>
              <div className="flex justify-between items-center text-slate-300">
                <span className="text-slate-400">Elevation Dataset:</span>
                <span className="text-white">NASA SRTM NASADEM (30m)</span>
              </div>
              <div className="flex justify-between items-center text-slate-300">
                <span className="text-slate-400">Optical Bands:</span>
                <span className="text-white">Sentinel-2 L2A (10m)</span>
              </div>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/40 border border-slate-700/30 text-xs text-slate-400 space-y-2">
            <div className="flex items-center gap-1.5 font-bold text-slate-300">
              <Shield className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>Scientific Disclosure</span>
            </div>
            <p className="text-[11px] leading-relaxed">
              TerraShield uses deterministic limit-equilibrium mechanics and Wu-Waldron root reinforcement models. Soil parameters are exploratory presets and must be verified by licensed geotechnical engineers.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsView;
