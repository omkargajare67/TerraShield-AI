import React, { useState } from 'react';
import { motion } from 'motion/react';
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
    },
    {
      id: 'case-studies' as ViewTab,
      label: 'Case Studies',
      icon: BookOpen,
      badge: 'Curated',
      hint: 'Real-world disasters',
    },
    {
      id: 'wizard' as ViewTab,
      label: 'New Analysis',
      icon: PlayCircle,
      badge: '5 Steps',
      hint: 'Guided step-by-step',
    },
    {
      id: 'map' as ViewTab,
      label: 'Map Explorer',
      icon: MapPin,
      badge: 'Map',
      hint: 'Geospatial intelligence',
    },
    {
      id: 'results' as ViewTab,
      label: 'Results',
      icon: BarChart3,
      badge: 'Outputs',
      hint: 'Rankings & exports',
    },
    {
      id: 'reports' as ViewTab,
      label: 'Reports',
      icon: FileText,
      badge: 'Audit',
      hint: 'Technical reports',
    },
    {
      id: 'data-library' as ViewTab,
      label: 'Data Library',
      icon: Database,
      badge: 'STAC',
      hint: 'DEM & Sentinel-2',
    },
    {
      id: 'projects' as ViewTab,
      label: 'My Projects',
      icon: FolderArchive,
      badge: 'Workspaces',
      hint: 'Project archives',
    },
    {
      id: 'settings' as ViewTab,
      label: 'Settings',
      icon: Sliders,
      badge: 'Config',
      hint: 'Geotechnical & API',
    },
  ];

  return (
    <aside
      aria-label="Application navigation rail"
      className={`shrink-0 glass-panel-deep border-r border-emerald-500/15 flex flex-col justify-between transition-all duration-300 relative z-20 ${
        isCollapsed ? 'w-20 p-3' : 'w-64 p-4'
      } ${className}`}
    >
      {/* Brand Header */}
      <div className="space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-emerald-500/15">
          <div className="flex items-center gap-3 overflow-hidden">
            {/* Custom Shield-and-Leaf Brand SVG Icon */}
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-emerald-500/25 via-emerald-600/30 to-teal-900/60 border border-emerald-400/40 flex items-center justify-center shrink-0 shadow-lg shadow-emerald-950/60 relative group">
              <svg
                viewBox="0 0 32 32"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                className="w-6 h-6 transform transition-transform group-hover:scale-110"
              >
                {/* Shield Contour */}
                <path
                  d="M16 3L6 7V15C6 21.6 10.3 27.7 16 29C21.7 27.7 26 21.6 26 15V7L16 3Z"
                  fill="url(#shieldGrad)"
                  stroke="#34d399"
                  strokeWidth="1.5"
                  strokeLinejoin="round"
                />
                {/* Embedded Botanical Leaf */}
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
                <path
                  d="M14 14.5L16 16"
                  stroke="#ecfdf5"
                  strokeWidth="1"
                  strokeLinecap="round"
                />
                <path
                  d="M18 17.5L16 19"
                  stroke="#ecfdf5"
                  strokeWidth="1"
                  strokeLinecap="round"
                />
                <defs>
                  <linearGradient id="shieldGrad" x1="6" y1="3" x2="26" y2="29" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#064e3b" />
                    <stop offset="1" stopColor="#022c22" />
                  </linearGradient>
                </defs>
              </svg>
              <div className="absolute inset-0 rounded-2xl bg-emerald-400/10 blur-sm -z-10 group-hover:bg-emerald-400/20 transition" />
            </div>

            {!isCollapsed && (
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="font-display font-extrabold text-sm tracking-tight text-white">
                    TerraShield
                  </span>
                  <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">
                    AI
                  </span>
                </div>
                <p className="text-[10px] text-slate-400 font-mono truncate">
                  Geospatial Intelligence
                </p>
              </div>
            )}
          </div>

          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1 rounded-lg text-slate-400 hover:text-emerald-300 hover:bg-emerald-950/40 border border-transparent hover:border-emerald-500/20 transition"
            title={isCollapsed ? 'Expand navigation' : 'Collapse navigation'}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Section Label */}
        {!isCollapsed && (
          <div className="px-2 text-[10px] font-mono uppercase tracking-wider text-emerald-400/70 font-semibold flex items-center justify-between">
            <span>Navigation</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
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
                } rounded-xl text-xs transition-all duration-200 group text-left focus:outline-none focus:ring-1 focus:ring-emerald-400 ${
                  isActive
                    ? 'text-white font-semibold'
                    : 'text-slate-300 hover:text-white hover:bg-emerald-900/25'
                }`}
              >
                {/* Active Indicator Backdrop */}
                {isActive && (
                  <motion.div
                    layoutId="activeRailPill"
                    className="absolute inset-0 bg-gradient-to-r from-emerald-600/35 via-emerald-700/20 to-teal-950/50 border border-emerald-400/50 rounded-xl shadow-lg shadow-emerald-950/60 -z-10"
                    transition={{ type: 'spring', stiffness: 380, damping: 32 }}
                  />
                )}

                <div className="flex items-center gap-3 min-w-0">
                  <Icon
                    className={`w-4 h-4 shrink-0 transition-transform group-hover:scale-110 ${
                      isActive ? 'text-emerald-300' : 'text-slate-400 group-hover:text-emerald-300'
                    }`}
                  />
                  {!isCollapsed && (
                    <div className="min-w-0">
                      <span className="block leading-tight truncate">{item.label}</span>
                      <span className="text-[10px] text-slate-400 font-normal truncate block">
                        {item.hint}
                      </span>
                    </div>
                  )}
                </div>

                {!isCollapsed && (
                  <span
                    className={`text-[9px] px-1.5 py-0.5 rounded font-mono uppercase tracking-wider shrink-0 transition ${
                      isActive
                        ? 'bg-emerald-500/25 text-emerald-300 border border-emerald-400/40'
                        : 'text-slate-400 bg-slate-800/40 group-hover:text-slate-200'
                    }`}
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
      <div className="mt-4 pt-3 border-t border-emerald-500/15">
        {!isCollapsed ? (
          <div className="p-3 rounded-xl bg-gradient-to-b from-emerald-950/50 to-teal-950/40 border border-emerald-500/20 text-xs text-slate-300 space-y-1.5 backdrop-blur-md">
            <div className="flex items-center gap-1.5 font-bold text-emerald-300 text-[11px]">
              <Shield className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>Scientific Integrity</span>
            </div>
            <p className="text-[10.5px] leading-relaxed text-slate-400">
              Infinite-slope limit equilibrium & Wu-Waldron root reinforcement mechanics.
            </p>
            <div className="flex items-center justify-between text-[10px] font-mono text-emerald-400/80 pt-1 border-t border-emerald-500/15">
              <span>Status</span>
              <span className="text-emerald-300 font-semibold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                Calibrated
              </span>
            </div>
          </div>
        ) : (
          <div
            className="w-10 h-10 mx-auto rounded-xl bg-emerald-950/50 border border-emerald-500/20 flex items-center justify-center text-emerald-400"
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
