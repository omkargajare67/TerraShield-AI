import React from 'react';
import { AlertCircle, HelpCircle } from 'lucide-react';

export const ProvenanceBanner: React.FC = () => {
  return (
    <div className="rounded-2xl p-4 bg-terra-forest/20 border border-terra-border/40 backdrop-blur-md">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-terra-mint/10 border border-terra-mint/20 text-terra-mint flex items-center justify-center shrink-0">
            <AlertCircle className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-terra-ivory font-mono uppercase tracking-wider">
                Geospatial & Geotechnical Transparency Notice
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-terra-mint/15 text-terra-mint border border-terra-mint/25">
                Audit Verified
              </span>
            </div>
            <p className="text-xs text-terra-slate mt-0.5">
              Terrain metrics are derived from genuine elevation rasters & Sentinel-2 bands. Stability factors reflect 1D infinite slope equilibrium and should be validated by field geologists.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-terra-slate shrink-0">
          <HelpCircle className="w-3.5 h-3.5 text-terra-mint" />
          <span>Non-commercial decision-support system</span>
        </div>
      </div>
    </div>
  );
};
