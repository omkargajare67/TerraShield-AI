import React, { useState, useEffect } from 'react';
import type { RecommendationRunResponse, ProjectMetadata } from '../api/types';
import { api } from '../api/client';
import {
  FileText,
  Download,
  FileCode,
  FileSpreadsheet,
  AlertCircle,
  Award,
  Compass,
} from 'lucide-react';

interface ReportsViewProps {
  activeProject: ProjectMetadata | null;
  latestRun: RecommendationRunResponse | null;
  onNavigateToWizard?: () => void;
  onNavigateToMap?: () => void;
}

export const ReportsView: React.FC<ReportsViewProps> = ({
  activeProject,
  latestRun,
  onNavigateToWizard,
  onNavigateToMap,
}) => {
  const [reportHtml, setReportHtml] = useState<string | null>(null);
  const [isLoadingReport, setIsLoadingReport] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);

  const reportArtifact = latestRun?.artifacts?.audit_report_html;

  useEffect(() => {
    if (!reportArtifact) {
      setReportHtml(null);
      return;
    }

    let isSubscribed = true;
    setIsLoadingReport(true);
    setReportError(null);

    api
      .getReportHtml(reportArtifact)
      .then((html) => {
        if (isSubscribed) {
          setReportHtml(html);
          setIsLoadingReport(false);
        }
      })
      .catch((err) => {
        if (isSubscribed) {
          setReportError(err.message || 'Could not load report content');
          setIsLoadingReport(false);
        }
      });

    return () => {
      isSubscribed = false;
    };
  }, [reportArtifact]);

  const handleDownload = (artifactId?: string) => {
    if (!artifactId) return;
    const url = api.getArtifactUrl(artifactId);
    window.open(url, '_blank');
  };

  return (
    <div className="space-y-6 pb-12 animate-fade-in max-w-6xl mx-auto px-4 sm:px-6">
      {/* Header */}
      <div className="p-5 rounded-2xl glass-panel-deep border border-emerald-500/20 backdrop-blur-xl shadow-lg flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-emerald-950/60 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
              <FileText className="w-4 h-4" />
            </div>
            <h2 className="text-lg font-display font-bold text-white tracking-tight">
              Audit & Technical Reports
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
              Export Hub
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {activeProject ? `Project: ${activeProject.name} • ` : ''}
            Download verified technical reports, spatial GeoJSON datasets, and numerical CSV audits for forestry planners.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {onNavigateToMap && (
            <button
              onClick={onNavigateToMap}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-950/60 hover:bg-emerald-900/40 text-emerald-300 border border-emerald-500/25 text-xs font-semibold transition cursor-pointer"
            >
              <Compass className="w-3.5 h-3.5" />
              <span>Map Explorer</span>
            </button>
          )}

          {latestRun && reportArtifact && (
            <button
              onClick={() => handleDownload(reportArtifact)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-500 hover:to-teal-600 text-white text-xs font-semibold border border-emerald-400/40 shadow-lg shadow-emerald-950/60 transition cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download HTML Audit</span>
            </button>
          )}
        </div>
      </div>

      {reportError && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{reportError}</span>
        </div>
      )}

      {/* Available Artifacts Grid */}
      {latestRun ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {/* HTML Audit Report */}
            <div className="p-4 rounded-2xl glass-panel-deep border border-emerald-500/20 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-2 border-b border-emerald-500/15 mb-2">
                  <span className="text-[10px] font-mono text-emerald-400 uppercase font-bold">Document</span>
                  <FileText className="w-4 h-4 text-emerald-400" />
                </div>
                <h4 className="text-xs font-bold text-white mb-1">Executive Audit Report</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed mb-3">
                  Comprehensive audit document with geotechnical scenarios and disclosures.
                </p>
              </div>
              <button
                onClick={() => handleDownload(latestRun.artifacts?.audit_report_html)}
                disabled={!latestRun.artifacts?.audit_report_html}
                className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-emerald-950/60 hover:bg-emerald-600 text-emerald-300 hover:text-white border border-emerald-500/20 text-xs font-mono transition cursor-pointer"
              >
                <Download className="w-3 h-3" />
                <span>HTML Report</span>
              </button>
            </div>

            {/* GeoJSON Parcels */}
            <div className="p-4 rounded-2xl glass-panel-deep border border-emerald-500/20 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-2 border-b border-emerald-500/15 mb-2">
                  <span className="text-[10px] font-mono text-cyan-400 uppercase font-bold">GIS Layer</span>
                  <FileCode className="w-4 h-4 text-cyan-400" />
                </div>
                <h4 className="text-xs font-bold text-white mb-1">Parcels GeoJSON</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed mb-3">
                  Standard RFC 7946 GeoJSON containing polygon geometries and metrics.
                </p>
              </div>
              <button
                onClick={() => handleDownload(latestRun.artifacts?.parcels_geojson || latestRun.artifacts?.geojson)}
                disabled={!latestRun.artifacts?.parcels_geojson && !latestRun.artifacts?.geojson}
                className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-cyan-950/60 hover:bg-cyan-600 text-cyan-300 hover:text-white border border-cyan-500/20 text-xs font-mono transition cursor-pointer"
              >
                <Download className="w-3 h-3" />
                <span>GeoJSON Export</span>
              </button>
            </div>

            {/* CSV Metrics */}
            <div className="p-4 rounded-2xl glass-panel-deep border border-emerald-500/20 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-2 border-b border-emerald-500/15 mb-2">
                  <span className="text-[10px] font-mono text-teal-400 uppercase font-bold">Spreadsheet</span>
                  <FileSpreadsheet className="w-4 h-4 text-teal-400" />
                </div>
                <h4 className="text-xs font-bold text-white mb-1">Parcel Metrics CSV</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed mb-3">
                  Numerical tables with slope, baseline FS, and root-reinforced parameters.
                </p>
              </div>
              <button
                onClick={() => handleDownload(latestRun.artifacts?.parcel_metrics_csv)}
                disabled={!latestRun.artifacts?.parcel_metrics_csv}
                className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-teal-950/60 hover:bg-teal-600 text-teal-300 hover:text-white border border-teal-500/20 text-xs font-mono transition cursor-pointer"
              >
                <Download className="w-3 h-3" />
                <span>Metrics CSV</span>
              </button>
            </div>

            {/* CSV Rankings */}
            <div className="p-4 rounded-2xl glass-panel-deep border border-emerald-500/20 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-2 border-b border-emerald-500/15 mb-2">
                  <span className="text-[10px] font-mono text-amber-400 uppercase font-bold">Rankings</span>
                  <Award className="w-4 h-4 text-amber-400" />
                </div>
                <h4 className="text-xs font-bold text-white mb-1">Rankings Summary CSV</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed mb-3">
                  Multi-criteria ranked order of prioritized planting parcels.
                </p>
              </div>
              <button
                onClick={() => handleDownload(latestRun.artifacts?.parcel_rankings_csv)}
                disabled={!latestRun.artifacts?.parcel_rankings_csv}
                className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-amber-950/60 hover:bg-amber-600 text-amber-300 hover:text-white border border-amber-500/20 text-xs font-mono transition cursor-pointer"
              >
                <Download className="w-3 h-3" />
                <span>Rankings CSV</span>
              </button>
            </div>
          </div>

          {/* Embedded Report Viewer */}
          <div className="rounded-2xl glass-panel-deep border border-emerald-500/20 p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-emerald-500/15">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-bold text-white uppercase font-mono">
                  Report Preview ({latestRun.run_id})
                </span>
              </div>
              <div className="text-[10.5px] font-mono text-slate-400">
                Timestamp: {new Date(latestRun.timestamp).toLocaleString()}
              </div>
            </div>

            {reportHtml ? (
              <div className="rounded-xl bg-[#091a13] border border-emerald-500/20 p-4 max-h-[500px] overflow-y-auto">
                <div
                  className="prose prose-invert prose-sm max-w-none text-slate-300"
                  dangerouslySetInnerHTML={{ __html: reportHtml }}
                />
              </div>
            ) : isLoadingReport ? (
              <div className="py-12 text-center text-xs font-mono text-slate-400">
                Loading technical report...
              </div>
            ) : (
              <div className="py-8 text-center text-xs text-slate-400 space-y-2">
                <p>Report preview is ready for download.</p>
                {reportArtifact && (
                  <button
                    onClick={() => handleDownload(reportArtifact)}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 text-xs font-semibold"
                  >
                    <Download className="w-3 h-3" />
                    <span>Download Report HTML</span>
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="p-8 rounded-2xl glass-panel-deep border border-emerald-500/20 text-center space-y-3">
          <AlertCircle className="w-8 h-8 text-slate-500 mx-auto" />
          <h3 className="text-sm font-semibold text-white">No Analysis Runs Found</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Run a spatial recommendation analysis in this workspace to generate audit reports, GeoJSON parcels, and CSV exports.
          </p>
          {onNavigateToWizard && (
            <button
              onClick={onNavigateToWizard}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-500 hover:to-teal-600 text-white text-xs font-semibold transition"
            >
              Start New Analysis
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default ReportsView;
