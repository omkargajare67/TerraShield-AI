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
    emerald: 'bg-terra-mint/15 text-terra-mint border-terra-mint/25',
    amber: 'bg-amber-500/15 text-amber-300 border-amber-500/25',
    blue: 'bg-sky-500/15 text-sky-300 border-sky-500/25',
    slate: 'bg-terra-slate/15 text-terra-muted border-terra-slate/25',
  };

  return (
    <Spotlight className="rounded-2xl p-5 border border-terra-border/40 bg-terra-forest/30 backdrop-blur-xl transition-all duration-300 hover:border-terra-border/80">
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <span className="text-xs font-mono uppercase tracking-wider text-terra-slate">
            {label}
          </span>
          <div className="flex items-baseline gap-1 text-2xl font-bold font-mono text-terra-ivory">
            {prefix && <span className="text-terra-mint text-xl font-mono">{prefix}</span>}
            <AnimatedNumber value={value} decimals={decimals} />
            {suffix && <span className="text-sm font-sans text-terra-muted">{suffix}</span>}
          </div>
          {subtext && <p className="text-[11px] text-terra-slate">{subtext}</p>}
        </div>

        <div className="flex flex-col items-end gap-2">
          <div className={`p-2.5 rounded-xl border ${colorMap[color]}`}>
            <Icon className="w-4 h-4" />
          </div>
          {badge && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-terra-deep/70 text-terra-slate border border-terra-border/40">
              {badge}
            </span>
          )}
        </div>
      </div>
    </Spotlight>
  );
};
