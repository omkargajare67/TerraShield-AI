import React from 'react';
import { motion } from 'motion/react';
import {
  Compass,
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
    { id: 'overview' as ViewTab, label: 'Overview', icon: Compass, badge: 'Home' },
    { id: 'wizard' as ViewTab, label: 'New Analysis', icon: PlayCircle, badge: 'Workflow' },
    { id: 'map' as ViewTab, label: 'Map Explorer', icon: MapPin, badge: 'Spatial' },
    { id: 'results' as ViewTab, label: 'Results & Rankings', icon: BarChart3, badge: 'Outputs' },
    { id: 'geotech' as ViewTab, label: 'Geotechnical Studio', icon: Sliders, badge: 'Solver' },
    { id: 'projects' as ViewTab, label: 'Projects & Data', icon: FolderArchive, badge: 'Storage' },
  ];

  return (
    <aside className="w-64 shrink-0 glass-panel-dark border-r border-forest-800/80 p-4 flex flex-col justify-between min-h-[calc(100vh-65px)]">
      <div className="space-y-1.5">
        <div className="px-3 py-2 text-[11px] font-bold tracking-wider uppercase text-forest-400">
          Navigation Workspace
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`relative w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl font-medium text-xs transition-all duration-200 group text-left ${
                isActive
                  ? 'text-white font-semibold'
                  : 'text-forest-300 hover:text-white hover:bg-forest-800/40'
              }`}
            >
              {/* Active Animated Background Pill */}
              {isActive && (
                <motion.div
                  layoutId="activeSidebarIndicator"
                  className="absolute inset-0 bg-gradient-to-r from-forest-700 to-forest-600 border border-forest-400/30 rounded-xl shadow-md -z-10"
                  transition={{ type: 'spring', stiffness: 350, damping: 30 }}
                />
              )}
              <div className="flex items-center gap-3">
                <Icon
                  className={`w-4 h-4 transition-transform group-hover:scale-110 ${
                    isActive ? 'text-forest-200' : 'text-forest-400'
                  }`}
                />
                <span>{item.label}</span>
              </div>
              <span
                className={`text-[10px] px-2 py-0.5 rounded-md font-mono ${
                  isActive
                    ? 'bg-forest-900/80 text-forest-200'
                    : 'text-forest-400/80 group-hover:text-forest-300'
                }`}
              >
                {item.badge}
              </span>
            </button>
          );
        })}
      </div>

      {/* Scientific Integrity Footer Callout */}
      <div className="p-3.5 rounded-xl bg-forest-900/90 border border-forest-800 text-xs text-forest-300/80 space-y-1.5">
        <div className="flex items-center gap-1.5 font-bold text-forest-200 text-[11px]">
          <Info className="w-3.5 h-3.5 text-forest-400" />
          <span>Scientific Assurance</span>
        </div>
        <p className="text-[11px] leading-relaxed">
          Limit-equilibrium Factor of Safety and root-cohesion calculations adhere to standard soil mechanics formulation.
        </p>
      </div>
    </aside>
  );
};
