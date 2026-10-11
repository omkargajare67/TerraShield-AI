import React from 'react';
import type { ProjectMetadata, SystemHealth } from '../../api/types';
import { Shield, Plus, Sparkles, AlertCircle } from 'lucide-react';

interface NavbarProps {
  projects: ProjectMetadata[];
  selectedProjectId: string | null;
  onSelectProject: (id: string) => void;
  onOpenCreateModal: () => void;
  health: SystemHealth | null;
}

export const Navbar: React.FC<NavbarProps> = ({
  projects,
  selectedProjectId,
  onSelectProject,
  onOpenCreateModal,
  health,
}) => {
  const isHealthy = health?.status === 'healthy' || health?.status === 'ok';

  return (
    <header className="h-16 px-6 border-b border-terra-border/40 bg-terra-forest/40 backdrop-blur-xl flex items-center justify-between z-30 sticky top-0">
      {/* Brand & Identity */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-terra-forest to-terra-mint flex items-center justify-center text-terra-deep shadow-md shadow-terra-mint/10 border border-terra-mint/30">
          <Shield className="w-5 h-5 fill-terra-deep" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-display font-bold text-base tracking-tight text-terra-ivory">
              TerraShield
            </span>
            <span className="text-[10px] font-mono tracking-widest font-semibold px-1.5 py-0.5 rounded bg-terra-mint/20 text-terra-mint uppercase border border-terra-mint/30">
              AI
            </span>
          </div>
          <p className="text-[10px] text-terra-slate font-mono -mt-0.5">
            Geospatial Environmental Intelligence
          </p>
        </div>
      </div>

      {/* Middle: Active Workspace Selector & Quick New Project */}
      <div className="flex items-center gap-3">
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-terra-deep/70 border border-terra-border/50 text-xs">
          <span className="text-[11px] text-terra-slate font-mono uppercase">Workspace:</span>
          <select
            value={selectedProjectId || ''}
            onChange={(e) => onSelectProject(e.target.value)}
            className="bg-transparent text-terra-ivory font-mono text-xs focus:outline-none cursor-pointer pr-1"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id} className="bg-terra-forest text-terra-ivory">
                {p.name} {p.id === 'wayanad_pilot' ? '(Pilot Catchment)' : ''}
              </option>
            ))}
            {projects.length === 0 && (
              <option value="" className="bg-terra-forest text-terra-slate">
                No Projects Loaded
              </option>
            )}
          </select>
        </div>

        <button
          onClick={onOpenCreateModal}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-terra-forest/80 hover:bg-terra-forest text-terra-mint text-xs font-semibold border border-terra-mint/30 transition shadow-sm"
        >
          <Plus className="w-3.5 h-3.5" />
          <span className="hidden md:inline">New Project</span>
        </button>
      </div>

      {/* Right Side: Health indicator and Version */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-terra-deep/60 border border-terra-border/40 text-[11px] font-mono">
          <span
            className={`w-2 h-2 rounded-full ${
              isHealthy ? 'bg-emerald-400 shadow-sm shadow-emerald-400 animate-pulse' : 'bg-amber-400'
            }`}
          />
          <span className="text-terra-muted">
            {isHealthy ? 'Backend Engine Online' : 'Connecting to API...'}
          </span>
          {health?.version && (
            <span className="text-terra-slate hidden lg:inline">v{health.version}</span>
          )}
        </div>

        {!isHealthy && health && (
          <span title="Backend offline" className="text-amber-400">
            <AlertCircle className="w-4 h-4" />
          </span>
        )}

        <div className="hidden lg:flex items-center gap-1 text-[11px] font-mono text-terra-slate">
          <Sparkles className="w-3.5 h-3.5 text-terra-mint" />
          <span>Scientific LE</span>
        </div>
      </div>
    </header>
  );
};
