import React from 'react';
import type { ProjectMetadata, RecommendationRunResponse } from '../api/types';
import { TextEffect } from '../components/motion-primitives/TextEffect';
import { InView } from '../components/motion-primitives/InView';
import { MetricCard } from '../components/common/MetricCard';
import { ProvenanceBanner } from '../components/common/ProvenanceBanner';
import {
  Compass,
  ArrowRight,
  ShieldCheck,
  MapPin,
  Trees,
  Mountain,
  Layers,
  Sparkles,
} from 'lucide-react';

interface OverviewViewProps {
  activeProject: ProjectMetadata | null;
  latestRun: RecommendationRunResponse | null;
  onStartAnalysis: () => void;
  onOpenDataLibrary: () => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  activeProject,
  latestRun,
  onStartAnalysis,
  onOpenDataLibrary,
}) => {
  const bounds = activeProject?.bounds || { minx: 76.0, miny: 11.55, maxx: 76.1, maxy: 11.65 };
  const dlon = Math.abs(bounds.maxx - bounds.minx);
  const dlat = Math.abs(bounds.maxy - bounds.miny);
  const approxHa = Math.round(dlon * 111 * dlat * 111 * 100);
  const layerCount = Object.keys(activeProject?.layers || {}).length;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8 animate-fade-in">
      {/* Hero Banner with Haikei SVG Backdrop */}
      <div className="relative rounded-3xl overflow-hidden border border-terra-border/50 shadow-2xl bg-terra-forest/40 backdrop-blur-xl">
        {/* Haikei SVG Background Image */}
        <div
          className="absolute inset-0 bg-cover bg-bottom opacity-35 mix-blend-luminosity pointer-events-none"
          style={{ backgroundImage: `url('/backgrounds/hero-layered-peaks.svg')` }}
        />
        {/* Subtle Ambient Radial Lighting */}
        <div className="absolute inset-0 bg-gradient-to-r from-terra-deep/95 via-terra-deep/80 to-transparent pointer-events-none" />

        <div className="relative z-10 px-8 py-12 md:py-16 max-w-3xl space-y-5">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-terra-mint/15 border border-terra-mint/25 text-terra-mint text-xs font-semibold backdrop-blur-md">
            <Sparkles className="w-3.5 h-3.5 text-terra-mint" />
            <span>TERRASHIELD AI • ENVIRONMENTAL INTELLIGENCE</span>
          </div>

          <TextEffect
            as="h1"
            per="word"
            className="text-3xl sm:text-4xl md:text-5xl font-display font-semibold text-terra-ivory tracking-tight leading-[1.15]"
          >
            Understand Terrain. Prioritize Restoration.
          </TextEffect>

          <p className="text-terra-muted text-sm sm:text-base leading-relaxed max-w-xl">
            Explore terrain characteristics, model hillslope limit-equilibrium stability, and prioritize
            high-impact reforestation parcels using generalized geospatial and geotechnical intelligence.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              onClick={onStartAnalysis}
              className="px-5 py-3 rounded-xl bg-terra-mint hover:bg-terra-mint/90 text-terra-deep font-semibold text-xs transition shadow-lg shadow-terra-mint/10 flex items-center gap-2 group cursor-pointer"
            >
              <span>Start New Analysis</span>
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </button>
            <button
              onClick={onOpenDataLibrary}
              className="px-5 py-3 rounded-xl bg-terra-forest/80 hover:bg-terra-forest text-terra-ivory font-semibold text-xs border border-terra-border/50 transition flex items-center gap-2 cursor-pointer"
            >
              <Compass className="w-4 h-4 text-terra-mint" />
              <span>Workspace Data Library</span>
            </button>
          </div>
        </div>
      </div>

      <ProvenanceBanner />

      {/* Workspace KPI Row */}
      <InView direction="up" delay={0.1}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Study Area Extent"
            value={approxHa}
            suffix=" ha"
            icon={MapPin}
            color="emerald"
            subtext={activeProject?.name || 'Active Study Corridor'}
            badge={activeProject?.study_area_type || 'BBox'}
          />
          <MetricCard
            label="Candidate Parcels"
            value={latestRun?.total_parcels || (activeProject?.id === 'wayanad_pilot' ? 1369 : 5)}
            icon={Mountain}
            color="blue"
            subtext="Grid resolution 300m"
            badge="Ellipsoidal"
          />
          <MetricCard
            label="Eligible for Planting"
            value={latestRun?.eligible_count || (activeProject?.id === 'wayanad_pilot' ? 1369 : 3)}
            icon={Trees}
            color="emerald"
            subtext="Slope & Reserve Filter"
            badge="Candidate"
          />
          <MetricCard
            label="Data Layers Attached"
            value={layerCount}
            icon={Layers}
            color="amber"
            subtext="DEM, Slope, NDVI, Vectors"
            badge="Verified"
          />
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
                    {activeProject?.name || 'No Active Project'}
                  </h3>
                  <p className="text-xs text-terra-slate">
                    {activeProject?.description || 'Select or create a project in the navigation header.'}
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

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2 text-xs">
              <div className="p-3 rounded-xl bg-terra-deep/60 border border-terra-border/40">
                <span className="text-terra-slate block text-[11px]">Coordinate CRS</span>
                <span className="font-mono text-terra-ivory font-semibold">{activeProject?.native_crs || 'EPSG:4326'}</span>
              </div>
              <div className="p-3 rounded-xl bg-terra-deep/60 border border-terra-border/40">
                <span className="text-terra-slate block text-[11px]">Geotechnical Preset</span>
                <span className="text-terra-ivory font-semibold">
                  {activeProject?.geotechnical_parameters?.name || 'Tropical Monsoon Saprolite'}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-terra-deep/60 border border-terra-border/40">
                <span className="text-terra-slate block text-[11px]">Saved Scenarios</span>
                <span className="font-mono text-terra-ivory font-semibold">
                  {activeProject?.saved_runs?.length || 0} runs
                </span>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between text-xs text-terra-slate border-t border-terra-border/30 font-mono">
              <span>Bounding Coordinates: {bounds.minx.toFixed(2)}°E, {bounds.miny.toFixed(2)}°N to {bounds.maxx.toFixed(2)}°E, {bounds.maxy.toFixed(2)}°N</span>
              <button
                onClick={onStartAnalysis}
                className="font-semibold text-terra-mint hover:text-terra-ivory flex items-center gap-1 cursor-pointer font-sans"
              >
                <span>Configure Analysis</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Quick Workflow Action Card */}
          <div className="rounded-2xl p-6 bg-terra-forest/30 border border-terra-border/40 backdrop-blur-xl space-y-4 flex flex-col justify-between">
            <div className="space-y-3">
              <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-terra-mint">
                Decision Support Workflow
              </span>
              <h4 className="font-display font-semibold text-terra-ivory text-sm">Guided 5-Step Pipeline</h4>
              <ul className="text-xs text-terra-muted space-y-2">
                <li className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-terra-deep text-terra-mint flex items-center justify-center font-mono text-[10px] border border-terra-border/50">1</span>
                  <span>Select study area & boundaries</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-terra-deep text-terra-mint flex items-center justify-center font-mono text-[10px] border border-terra-border/50">2</span>
                  <span>Validate DEM & Sentinel-2 layers</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-terra-deep text-terra-mint flex items-center justify-center font-mono text-[10px] border border-terra-border/50">3</span>
                  <span>Tune soil cohesion & root tensile strength</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-terra-deep text-terra-mint flex items-center justify-center font-mono text-[10px] border border-terra-border/50">4</span>
                  <span>Execute multi-criteria ranking algorithm</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-terra-deep text-terra-mint flex items-center justify-center font-mono text-[10px] border border-terra-border/50">5</span>
                  <span>Inspect parcels & download GIS exports</span>
                </li>
              </ul>
            </div>

            <button
              onClick={onStartAnalysis}
              className="w-full py-2.5 rounded-xl bg-terra-mint text-terra-deep font-semibold text-xs hover:bg-terra-mint/90 transition shadow-md shadow-terra-mint/10 flex items-center justify-center gap-2 cursor-pointer"
            >
              <span>Launch Analysis Wizard</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </InView>
    </div>
  );
};
