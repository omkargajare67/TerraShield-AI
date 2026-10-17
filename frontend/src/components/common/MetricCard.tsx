import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { AnimatedNumber } from '../motion-primitives/AnimatedNumber';
import { Spotlight } from '../motion-primitives/Spotlight';

interface MetricCardProps {
  label: string;
  value: number;
  decimals?: number;
  suffix?: string;
  prefix?: string;
  icon: LucideIcon;
  badge?: string;
  subtext?: string;
  color?: 'emerald' | 'amber' | 'blue' | 'slate';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  decimals = 0,
  suffix = '',
  prefix = '',
  icon: Icon,
  badge,
  subtext,
  color = 'emerald',
}) => {
  const colorMap = {
    emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    amber: 'bg-amber-50 text-amber-700 border-amber-200',
    blue: 'bg-sky-50 text-sky-700 border-sky-200',
    slate: 'bg-slate-100 text-slate-700 border-slate-200',
  };

  const safeValue = typeof value === 'number' && !isNaN(value) ? value : 0;

  return (
    <Spotlight className="rounded-2xl p-5 border border-slate-200 bg-white shadow-xs transition-all duration-200 hover:shadow-md hover:border-slate-300">
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <span className="text-xs font-mono uppercase tracking-wider text-slate-500 font-semibold">
            {label}
          </span>
          <div className="flex items-baseline gap-1 text-2xl font-bold font-mono text-slate-900">
            {prefix && <span className="text-emerald-600 text-xl font-mono">{prefix}</span>}
            <AnimatedNumber value={safeValue} decimals={decimals} />
            {suffix && <span className="text-sm font-sans text-slate-500 font-normal">{suffix}</span>}
          </div>
          {subtext && <p className="text-[11px] text-slate-500">{subtext}</p>}
        </div>

        <div className="flex flex-col items-end gap-2">
          <div className={`p-2.5 rounded-xl border ${colorMap[color]}`}>
            <Icon className="w-4 h-4" />
          </div>
          {badge && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-50 text-slate-600 border border-slate-200">
              {badge}
            </span>
          )}
        </div>
      </div>
    </Spotlight>
  );
};
