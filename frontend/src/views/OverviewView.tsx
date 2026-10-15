import React from 'react';
import type { ProjectMetadata, RecommendationRunResponse } from '../api/types';
import { TextEffect } from '../components/motion-primitives/TextEffect';
import { InView } from '../components/motion-primitives/InView';
import { MetricCard } from '../components/common/MetricCard';
import { ProvenanceBanner } from '../components/common/ProvenanceBanner';
import { HelpTooltip } from '../components/common/HelpTooltip';
import {
  ArrowRight,
  ShieldCheck,
  MapPin,
  Trees,
  Mountain,
  Layers,
  Sparkles,
  BarChart3,
  FolderPlus,
  Compass,
} from 'lucide-react';

interface OverviewViewProps {
  activeProject: ProjectMetadata | null;
  latestRun: RecommendationRunResponse | null;
  onStartAnalysis: () => void;
  onOpenDataLibrary: () => void;
  onSelectProject?: (id: string) => void;
  onOpenResults?: () => void;
  onOpenCreateModal?: () => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  activeProject,
  latestRun,
  onStartAnalysis,
  onOpenDataLibrary,
  onSelectProject,
  onOpenResults,
  onOpenCreateModal,
}) => {
  const bounds = activeProject?.bounds || { minx: 76.0, miny: 11.55, maxx: 76.1, maxy: 11.65 };
  const dlon = Math.abs(bounds.maxx - bounds.minx);
  const dlat = Math.abs(bounds.maxy - bounds.miny);
  const approxHa = Math.round(dlon * 111 * dlat * 111 * 100);
  const layerCount = Object.keys(activeProject?.layers || {}).length;
  const hasRuns = (activeProject?.saved_runs && activeProject.saved_runs.length > 0) || Boolean(latestRun);

  // If no project exists at all
  if (!activeProject) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-16 animate-fade-in text-center space-y-6">
        <div className="p-12 rounded-3xl bg-terra-forest/40 border border-terra-border/50 backdrop-blur-xl space-y-5 shadow-2xl">
          <div className="w-16 h-16 rounded-2xl bg-terra-mint/15 text-terra-mint border border-terra-mint/30 flex items-center justify-center mx-auto shadow-inner">
            <Sparkles className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-display font-semibold text-terra-ivory">
            Welcome to TerraShield AI
          </h2>
          <p className="text-terra-muted text-sm max-w-md mx-auto leading-relaxed">
            Understand your terrain and plan restoration better. Select a demonstration watershed or create a new workspace to begin.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3 pt-3">
            {onSelectProject && (
              <button
                onClick={() => onSelectProject('wayanad_pilot')}
                className="px-6 py-3 rounded-xl bg-terra-mint text-terra-deep font-semibold text-xs hover:bg-terra-mint/90 transition shadow-lg shadow-terra-mint/10 flex items-center gap-2"
              >
                <Sparkles className="w-4 h-4" />
                <span>Explore Demo Project (Wayanad)</span>
              </button>
            )}
            {onOpenCreateModal && (
              <button
                onClick={onOpenCreateModal}
                className="px-5 py-3 rounded-xl bg-terra-forest/80 text-terra-ivory font-semibold text-xs border border-terra-border/60 hover:bg-terra-forest transition flex items-center gap-2"
              >
                <FolderPlus className="w-4 h-4 text-terra-mint" />
                <span>Create New Project</span>
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8 animate-fade-in">
      {/* Hero Banner with Haikei SVG Backdrop */}
      <div className="relative rounded-3xl overflow-hidden border border-terra-border/50 shadow-2xl bg-terra-forest/40 backdrop-blur-xl">
        <div
          className="absolute inset-0 bg-cover bg-bottom opacity-35 mix-blend-luminosity pointer-events-none"
          style={{ backgroundImage: `url('/backgrounds/hero-layered-peaks.svg')` }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-terra-deep/95 via-terra-deep/80 to-transparent pointer-events-none" />

        <div className="relative z-10 px-6 sm:px-8 py-10 md:py-14 max-w-3xl space-y-4 sm:space-y-5">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-terra-mint/15 border border-terra-mint/25 text-terra-mint text-xs font-semibold backdrop-blur-md">
            <Sparkles className="w-3.5 h-3.5 text-terra-mint" />
            <span>TERRASHIELD AI • ENVIRONMENTAL DECISION SUPPORT</span>
          </div>

          <TextEffect
            as="h1"
            per="word"
            className="text-2xl sm:text-4xl md:text-5xl font-display font-semibold text-terra-ivory tracking-tight leading-[1.15]"
          >
            Understand Your Terrain. Plan Restoration Better.
          </TextEffect>

          <p className="text-terra-muted text-sm sm:text-base leading-relaxed max-w-xl">
            Analyze terrain and vegetation data, explore slope stability, and identify high-impact
            locations that may need further assessment.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              onClick={onStartAnalysis}
              className="px-5 py-3 rounded-xl bg-terra-mint hover:bg-terra-mint/90 text-terra-deep font-semibold text-xs transition shadow-lg shadow-terra-mint/10 flex items-center gap-2 group cursor-pointer"
            >
              <span>Start New Analysis</span>
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </button>

            {hasRuns && onOpenResults && (
              <button
                onClick={onOpenResults}
                className="px-5 py-3 rounded-xl bg-terra-forest/90 hover:bg-terra-forest text-terra-ivory font-semibold text-xs border border-terra-mint/30 transition flex items-center gap-2 cursor-pointer shadow-sm"
              >
                <BarChart3 className="w-4 h-4 text-terra-mint" />
                <span>View Latest Results</span>
              </button>
            )}

            {activeProject.id !== 'wayanad_pilot' && onSelectProject && (
              <button
                onClick={() => onSelectProject('wayanad_pilot')}
                className="px-5 py-3 rounded-xl bg-terra-forest/70 hover:bg-terra-forest text-terra-ivory font-semibold text-xs border border-terra-border/50 transition flex items-center gap-2 cursor-pointer"
              >
                <Sparkles className="w-4 h-4 text-terra-mint" />
                <span>Explore Demo Project</span>
              </button>
            )}

            <button
              onClick={onOpenDataLibrary}
              className="px-5 py-3 rounded-xl bg-terra-forest/50 hover:bg-terra-forest/80 text-terra-muted hover:text-terra-ivory font-semibold text-xs border border-terra-border/40 transition flex items-center gap-2 cursor-pointer"
            >
              <Compass className="w-4 h-4 text-terra-slate" />
              <span>Workspace Data</span>
            </button>
          </div>
        </div>
      </div>

      <ProvenanceBanner />

      {/* Honest Workspace Summary Cards */}
      <InView direction="up" delay={0.1}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Study Area Extent"
            value={approxHa}
            suffix=" ha"
            icon={MapPin}
            color="emerald"
            subtext={activeProject.name}
            badge="Boundary"
          />

          <MetricCard
            label="Data Layers Ready"
            value={layerCount}
            icon={Layers}
            color="amber"
            subtext="Elevation, Slope, NDVI"
            badge="Verified"
          />

          {latestRun ? (
            <>
              <MetricCard
                label="Evaluated Locations"
                value={latestRun.total_parcels}
                icon={Mountain}
                color="blue"
                subtext={`Grid resolution ${latestRun.cell_size_m || 300}m`}
                badge="Modeled"
              />
              <MetricCard
                label="Recommended for Planting"
                value={latestRun.eligible_count}
                icon={Trees}
                color="emerald"
                subtext="Passed stability & canopy rules"
                badge="Actionable"
              />
            </>
          ) : (
            <>
              <MetricCard
                label="Analysis Status"
                value={hasRuns ? 1 : 0}
                icon={Mountain}
                color="blue"
                subtext={hasRuns ? 'Prior run available' : 'Ready for first analysis'}
                badge={hasRuns ? 'Available' : 'Pending'}
              />
              <MetricCard
                label="Planting Candidates"
                value={hasRuns ? (activeProject.saved_runs?.[0]?.eligible_count || 0) : 0}
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
                    {activeProject.name}
                  </h3>
                  <p className="text-xs text-terra-slate">
                    {activeProject.description || 'Active environmental workspace for terrain modeling.'}
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
                  {activeProject.native_crs || 'EPSG:4326 (WGS 84)'}
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
                  {activeProject.geotechnical_parameters?.name || 'Tropical Monsoon Saprolite'}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-terra-deep/60 border border-terra-border/40">
                <span className="text-terra-slate block text-[11px] mb-1">Saved Analyses</span>
                <span className="font-mono text-terra-ivory font-semibold">
                  {activeProject.saved_runs?.length || 0} run{activeProject.saved_runs?.length === 1 ? '' : 's'}
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
                <span>Start 5-Step Analysis</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Guided 5-Step Workflow Card */}
          <div className="rounded-2xl p-6 bg-terra-forest/30 border border-terra-border/40 backdrop-blur-xl space-y-4 flex flex-col justify-between">
            <div className="space-y-3">
              <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-terra-mint">
                Simple 5-Step Workflow
              </span>
              <h4 className="font-display font-semibold text-terra-ivory text-sm">
                How TerraShield AI Works
              </h4>
              <ol className="text-xs text-terra-muted space-y-2.5">
                <li className="flex items-start gap-2.5">
                  <span className="w-5 h-5 rounded-full bg-terra-deep text-terra-mint flex items-center justify-center font-mono text-[10px] border border-terra-border/50 shrink-0 mt-0.5 font-bold">1</span>
                  <div>
                    <span className="font-medium text-terra-ivory block">Choose Your Area</span>
                    <span className="text-[11px] text-terra-slate">Confirm your study boundary or watershed.</span>
                  </div>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="w-5 h-5 rounded-full bg-terra-deep text-terra-mint flex items-center justify-center font-mono text-[10px] border border-terra-border/50 shrink-0 mt-0.5 font-bold">2</span>
                  <div>
                    <span className="font-medium text-terra-ivory block">Add Your Data</span>
                    <span className="text-[11px] text-terra-slate">Verify elevation (DEM) and vegetation (NDVI) layers.</span>
                  </div>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="w-5 h-5 rounded-full bg-terra-deep text-terra-mint flex items-center justify-center font-mono text-[10px] border border-terra-border/50 shrink-0 mt-0.5 font-bold">3</span>
                  <div>
                    <span className="font-medium text-terra-ivory block">Review Settings</span>
                    <span className="text-[11px] text-terra-slate">Select priority goal and soil parameters.</span>
                  </div>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="w-5 h-5 rounded-full bg-terra-deep text-terra-mint flex items-center justify-center font-mono text-[10px] border border-terra-border/50 shrink-0 mt-0.5 font-bold">4</span>
                  <div>
                    <span className="font-medium text-terra-ivory block">Run Analysis</span>
                    <span className="text-[11px] text-terra-slate">Execute physics modeling & multi-criteria ranking.</span>
                  </div>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="w-5 h-5 rounded-full bg-terra-deep text-terra-mint flex items-center justify-center font-mono text-[10px] border border-terra-border/50 shrink-0 mt-0.5 font-bold">5</span>
                  <div>
                    <span className="font-medium text-terra-ivory block">Explore Results</span>
                    <span className="text-[11px] text-terra-slate">Inspect parcels, map layers, and download GIS exports.</span>
                  </div>
                </li>
              </ol>
            </div>

            <button
              onClick={onStartAnalysis}
              className="w-full py-2.5 rounded-xl bg-terra-mint text-terra-deep font-semibold text-xs hover:bg-terra-mint/90 transition shadow-md shadow-terra-mint/10 flex items-center justify-center gap-2 cursor-pointer mt-2"
            >
              <span>Begin Analysis</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </InView>
    </div>
  );
};

export default OverviewView;
