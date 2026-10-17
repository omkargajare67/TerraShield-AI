import React, { useState, useMemo } from 'react';
import type { ProjectMetadata, SystemHealth } from '../../api/types';
import {
  Search,
  Plus,
  Sparkles,
  AlertCircle,
  RefreshCw,
  Folder,
  Layers,
  CloudOff,
} from 'lucide-react';

interface NavbarProps {
  projects: ProjectMetadata[];
  selectedProjectId: string | null;
  onSelectProject: (id: string) => void;
  onOpenCreateModal: () => void;
  health: SystemHealth | null;
  onRetryHealth?: () => void;
  onSearchSelect?: (query: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  projects,
  selectedProjectId,
  onSelectProject,
  onOpenCreateModal,
  health,
  onRetryHealth,
  onSearchSelect,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchFocused, setIsSearchFocused] = useState(false);

  const isHealthy = health?.status === 'healthy' || health?.status === 'ok';
  const hasDemo = projects.some((p) => p.id === 'wayanad_pilot');
  const activeProj = projects.find((p) => p.id === selectedProjectId) || null;

  // Search presets / quick suggestions
  const searchSuggestions = useMemo(() => {
    if (!searchQuery.trim()) return [];
    const q = searchQuery.toLowerCase();
    const suggestions: Array<{ label: string; type: 'project' | 'preset' | 'parcel'; id: string }> = [];

    // Check existing projects
    for (const p of projects) {
      if (p.name.toLowerCase().includes(q) || p.id.toLowerCase().includes(q)) {
        suggestions.push({ label: p.name, type: 'project', id: p.id });
      }
    }

    // Common geographic catchments
    const presets = [
      { name: 'Wayanad Meppadi (Kerala)', id: 'wayanad_pilot' },
      { name: 'Malin Disaster AOI (Maharashtra)', id: 'proj_case_malin_2014' },
      { name: 'Himachal Beas Basin (Mandi)', id: 'proj_case_himachal_2023' },
      { name: 'Kedarnath Catchment (Uttarakhand)', id: 'kedarnath_2013' },
      { name: 'Cascade Demonstration Basin', id: 'cascade_demo' },
    ];

    for (const pr of presets) {
      if (pr.name.toLowerCase().includes(q) && !suggestions.some((s) => s.id === pr.id)) {
        suggestions.push({ label: pr.name, type: 'preset', id: pr.id });
      }
    }

    return suggestions.slice(0, 5);
  }, [searchQuery, projects]);

  const handleSuggestionClick = (item: { label: string; type: string; id: string }) => {
    if (item.type === 'project' || item.type === 'preset') {
      const match = projects.find((p) => p.id === item.id);
      if (match) {
        onSelectProject(match.id);
      }
    }
    if (onSearchSelect) {
      onSearchSelect(item.label);
    }
    setSearchQuery('');
    setIsSearchFocused(false);
  };

