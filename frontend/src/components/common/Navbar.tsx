import React, { useState, useMemo, useRef, useEffect } from 'react';
import type { ProjectMetadata, SystemHealth } from '../../api/types';
import type { ViewTab } from './Sidebar';
import {
  Search,
  Plus,
  Sparkles,
  RefreshCw,
  Folder,
  ChevronDown,
  Menu,
  X,
  Compass,
  PlayCircle,
  BookOpen,
  BarChart3,
  Sliders,
  FileText,
  Settings,
  Database,
  Home,
  Shield,
  ArrowRight,
} from 'lucide-react';

interface NavbarProps {
  projects: ProjectMetadata[];
  selectedProjectId: string | null;
  onSelectProject: (id: string) => void;
  onOpenCreateModal: () => void;
  health: SystemHealth | null;
  onRetryHealth?: () => void;
  onSearchSelect?: (query: string) => void;
  currentTab?: ViewTab;
  onTabChange?: (tab: ViewTab) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  projects,
  selectedProjectId,
  onSelectProject,
  onOpenCreateModal,
  health,
  onRetryHealth,
  onSearchSelect,
  currentTab = 'overview',
  onTabChange,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchFocused, setIsSearchFocused] = useState(false);
  const [isToolsOpen, setIsToolsOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const toolsRef = useRef<HTMLDivElement>(null);

  // Close tools dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (toolsRef.current && !toolsRef.current.contains(event.target as Node)) {
        setIsToolsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const isHealthy = health?.status === 'healthy' || health?.status === 'ok';
  const activeProj = projects.find((p) => p.id === selectedProjectId) || null;

  // Search suggestions
  const searchSuggestions = useMemo(() => {
    if (!searchQuery.trim()) return [];
    const q = searchQuery.toLowerCase();
    const suggestions: Array<{ label: string; type: 'project' | 'preset' | 'tab'; id: string }> = [];

    // Navigation shortcuts
    const navItems: Array<{ label: string; tab: ViewTab }> = [
      { label: 'Map Explorer', tab: 'map' },
      { label: 'Analysis Wizard', tab: 'wizard' },
      { label: 'Results & Rankings', tab: 'results' },
      { label: 'Case Studies Library', tab: 'case-studies' },
      { label: 'Geotechnical Studio', tab: 'geotech' },
      { label: 'Reports & Audit', tab: 'reports' },
      { label: 'Projects & Workspaces', tab: 'projects' },
      { label: 'System Settings', tab: 'settings' },
    ];

    for (const nav of navItems) {
      if (nav.label.toLowerCase().includes(q)) {
        suggestions.push({ label: nav.label, type: 'tab', id: nav.tab });
      }
    }

    // Projects
    for (const p of projects) {
      if (p.name.toLowerCase().includes(q) || p.id.toLowerCase().includes(q)) {
        suggestions.push({ label: p.name, type: 'project', id: p.id });
      }
    }

    // Presets
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

    return suggestions.slice(0, 6);
  }, [searchQuery, projects]);

  const handleSuggestionClick = (item: { label: string; type: string; id: string }) => {
    if (item.type === 'tab' && onTabChange) {
      onTabChange(item.id as ViewTab);
    } else if (item.type === 'project' || item.type === 'preset') {
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

  const primaryTabs: Array<{ id: ViewTab; label: string; icon: React.FC<{ className?: string }> }> = [
    { id: 'overview', label: 'Overview', icon: Home },
    { id: 'map', label: 'Map Explorer', icon: Compass },
    { id: 'wizard', label: 'Analysis Wizard', icon: PlayCircle },
    { id: 'case-studies', label: 'Case Studies', icon: BookOpen },
    { id: 'results', label: 'Results', icon: BarChart3 },
  ];

  const secondaryTabs: Array<{ id: ViewTab; label: string; desc: string; icon: React.FC<{ className?: string }> }> = [
    { id: 'geotech', label: 'Geotechnical Studio', desc: 'Slope stability & root mechanics', icon: Sliders },
    { id: 'reports', label: 'Reports & Exports', desc: 'Audit packages & spatial downloads', icon: FileText },
    { id: 'projects', label: 'Projects & Data', desc: 'Workspaces & layer library', icon: Database },
    { id: 'settings', label: 'Settings', desc: 'Environment & calibration', icon: Settings },
  ];

  const isSecondaryActive = secondaryTabs.some((t) => t.id === currentTab);

  return (
    <header className="relative z-40 bg-[#071c17]/95 backdrop-blur-md border-b border-white/10 text-white px-4 sm:px-6 py-3 transition-colors">
      <div className="max-w-[1680px] mx-auto flex items-center justify-between gap-4">
        {/* Left Side: Brand & Horizontal Nav Links */}
        <div className="flex items-center gap-6 lg:gap-8">
          {/* Brand Wordmark */}
          <button
            onClick={() => onTabChange?.('overview')}
            className="flex items-center gap-3 text-left group cursor-pointer"
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-700 flex items-center justify-center text-white shadow-md shadow-emerald-950/40 border border-emerald-400/30">
              <Shield className="w-5 h-5 text-emerald-100 group-hover:scale-105 transition-transform" />
            </div>
            <div>
              <span className="font-display font-bold text-base sm:text-lg tracking-tight text-white block leading-tight">
                TerraShield <span className="text-emerald-400 font-medium">AI</span>
              </span>
              <span className="text-[9.5px] font-mono tracking-widest text-emerald-300/80 uppercase block">
                GEOSPATIAL INTELLIGENCE
              </span>
            </div>
          </button>

          {/* Primary Navigation Links (Desktop) */}
          <nav className="hidden xl:flex items-center gap-1.5" aria-label="Primary Navigation">
            {primaryTabs.map((tab) => {
              const isActive = currentTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => onTabChange?.(tab.id)}
                  className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all cursor-pointer flex items-center gap-1.5 ${
                    isActive
                      ? 'bg-white/15 text-white font-semibold border border-white/20 shadow-xs'
                      : 'text-emerald-100/75 hover:text-white hover:bg-white/10'
                  }`}
                >
                  <tab.icon className="w-3.5 h-3.5 text-emerald-300" />
                  <span>{tab.label}</span>
                </button>
              );
            })}

            {/* Secondary Tools Dropdown */}
            <div className="relative" ref={toolsRef}>
              <button
                onClick={() => setIsToolsOpen(!isToolsOpen)}
                className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all cursor-pointer flex items-center gap-1.5 ${
                  isSecondaryActive || isToolsOpen
                    ? 'bg-white/15 text-white font-semibold border border-white/20 shadow-xs'
                    : 'text-emerald-100/75 hover:text-white hover:bg-white/10'
                }`}
              >
                <span>Modules</span>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isToolsOpen ? 'rotate-180' : ''}`} />
              </button>

              {isToolsOpen && (
                <div className="absolute top-full left-0 mt-2 w-64 rounded-2xl bg-[#09221c] border border-white/15 shadow-2xl p-2 z-50 animate-fade-in text-white">
                  <div className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider text-emerald-400 font-semibold border-b border-white/10">
                    Scientific &amp; System Modules
                  </div>
                  <div className="py-1 space-y-1">
                    {secondaryTabs.map((t) => {
                      const isActive = currentTab === t.id;
                      return (
                        <button
                          key={t.id}
                          onClick={() => {
                            onTabChange?.(t.id);
                            setIsToolsOpen(false);
                          }}
                          className={`w-full text-left p-2.5 rounded-xl transition cursor-pointer flex items-start gap-2.5 ${
                            isActive
                              ? 'bg-emerald-600/30 text-white border border-emerald-400/30'
                              : 'text-slate-200 hover:bg-white/10 hover:text-white'
                          }`}
                        >
                          <t.icon className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                          <div>
                            <div className="text-xs font-semibold">{t.label}</div>
                            <div className="text-[11px] text-emerald-200/60 leading-tight">{t.desc}</div>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </nav>
        </div>

        {/* Center: Universal Quick Search (Desktop) */}
        <div className="hidden lg:block relative max-w-xs xl:max-w-sm w-full mx-2">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/15 text-xs text-white focus-within:bg-white/20 focus-within:border-emerald-400 transition">
            <Search className="w-3.5 h-3.5 text-emerald-300/80 shrink-0" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setIsSearchFocused(true)}
              onBlur={() => setTimeout(() => setIsSearchFocused(false), 200)}
              placeholder="Search study area, module, or basin..."
              aria-label="Search study areas and modules"
              className="bg-transparent text-white placeholder-emerald-200/50 text-xs focus:outline-none w-full"
            />
          </div>

          {/* Autocomplete Dropdown */}
          {isSearchFocused && searchSuggestions.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-2 rounded-2xl bg-[#09221c] border border-white/15 shadow-2xl p-2 z-50 text-white">
              <div className="px-2.5 py-1 text-[10px] font-mono uppercase text-emerald-400 font-bold">
                Matching Areas &amp; Modules
              </div>
              {searchSuggestions.map((s, idx) => (
                <button
                  key={idx}
                  onMouseDown={() => handleSuggestionClick(s)}
                  className="w-full text-left px-3 py-2 rounded-xl text-xs hover:bg-white/10 text-slate-100 flex items-center justify-between transition cursor-pointer"
                >
                  <span className="truncate">{s.label}</span>
                  <span className="text-[9.5px] font-mono uppercase px-2 py-0.5 rounded bg-white/10 text-emerald-300 border border-white/10">
                    {s.type}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right Side: Workspace Project Dropdown + Engine Status + Primary CTA */}
        <div className="flex items-center gap-2.5 sm:gap-3 shrink-0">
          {/* Active Workspace Selector */}
          <div
            title={activeProj ? `Active Workspace: ${activeProj.name}` : 'Select Workspace'}
            className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/15 text-xs text-emerald-100"
          >
            <Folder className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <select
              value={selectedProjectId || ''}
              onChange={(e) => onSelectProject(e.target.value)}
              aria-label="Select active project workspace"
              className="bg-transparent text-emerald-100 font-medium text-xs focus:outline-none cursor-pointer max-w-[130px] sm:max-w-[170px] truncate"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id} className="bg-[#09221c] text-white">
                  {p.name} {p.id === 'wayanad_pilot' ? '(Demo)' : ''}
                </option>
              ))}
              {projects.length === 0 && (
                <option value="" className="bg-[#09221c] text-slate-400">
                  No Projects Found
                </option>
              )}
            </select>
          </div>

          {/* New Project Button */}
          <button
            onClick={onOpenCreateModal}
            className="p-1.5 sm:px-2.5 sm:py-1.5 rounded-full bg-white/10 hover:bg-white/20 border border-white/15 text-emerald-200 text-xs font-medium transition flex items-center gap-1 cursor-pointer"
            title="Create New Project Workspace"
          >
            <Plus className="w-3.5 h-3.5 text-emerald-300" />
            <span className="hidden sm:inline">New Area</span>
          </button>

          {/* Engine Status indicator */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/15 text-[11px] font-mono">
            <span
              className={`w-2 h-2 rounded-full ${
                isHealthy
                  ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)] animate-pulse'
                  : 'bg-amber-400'
              }`}
            />
            <span className="text-emerald-100 font-medium">
              {isHealthy ? 'Engine Online' : 'Engine Offline'}
            </span>
            {!isHealthy && onRetryHealth && (
              <button
                onClick={onRetryHealth}
                className="p-0.5 hover:text-emerald-300 transition"
                title="Retry Health Check"
              >
                <RefreshCw className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Primary Action Button (Reference Design Inspired Pill Button) */}
          <button
            onClick={() => onTabChange?.('wizard')}
            className="px-4 sm:px-5 py-2 rounded-full bg-white text-[#0a2e24] hover:bg-emerald-50 text-xs font-bold transition shadow-md flex items-center gap-1.5 cursor-pointer group"
          >
            <Sparkles className="w-3.5 h-3.5 text-emerald-700" />
            <span>Analyse a Site</span>
            <ArrowRight className="w-3 h-3 text-emerald-800 group-hover:translate-x-0.5 transition-transform" />
          </button>

          {/* Mobile Hamburger Menu Toggle */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="xl:hidden p-2 rounded-xl bg-white/10 text-emerald-200 hover:text-white hover:bg-white/20 transition cursor-pointer"
            aria-label="Toggle navigation menu"
          >
            {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Responsive Navigation Drawer */}
      {isMobileMenuOpen && (
        <div className="xl:hidden mt-3 pt-3 border-t border-white/15 animate-fade-in space-y-4">
          <div className="grid grid-cols-2 gap-2 text-xs">
            {primaryTabs.map((tab) => {
              const isActive = currentTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => {
                    onTabChange?.(tab.id);
                    setIsMobileMenuOpen(false);
                  }}
                  className={`p-2.5 rounded-xl transition text-left flex items-center gap-2 ${
                    isActive
                      ? 'bg-emerald-600 text-white font-semibold'
                      : 'bg-white/10 text-emerald-100 hover:bg-white/20'
                  }`}
                >
                  <tab.icon className="w-4 h-4 text-emerald-300" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          <div className="border-t border-white/10 pt-2">
            <div className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 font-semibold mb-2">
              Advanced Modules
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              {secondaryTabs.map((tab) => {
                const isActive = currentTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => {
                      onTabChange?.(tab.id);
                      setIsMobileMenuOpen(false);
                    }}
                    className={`p-2.5 rounded-xl transition text-left flex items-center gap-2 ${
                      isActive
                        ? 'bg-emerald-600 text-white font-semibold'
                        : 'bg-white/10 text-emerald-100 hover:bg-white/20'
                    }`}
                  >
                    <tab.icon className="w-4 h-4 text-emerald-300" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </header>
  );
};

export default Navbar;
