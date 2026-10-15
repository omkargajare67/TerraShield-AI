import React from 'react';
import { motion } from 'motion/react';
import {
  Home,
  PlayCircle,
  MapPin,
  BarChart3,
  Sliders,
  FolderArchive,
  Info,
} from 'lucide-react';

export type ViewTab = 'overview' | 'wizard' | 'map' | 'results' | 'geotech' | 'projects';

interface SidebarProps {
  currentTab: ViewTab;
  onTabChange: (tab: ViewTab) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onTabChange }) => {
  const navItems = [
    {
      id: 'overview' as ViewTab,
      label: 'Home',
      icon: Home,
      badge: 'Start',
      hint: 'Overview & status',
    },
    {
      id: 'wizard' as ViewTab,
      label: 'New Analysis',
      icon: PlayCircle,
      badge: '5 Steps',
      hint: 'Guided step-by-step',
    },
    {
      id: 'results' as ViewTab,
      label: 'Results',
      icon: BarChart3,
      badge: 'Outputs',
      hint: 'Rankings & exports',
    },
    {
      id: 'map' as ViewTab,
      label: 'Map Explorer',
      icon: MapPin,
      badge: 'Map',
      hint: 'Interactive parcel view',
    },
    {
      id: 'projects' as ViewTab,
      label: 'My Projects',
      icon: FolderArchive,
      badge: 'Data',
      hint: 'Workspaces & datasets',
    },
    {
      id: 'geotech' as ViewTab,
      label: 'Slope Simulation',
      icon: Sliders,
      badge: 'Advanced',
      hint: 'Soil & root physics',
    },
  ];

  return (
    <aside
      aria-label="Application navigation"
      className="w-64 shrink-0 glass-panel-dark border-r border-terra-border/50 p-4 flex flex-col justify-between min-h-[calc(100vh-65px)]"
    >
      <div className="space-y-1.5">
        <div className="px-3 py-2 text-[11px] font-bold tracking-wider uppercase text-terra-slate font-mono">
          Main Workflow
        </div>

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
                title={item.hint}
                className={`relative w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs transition-all duration-200 group text-left focus:outline-none focus:ring-2 focus:ring-terra-mint/50 ${
                  isActive
                    ? 'text-terra-ivory font-semibold'
                    : 'text-terra-muted hover:text-terra-ivory hover:bg-terra-forest/40'
                }`}
              >
                {/* Active Animated Background Pill */}
                {isActive && (
                  <motion.div
                    layoutId="activeSidebarIndicator"
                    className="absolute inset-0 bg-gradient-to-r from-terra-forest to-terra-deep border border-terra-mint/30 rounded-xl shadow-md -z-10"
                    transition={{ type: 'spring', stiffness: 350, damping: 30 }}
                  />
                )}

                <div className="flex items-center gap-3">
                  <Icon
                    className={`w-4 h-4 transition-transform group-hover:scale-110 ${
                      isActive ? 'text-terra-mint' : 'text-terra-slate'
                    }`}
                  />
                  <div>
                    <span className="block leading-none">{item.label}</span>
                    <span className="text-[10px] text-terra-slate group-hover:text-terra-muted transition font-normal hidden lg:block mt-0.5">
                      {item.hint}
                    </span>
                  </div>
                </div>

                <span
                  className={`text-[10px] px-2 py-0.5 rounded-md font-mono transition ${
                    isActive
                      ? 'bg-terra-deep/90 text-terra-mint border border-terra-mint/30'
                      : 'text-terra-slate/80 group-hover:text-terra-muted bg-terra-deep/40'
                  }`}
                >
                  {item.badge}
                </span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Scientific Assurance Note */}
      <div className="p-3.5 rounded-2xl bg-terra-forest/40 border border-terra-border/50 text-xs text-terra-muted space-y-1.5 backdrop-blur-md">
        <div className="flex items-center gap-1.5 font-bold text-terra-mint text-[11px]">
          <Info className="w-3.5 h-3.5 text-terra-mint shrink-0" />
          <span>Scientific Assurance</span>
        </div>
        <p className="text-[11px] leading-relaxed text-terra-slate">
          Slope stability calculations use standard infinite-slope limit equilibrium equations and Wu-Waldron root reinforcement models.
        </p>
      </div>
    </aside>
  );
};

export default Sidebar;