  return (
    <header className="h-16 px-4 sm:px-6 border-b border-emerald-500/15 bg-gradient-to-r from-[#06120e]/95 via-[#091b15]/95 to-[#06120e]/95 backdrop-blur-2xl flex items-center justify-between z-30 sticky top-0 shadow-lg shadow-black/40">
      {/* Left: Study Area Context / Breadcrumb */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-950/40 border border-emerald-500/20 text-xs text-slate-300">
          <Layers className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
          <span className="text-[11px] text-slate-400 font-mono hidden md:inline">Workspace:</span>
          <span className="font-semibold text-emerald-300 truncate max-w-[140px] sm:max-w-[200px]">
            {activeProj?.name || 'No Project Active'}
          </span>
          {activeProj?.study_area_type && (
            <span className="text-[9.5px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-400/30 uppercase tracking-wider hidden lg:inline">
              {activeProj.study_area_type}
            </span>
          )}
        </div>
      </div>

      {/* Middle: Universal Search Bar & Active Project Selector */}
      <div className="flex items-center gap-2 sm:gap-3 flex-1 max-w-xl mx-4">
        {/* Search Input with Autocomplete */}
        <div className="relative flex-1">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#081812]/90 border border-emerald-500/20 text-xs focus-within:border-emerald-400/50 focus-within:ring-1 focus-within:ring-emerald-400/30 transition shadow-inner">
            <Search className="w-3.5 h-3.5 text-emerald-400/70 shrink-0" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setIsSearchFocused(true)}
              onBlur={() => setTimeout(() => setIsSearchFocused(false), 200)}
              placeholder="Search study area, case study, district..."
              aria-label="Search locations or projects"
              className="bg-transparent text-white placeholder-slate-500 font-sans text-xs focus:outline-none w-full"
            />
          </div>

          {/* Autocomplete Dropdown */}
          {isSearchFocused && searchSuggestions.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1.5 rounded-xl bg-[#091d16] border border-emerald-500/30 shadow-2xl p-1.5 z-50 backdrop-blur-xl">
              <div className="px-2 py-1 text-[10px] font-mono uppercase text-emerald-400/80 font-bold">
                Matching Areas & Projects
              </div>
              {searchSuggestions.map((s, idx) => (
                <button
                  key={idx}
                  onMouseDown={() => handleSuggestionClick(s)}
                  className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs hover:bg-emerald-800/30 text-slate-200 hover:text-white flex items-center justify-between transition cursor-pointer"
                >
                  <span className="truncate">{s.label}</span>
                  <span className="text-[9px] font-mono uppercase text-emerald-400/70 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-500/20">
                    {s.type}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Project Selector Dropdown */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#081812]/90 border border-emerald-500/20 text-xs shrink-0">
          <Folder className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
          <select
            value={selectedProjectId || ''}
            onChange={(e) => onSelectProject(e.target.value)}
            aria-label="Select active project workspace"
            className="bg-transparent text-slate-200 hover:text-white font-medium text-xs focus:outline-none cursor-pointer max-w-[150px] md:max-w-[190px] truncate"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id} className="bg-[#091a13] text-white">
                {p.name} {p.id === 'wayanad_pilot' ? '(Demo Catchment)' : ''}
              </option>
            ))}
            {projects.length === 0 && (
              <option value="" className="bg-[#091a13] text-slate-400">
                No Projects Found
              </option>
            )}
          </select>
        </div>

        {/* Quick Actions */}
        {hasDemo && selectedProjectId !== 'wayanad_pilot' && (
          <button
            onClick={() => onSelectProject('wayanad_pilot')}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 text-xs font-semibold border border-emerald-400/30 transition shadow-sm cursor-pointer"
            title="Load Wayanad Pilot demonstration project"
          >
            <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            <span>Load Demo Area</span>
          </button>
        )}

        <button
          onClick={onOpenCreateModal}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-500 hover:to-teal-600 text-white text-xs font-semibold border border-emerald-400/40 transition shadow-md shadow-emerald-950/60 shrink-0 cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" />
          <span className="hidden md:inline">New Project</span>
        </button>
      </div>

      {/* Right Side: Environmental Feeds & Engine Status */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Environmental Feeds: Real Disclosure (No Invented Data) */}
        <div className="hidden 2xl:flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-900/40 border border-slate-700/30 text-[11px] font-mono text-slate-400" title="Environmental sensor feeds (live telemetry) are not currently connected to this station.">
          <CloudOff className="w-3 h-3 text-slate-500" />
          <span>Telemetry: Feeds Offline</span>
        </div>

        {/* Engine Status indicator */}
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-[#081912] border border-emerald-500/25 text-[11px] font-mono">
          <span
            className={`w-2 h-2 rounded-full ${
              isHealthy
                ? 'bg-emerald-400 shadow-sm shadow-emerald-400 animate-pulse'
                : 'bg-amber-400'
            }`}
          />
          <span className="text-slate-300 hidden md:inline">
            {isHealthy ? 'Engine Online' : 'Connecting...'}
          </span>

          {!isHealthy && onRetryHealth && (
            <button
              onClick={onRetryHealth}
              title="Click to retry connecting to the backend server"
              className="text-emerald-300 hover:text-white ml-1 p-0.5"
            >
              <RefreshCw className="w-3 h-3" />
            </button>
          )}

          {health?.version && (
            <span className="text-slate-500 hidden xl:inline">v{health.version}</span>
          )}
        </div>

        {!isHealthy && health && (
          <span title="Backend service unreachable" className="text-amber-400">
            <AlertCircle className="w-4 h-4" />
          </span>
        )}
      </div>
    </header>
  );
};

export default Navbar;
