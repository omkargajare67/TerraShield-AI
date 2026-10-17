import React, { useState, useMemo } from 'react';
import type { ProjectMetadata, SystemHealth } from '../../api/types';
import {
  Search,
  Plus,
  Sparkles,
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
    <header className="h-16 px-4 sm:px-6 border-b border-slate-200 bg-white/95 backdrop-blur-xl flex items-center justify-between z-30 sticky top-0 shadow-xs">
      {/* Left: Study Area Context / Breadcrumb */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-slate-700 shadow-xs">
          <Layers className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
          <span className="text-[11px] text-slate-500 font-mono hidden md:inline">Workspace:</span>
          <span className="font-semibold text-emerald-900 truncate max-w-[140px] sm:max-w-[200px]">
            {activeProj?.name || 'No Project Active'}
          </span>
          {activeProj?.study_area_type && (
            <span className="text-[9.5px] font-mono px-1.5 py-0.5 rounded bg-white text-emerald-700 border border-emerald-200 font-bold uppercase tracking-wider hidden lg:inline shadow-2xs">
              {activeProj.study_area_type}
            </span>
          )}
        </div>
      </div>

      {/* Middle: Universal Search Bar & Active Project Selector */}
      <div className="flex items-center gap-2 sm:gap-3 flex-1 max-w-xl mx-4">
        {/* Search Input with Autocomplete */}
        <div className="relative flex-1">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-xs focus-within:bg-white focus-within:border-emerald-500 focus-within:ring-2 focus-within:ring-emerald-500/20 transition shadow-xs">
            <Search className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setIsSearchFocused(true)}
              onBlur={() => setTimeout(() => setIsSearchFocused(false), 200)}
              placeholder="Search study area, case study, district..."
              aria-label="Search locations or projects"
              className="bg-transparent text-slate-900 placeholder-slate-400 font-sans text-xs focus:outline-none w-full"
            />
          </div>

          {/* Autocomplete Dropdown */}
          {isSearchFocused && searchSuggestions.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1.5 rounded-xl bg-white border border-slate-200 shadow-2xl p-1.5 z-50">
              <div className="px-2 py-1 text-[10px] font-mono uppercase text-emerald-700 font-bold">
                Matching Areas & Projects
              </div>
              {searchSuggestions.map((s, idx) => (
                <button
                  key={idx}
                  onMouseDown={() => handleSuggestionClick(s)}
                  className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs hover:bg-slate-100 text-slate-800 hover:text-slate-900 flex items-center justify-between transition cursor-pointer"
                >
                  <span className="truncate">{s.label}</span>
                  <span className="text-[9px] font-mono uppercase text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                    {s.type}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Project Selector Dropdown */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-xs shrink-0 shadow-xs">
          <Folder className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
          <select
            value={selectedProjectId || ''}
            onChange={(e) => onSelectProject(e.target.value)}
            aria-label="Select active project workspace"
            className="bg-transparent text-slate-800 font-medium text-xs focus:outline-none cursor-pointer max-w-[150px] md:max-w-[190px] truncate"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id} className="bg-white text-slate-900">
                {p.name} {p.id === 'wayanad_pilot' ? '(Demo Catchment)' : ''}
              </option>
            ))}
            {projects.length === 0 && (
              <option value="" className="bg-white text-slate-400">
                No Projects Found
              </option>
            )}
          </select>
        </div>

        {/* Quick Actions */}
        {hasDemo && selectedProjectId !== 'wayanad_pilot' && (
          <button
            onClick={() => onSelectProject('wayanad_pilot')}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-xs font-semibold border border-emerald-200 transition shadow-xs cursor-pointer"
            title="Load Wayanad Pilot demonstration project"
          >
            <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
            <span>Load Demo Area</span>
          </button>
        )}

        <button
          onClick={onOpenCreateModal}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold border border-emerald-600 transition shadow-xs shrink-0 cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" />
          <span className="hidden md:inline">New Project</span>
        </button>
      </div>

      {/* Right Side: Environmental Feeds & Engine Status */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Environmental Feeds: Real Disclosure (No Invented Data) */}
        <div className="hidden 2xl:flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200 text-[11px] font-mono text-slate-500" title="Environmental sensor feeds (live telemetry) are not currently connected to this station.">
          <CloudOff className="w-3 h-3 text-slate-400" />
          <span>Telemetry: Feeds Offline</span>
        </div>

        {/* Engine Status indicator */}
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-50 border border-slate-200 text-[11px] font-mono">
          <span
            className={`w-2 h-2 rounded-full ${
              isHealthy
                ? 'bg-emerald-500 shadow-xs shadow-emerald-500 animate-pulse'
                : 'bg-amber-500'
            }`}
          />
          <span className="text-slate-700 font-medium hidden sm:inline">
            {isHealthy ? 'Engine Online' : 'Engine Offline'}
          </span>
          {health?.version && (
            <span className="text-slate-400 text-[10px] hidden md:inline">
              v{health.version}
            </span>
          )}
          {!isHealthy && onRetryHealth && (
            <button
              onClick={onRetryHealth}
              className="p-0.5 hover:text-emerald-600 transition"
              title="Retry Health Check"
            >
              <RefreshCw className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
    </header>
  );
};

export default Navbar;
