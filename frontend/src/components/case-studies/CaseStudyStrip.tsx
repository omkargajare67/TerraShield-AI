import React, { useState, useEffect } from 'react';
import type { CaseStudy } from '../../api/types';
import { api } from '../../api/client';
import {
  BookOpen,
  Calendar,
  MapPin,
  ArrowRight,
  Loader2,
} from 'lucide-react';

interface CaseStudyStripProps {
  onExploreCaseStudy: (caseId: string) => Promise<void>;
  activeCaseId?: string | null;
  className?: string;
}

export const CaseStudyStrip: React.FC<CaseStudyStripProps> = ({
  onExploreCaseStudy,
  activeCaseId,
  className = '',
}) => {
  const [caseStudies, setCaseStudies] = useState<CaseStudy[]>([]);
  const [loadingCaseId, setLoadingCaseId] = useState<string | null>(null);

  useEffect(() => {
    let isSubscribed = true;
    api
      .getCaseStudies()
      .then((data) => {
        if (isSubscribed) setCaseStudies(data || []);
      })
      .catch((err) => {
        console.warn('Could not fetch case studies strip:', err);
      });
    return () => {
      isSubscribed = false;
    };
  }, []);

  const handleLaunch = async (caseId: string) => {
    try {
      setLoadingCaseId(caseId);
      await onExploreCaseStudy(caseId);
    } catch (err) {
      console.error('Error launching case study:', err);
    } finally {
      setLoadingCaseId(null);
    }
  };

  if (caseStudies.length === 0) {
    return null;
  }

  return (
    <div className={`space-y-2.5 ${className}`}>
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-emerald-400" />
          <h4 className="text-xs font-bold font-display uppercase tracking-wider text-slate-200">
            Curated Real-World Case Studies
          </h4>
        </div>
        <span className="text-[10px] font-mono text-slate-400">
          Verified historical disasters & study AOIs
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {caseStudies.map((cs) => {
          const isActive = activeCaseId === cs.id;
          const isLoading = loadingCaseId === cs.id;
          const isReady = cs.readiness === 'READY_TO_ANALYZE';

          return (
            <div
              key={cs.id}
              className={`p-3 rounded-2xl glass-panel-deep border transition-all duration-200 flex flex-col justify-between group ${
                isActive
                  ? 'border-emerald-400/50 bg-[#092218]/90 ring-1 ring-emerald-400/40'
                  : 'border-emerald-500/15 hover:border-emerald-500/35 bg-[#081812]/80 hover:bg-[#0a2018]/90'
              }`}
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-1">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-emerald-400/90 font-semibold truncate">
                    <MapPin className="w-3 h-3 shrink-0" />
                    <span className="truncate">{cs.country || cs.state_province}</span>
                  </div>

                  <span
                    className={`text-[8.5px] font-mono px-1.5 py-0.5 rounded font-bold uppercase shrink-0 ${
                      isReady
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                    }`}
                  >
                    {isReady ? 'Ready' : 'Pending Data'}
                  </span>
                </div>

                <div>
                  <h5 className="font-bold text-xs text-white group-hover:text-emerald-300 transition line-clamp-2 leading-snug">
                    {cs.name}
                  </h5>
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-400 mt-1">
                    <Calendar className="w-3 h-3 text-slate-500 shrink-0" />
                    <span>{cs.event_date || 'Monsoon Season'}</span>
                  </div>
                </div>

                <p className="text-[10.5px] text-slate-400 line-clamp-2 leading-relaxed">
                  {cs.short_description}
                </p>
              </div>

              <div className="pt-2.5 mt-2.5 border-t border-emerald-500/15 flex items-center justify-between">
                <span className="text-[9px] font-mono text-slate-400 truncate max-w-[90px]">
                  {cs.disaster_type}
                </span>

                <button
                  onClick={() => handleLaunch(cs.id)}
                  disabled={isLoading}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10.5px] font-mono font-semibold transition cursor-pointer ${
                    isActive
                      ? 'bg-emerald-500/30 text-emerald-200 border border-emerald-400/40'
                      : 'bg-emerald-950/60 hover:bg-emerald-600 hover:text-white text-emerald-300 border border-emerald-500/25'
                  }`}
                >
                  {isLoading ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <>
                      <span>{isActive ? 'Active AOI' : 'Explore'}</span>
                      <ArrowRight className="w-2.5 h-2.5" />
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default CaseStudyStrip;
