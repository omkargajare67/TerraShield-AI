import React, { useState } from 'react';
import {
  Home,
  BookOpen,
  PlayCircle,
  MapPin,
  BarChart3,
  FileText,
  Database,
  FolderArchive,
  Sliders,
  Shield,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

export type ViewTab =
  | 'overview'
  | 'case-studies'
  | 'wizard'
  | 'map'
  | 'results'
  | 'reports'
  | 'data-library'
  | 'projects'
  | 'settings'
  | 'geotech';

interface SidebarProps {
  currentTab: ViewTab;
  onTabChange: (tab: ViewTab) => void;
  className?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onTabChange, className = '' }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const navItems = [
    {
      id: 'overview' as ViewTab,
      label: 'Home',
      icon: Home,
      badge: 'Start',
      hint: 'Overview & status',
      iconColor: 'text-indigo-600',
      activeBg: 'bg-indigo-50 border-indigo-200 text-indigo-900',
      badgeColor: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    },
    {
      id: 'case-studies' as ViewTab,
      label: 'Case Studies',
      icon: BookOpen,
      badge: 'Curated',
      hint: 'Real-world disasters',
      iconColor: 'text-amber-600',
      activeBg: 'bg-amber-50 border-amber-200 text-amber-900',
      badgeColor: 'bg-amber-50 text-amber-700 border-amber-200',
    },
    {
      id: 'wizard' as ViewTab,
      label: 'New Analysis',
      icon: PlayCircle,
      badge: '5 Steps',
      hint: 'Guided step-by-step',
      iconColor: 'text-emerald-600',
      activeBg: 'bg-emerald-50 border-emerald-200 text-emerald-900',
      badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    },
    {
      id: 'map' as ViewTab,
      label: 'Map Explorer',
      icon: MapPin,
      badge: 'Map',
      hint: 'Geospatial intelligence',
      iconColor: 'text-sky-600',
      activeBg: 'bg-sky-50 border-sky-200 text-sky-900',
      badgeColor: 'bg-sky-50 text-sky-700 border-sky-200',
    },
    {
      id: 'results' as ViewTab,
      label: 'Results',
      icon: BarChart3,
      badge: 'Outputs',
      hint: 'Rankings & exports',
      iconColor: 'text-purple-600',
      activeBg: 'bg-purple-50 border-purple-200 text-purple-900',
      badgeColor: 'bg-purple-50 text-purple-700 border-purple-200',
    },
    {
      id: 'reports' as ViewTab,
      label: 'Reports',
      icon: FileText,
      badge: 'Audit',
      hint: 'Technical reports',
      iconColor: 'text-blue-600',
      activeBg: 'bg-blue-50 border-blue-200 text-blue-900',
      badgeColor: 'bg-blue-50 text-blue-700 border-blue-200',
    },
    {
      id: 'data-library' as ViewTab,
      label: 'Data Library',
      icon: Database,
      badge: 'STAC',
      hint: 'DEM & Sentinel-2',
      iconColor: 'text-teal-600',
      activeBg: 'bg-teal-50 border-teal-200 text-teal-900',
      badgeColor: 'bg-teal-50 text-teal-700 border-teal-200',
    },
    {
      id: 'projects' as ViewTab,
      label: 'My Projects',
      icon: FolderArchive,
      badge: 'Workspaces',
      hint: 'Project archives',
      iconColor: 'text-cyan-600',
      activeBg: 'bg-cyan-50 border-cyan-200 text-cyan-900',
      badgeColor: 'bg-cyan-50 text-cyan-700 border-cyan-200',
    },
    {
      id: 'settings' as ViewTab,
      label: 'Settings',
      icon: Sliders,
      badge: 'Config',
      hint: 'Geotechnical & API',
      iconColor: 'text-slate-600',
      activeBg: 'bg-slate-100 border-slate-300 text-slate-900',
      badgeColor: 'bg-slate-100 text-slate-700 border-slate-200',
    },
  ];

  return (
    <aside
      aria-label="Application navigation rail"
      className={`shrink-0 bg-white border-r border-slate-200 shadow-xs flex flex-col justify-between transition-all duration-300 relative z-20 ${
        isCollapsed ? 'w-20 p-3' : 'w-64 p-4'
      } ${className}`}
    >
      {/* Brand Header */}
      <div className="space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-200">
          <div className="flex items-center gap-3 overflow-hidden">
            {/* Brand Icon */}
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-700 flex items-center justify-center shrink-0 shadow-md shadow-emerald-500/20">
              <svg
                viewBox="0 0 32 32"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                className="w-6 h-6"
              >
                <path
                  d="M16 3L6 7V15C6 21.6 10.3 27.7 16 29C21.7 27.7 26 21.6 26 15V7L16 3Z"
                  fill="#064e3b"
                  stroke="#34d399"
                  strokeWidth="1.5"
                  strokeLinejoin="round"
                />
                <path
                  d="M16 9C13 13 12 18 16 23C20 18 19 13 16 9Z"
                  fill="#10b981"
                  opacity="0.9"
                />
                <path
                  d="M16 11V21"
                  stroke="#ecfdf5"
                  strokeWidth="1.2"
                  strokeLinecap="round"
                />
              </svg>
            </div>

            {!isCollapsed && (
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="font-display font-extrabold text-sm tracking-tight text-slate-900">
                    TerraShield
                  </span>
                  <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                    AI
                  </span>
                </div>
                <p className="text-[10px] text-slate-500 font-mono truncate">
                  Geospatial Intelligence
                </p>
              </div>
            )}
          </div>

          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 border border-transparent hover:border-slate-200 transition"
            title={isCollapsed ? 'Expand navigation' : 'Collapse navigation'}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Section Label */}
        {!isCollapsed && (
          <div className="px-2 text-[10px] font-mono uppercase tracking-wider text-slate-400 font-bold flex items-center justify-between">
            <span>Navigation</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          </div>
        )}

        {/* Navigation Items List */}
        <nav className="space-y-1" role="tablist">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;

            return (
              <button
                key={item.id}
                role="tab"
                aria-selected={isActive}
                onClick={() => onTabChange(item.id)}
                title={isCollapsed ? `${item.label} — ${item.hint}` : item.hint}
                className={`relative w-full flex items-center ${
                  isCollapsed ? 'justify-center p-2.5' : 'justify-between px-3 py-2.5'
                } rounded-xl text-xs transition-all duration-150 group text-left focus:outline-none cursor-pointer ${
                  isActive
                    ? `${item.activeBg} font-semibold shadow-2xs border`
                    : 'text-slate-700 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div
                    className={`p-1.5 rounded-lg transition-transform group-hover:scale-105 ${
                      isActive ? 'bg-white shadow-2xs' : 'bg-slate-100'
                    }`}
                  >
                    <Icon className={`w-4 h-4 shrink-0 ${item.iconColor}`} />
                  </div>
                  {!isCollapsed && (
                    <div className="min-w-0">
                      <span className="block leading-tight truncate font-medium text-slate-800">
                        {item.label}
                      </span>
                      <span className="text-[10px] text-slate-500 font-normal truncate block">
                        {item.hint}
                      </span>
                    </div>
                  )}
                </div>

                {!isCollapsed && (
                  <span
                    className={`text-[9px] px-1.5 py-0.5 rounded font-mono uppercase tracking-wider shrink-0 transition border ${item.badgeColor}`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Scientific Assurance Widget at Rail Bottom */}
      <div className="mt-4 pt-3 border-t border-slate-200">
        {!isCollapsed ? (
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 space-y-1.5 shadow-2xs">
            <div className="flex items-center gap-1.5 font-bold text-emerald-800 text-[11px]">
              <Shield className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>Scientific Integrity</span>
            </div>
            <p className="text-[10.5px] leading-relaxed text-slate-500">
              Infinite-slope limit equilibrium & Wu-Waldron root reinforcement mechanics.
            </p>
            <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 pt-1 border-t border-slate-200">
              <span>Status</span>
              <span className="text-emerald-700 font-semibold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                Calibrated
              </span>
            </div>
          </div>
        ) : (
          <div
            className="w-10 h-10 mx-auto rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center text-emerald-600"
            title="Infinite-slope limit equilibrium & Wu-Waldron root reinforcement mechanics"
          >
            <Shield className="w-4 h-4" />
          </div>
        )}
      </div>
    </aside>
  );
};

export default Sidebar;
