import React, { useState } from 'react';
import {
  FolderKanban,
  Database,
  Upload,
  Plus,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  Layers,
  MapPin,
  RefreshCw,
  ChevronRight,
  ArrowRight,
  BarChart3,
} from 'lucide-react';
import type { ProjectMetadata, VectorReport } from '../api/types';
import { api } from '../api/client';
import { ProvenanceBanner } from '../components/common/ProvenanceBanner';

interface ProjectsDataLibraryViewProps {
  projects: ProjectMetadata[];
  selectedProjectId: string | null;
  onSelectProject: (id: string) => void;
  onRefreshProjects: () => void;
  onOpenCreateModal: () => void;
  onNavigateToWizard?: () => void;
  onNavigateToResults?: () => void;
}

export const ProjectsDataLibraryView: React.FC<ProjectsDataLibraryViewProps> = ({
  projects,
  selectedProjectId,
  onSelectProject,
  onRefreshProjects,
  onOpenCreateModal,
  onNavigateToWizard,
  onNavigateToResults,
}) => {
  const [activeTab, setActiveTab] = useState<'projects' | 'data'>('projects');
  const [vectorFile, setVectorFile] = useState<File | null>(null);
  const [vectorPurpose, setVectorPurpose] = useState<'boundary' | 'exclusion'>('boundary');
  const [rasterFile, setRasterFile] = useState<File | null>(null);
  const [rasterLayerType, setRasterLayerType] = useState<'dem' | 'ndvi' | 'red' | 'nir'>('dem');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [lastVectorReport, setLastVectorReport] = useState<VectorReport | null>(null);

  const activeProject = projects.find((p) => p.id === selectedProjectId) || null;

  const handleUploadVector = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProject || !vectorFile) return;

    setIsUploading(true);
    setStatusMessage(null);
    setLastVectorReport(null);

    try {
      const res = await api.uploadVector(activeProject.id, vectorFile, vectorPurpose);
      setStatusMessage(`Vector uploaded successfully: ${res.message}`);
      setLastVectorReport(res.report);
      setVectorFile(null);
      onRefreshProjects();
    } catch (err: any) {
      setStatusMessage(`Vector upload failed: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleUploadRaster = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProject || !rasterFile) return;

    setIsUploading(true);
    setStatusMessage(null);

    try {
      await api.uploadRaster(activeProject.id, rasterFile, rasterLayerType);
      setStatusMessage(`Raster (${rasterLayerType.toUpperCase()}) uploaded and verified successfully!`);
      setRasterFile(null);
      onRefreshProjects();
    } catch (err: any) {
      setStatusMessage(`Raster upload failed: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleProcessTerrain = async () => {
    if (!activeProject) return;
    setIsUploading(true);
    setStatusMessage(null);
    try {
      const res = await api.processTerrain(activeProject.id);
      setStatusMessage(`Terrain processing completed: ${res.message || 'Slope & Aspect generated'}`);
      onRefreshProjects();
    } catch (err: any) {
      setStatusMessage(`Terrain processing error: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-2 border-b border-terra-border/30">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono tracking-wider font-semibold uppercase bg-terra-mint/15 text-terra-mint border border-terra-mint/25">
              Workspace & Asset Management
            </span>
            <span className="text-xs text-terra-slate font-mono">
              Vector & Raster Provenance
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-display font-semibold text-terra-ivory">
            My Projects & Data Library
          </h1>
          <p className="text-sm text-terra-muted mt-1">
            Manage environmental study workspaces, boundary shapefiles, elevation rasters, and multispectral assets.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Tab Switcher */}
          <div className="flex items-center p-1 rounded-xl bg-terra-deep/70 border border-terra-border/40 text-xs">
            <button
              onClick={() => setActiveTab('projects')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition font-medium cursor-pointer ${
                activeTab === 'projects'
                  ? 'bg-terra-forest text-terra-mint font-semibold shadow-sm'
                  : 'text-terra-muted hover:text-terra-ivory'
              }`}
            >
              <FolderKanban className="w-3.5 h-3.5" />
              <span>Projects ({projects.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('data')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition font-medium cursor-pointer ${
                activeTab === 'data'
                  ? 'bg-terra-forest text-terra-mint font-semibold shadow-sm'
                  : 'text-terra-muted hover:text-terra-ivory'
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              <span>Data Layers & Upload</span>
            </button>
          </div>

          <button
            onClick={onOpenCreateModal}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-terra-mint text-terra-deep text-xs font-semibold hover:bg-terra-mint/90 transition shadow-md shadow-terra-mint/10 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Project</span>
          </button>
        </div>
      </div>

      <ProvenanceBanner />

      {statusMessage && (
        <div
          className={`p-4 rounded-xl border text-xs font-mono flex items-center gap-3 ${
            statusMessage.includes('failed') || statusMessage.includes('error')
              ? 'bg-rose-500/10 border-rose-500/30 text-rose-300'
              : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
          }`}
        >
          {statusMessage.includes('failed') || statusMessage.includes('error') ? (
            <AlertTriangle className="w-4 h-4 shrink-0" />
          ) : (
            <CheckCircle2 className="w-4 h-4 shrink-0" />
          )}
          <span>{statusMessage}</span>
        </div>
      )}

      {/* View: Projects List */}
      {activeTab === 'projects' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((proj) => {
              const isSelected = proj.id === selectedProjectId;
              const layerCount = Object.keys(proj.layers || {}).length;
              const runCount = proj.saved_runs?.length || 0;

              return (
                <div
                  key={proj.id}
                  onClick={() => onSelectProject(proj.id)}
                  className={`group relative p-6 rounded-3xl border transition-all cursor-pointer backdrop-blur-xl ${
                    isSelected
                      ? 'bg-terra-forest/60 border-terra-mint shadow-xl shadow-terra-mint/5'
                      : 'bg-terra-forest/20 border-terra-border/40 hover:border-terra-border hover:bg-terra-forest/40'
                  }`}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="w-10 h-10 rounded-2xl bg-terra-mint/10 border border-terra-mint/20 text-terra-mint flex items-center justify-center">
                      <FolderKanban className="w-5 h-5" />
                    </div>
                    {isSelected ? (
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-terra-mint text-terra-deep">
                        Active Workspace
                      </span>
                    ) : (
                      <span className="text-xs text-terra-slate font-mono">
                        {proj.id.slice(0, 8)}
                      </span>
                    )}
                  </div>

                  <h3 className="text-base font-display font-semibold text-terra-ivory mb-1 group-hover:text-terra-mint transition">
                    {proj.name}
                  </h3>
                  <p className="text-xs text-terra-muted line-clamp-2 mb-4">
                    {proj.description || 'No description provided.'}
                  </p>

                  <div className="space-y-1.5 pt-3 border-t border-terra-border/30 text-[11px] text-terra-slate font-mono">
                    <div className="flex justify-between">
                      <span>Attached Layers:</span>
                      <span className="text-terra-ivory font-semibold">{layerCount} layers</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Completed Runs:</span>
                      <span className="text-terra-ivory font-semibold">{runCount} run{runCount === 1 ? '' : 's'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Area Type:</span>
                      <span className="text-terra-ivory">{proj.study_area_type || 'Catchment'}</span>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-terra-border/30 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectProject(proj.id);
                          if (onNavigateToWizard) onNavigateToWizard();
                        }}
                        className="text-xs text-terra-mint hover:underline font-semibold flex items-center gap-1 cursor-pointer"
                      >
                        <span>Run Analysis</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>

                      {runCount > 0 && onNavigateToResults && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectProject(proj.id);
                            onNavigateToResults();
                          }}
                          className="text-xs text-terra-ivory hover:text-terra-mint font-medium flex items-center gap-1 cursor-pointer"
                        >
                          <BarChart3 className="w-3 h-3 text-terra-mint" />
                          <span>Results</span>
                        </button>
                      )}
                    </div>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectProject(proj.id);
                        setActiveTab('data');
                      }}
                      className="text-xs text-terra-muted hover:text-terra-ivory flex items-center gap-1 cursor-pointer"
                    >
                      <span>Layers</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* View: Data Layers & Uploaders */}
      {activeTab === 'data' && (
        <div className="space-y-8">
          {/* Active Project Banner */}
          <div className="p-5 rounded-2xl bg-terra-forest/30 border border-terra-border/40 backdrop-blur-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-terra-mint/10 border border-terra-mint/20 flex items-center justify-center text-terra-mint">
                <MapPin className="w-5 h-5" />
              </div>
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-terra-slate">
                  Selected Workspace
                </span>
                <h3 className="text-base font-display font-semibold text-terra-ivory">
                  {activeProject ? activeProject.name : 'No Project Selected'}
                </h3>
              </div>
            </div>

            {activeProject && (
              <button
                onClick={handleProcessTerrain}
                disabled={isUploading}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-terra-forest border border-terra-mint/40 text-terra-mint hover:bg-terra-forest/80 text-xs font-semibold transition cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isUploading ? 'animate-spin' : ''}`} />
                <span>Process DEM (Generate Slope & Aspect)</span>
              </button>
            )}
          </div>

          {/* Upload Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Vector Boundary Upload Card */}
            <div className="p-6 rounded-3xl bg-terra-forest/20 border border-terra-border/40 backdrop-blur-xl space-y-5">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-terra-mint/10 border border-terra-mint/20 flex items-center justify-center text-terra-mint">
                  <FileCode className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-terra-ivory">
                    Upload Vector Boundary Layer
                  </h3>
                  <p className="text-xs text-terra-slate">
                    Upload GeoJSON, Shapefile (.zip), or GeoPackage (.gpkg)
                  </p>
                </div>
              </div>

              <form onSubmit={handleUploadVector} className="space-y-4">
                <div>
                  <label className="block text-xs font-mono text-terra-muted mb-1.5">
                    Layer Purpose
                  </label>
                  <select
                    value={vectorPurpose}
                    onChange={(e) => setVectorPurpose(e.target.value as any)}
                    className="w-full px-3 py-2 rounded-xl bg-terra-deep/70 border border-terra-border/60 text-terra-ivory text-xs font-mono focus:outline-none focus:border-terra-mint"
                  >
                    <option value="boundary">Study Area Boundary (Polygons)</option>
                    <option value="exclusion">Exclusion Zones (Mask Layer)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-mono text-terra-muted mb-1.5">
                    Select File
                  </label>
                  <input
                    type="file"
                    accept=".geojson,.json,.zip,.gpkg"
                    onChange={(e) => setVectorFile(e.target.files?.[0] || null)}
                    className="w-full text-xs text-terra-muted file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-terra-forest file:text-terra-mint hover:file:bg-terra-forest/80 cursor-pointer"
                  />
                </div>

                <button
                  type="submit"
                  disabled={!vectorFile || !activeProject || isUploading}
                  className="w-full py-2.5 rounded-xl bg-terra-mint text-terra-deep font-semibold text-xs hover:bg-terra-mint/90 transition shadow-md shadow-terra-mint/10 disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
                >
                  <Upload className="w-4 h-4" />
                  <span>{isUploading ? 'Validating Geometry...' : 'Upload & Validate Vector'}</span>
                </button>
              </form>

              {lastVectorReport && (
                <div className="p-3.5 rounded-xl bg-terra-deep/70 border border-terra-border/40 text-[11px] font-mono space-y-1 text-terra-muted">
                  <span className="text-terra-mint font-semibold block">Geometry Validated:</span>
                  <div>Features: {lastVectorReport.feature_count}</div>
                  <div>Geometry: {lastVectorReport.geometry_types?.join(', ') || lastVectorReport.geom_type || 'Polygon'}</div>
                  <div>CRS: {lastVectorReport.crs || lastVectorReport.original_crs}</div>
                  <div>Total Area: {(lastVectorReport.area_approx_ha || 0).toFixed(1)} ha</div>
                </div>
              )}
            </div>

            {/* Raster DEM / NDVI Upload Card */}
            <div className="p-6 rounded-3xl bg-terra-forest/20 border border-terra-border/40 backdrop-blur-xl space-y-5">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-terra-mint/10 border border-terra-mint/20 flex items-center justify-center text-terra-mint">
                  <Layers className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-terra-ivory">
                    Upload Raster Grid Layer
                  </h3>
                  <p className="text-xs text-terra-slate">
                    Upload GeoTIFF (.tif) elevation or multispectral bands
                  </p>
                </div>
              </div>

              <form onSubmit={handleUploadRaster} className="space-y-4">
                <div>
                  <label className="block text-xs font-mono text-terra-muted mb-1.5">
                    Raster Layer Type
                  </label>
                  <select
                    value={rasterLayerType}
                    onChange={(e) => setRasterLayerType(e.target.value as any)}
                    className="w-full px-3 py-2 rounded-xl bg-terra-deep/70 border border-terra-border/60 text-terra-ivory text-xs font-mono focus:outline-none focus:border-terra-mint"
                  >
                    <option value="dem">Digital Elevation Model (DEM) - Required</option>
                    <option value="ndvi">Vegetation Index (NDVI) - Optional</option>
                    <option value="red">Sentinel-2 Band 4 (Red) - Optional</option>
                    <option value="nir">Sentinel-2 Band 8 (NIR) - Optional</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-mono text-terra-muted mb-1.5">
                    Select GeoTIFF File (.tif)
                  </label>
                  <input
                    type="file"
                    accept=".tif,.tiff"
                    onChange={(e) => setRasterFile(e.target.files?.[0] || null)}
                    className="w-full text-xs text-terra-muted file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-terra-forest file:text-terra-mint hover:file:bg-terra-forest/80 cursor-pointer"
                  />
                </div>

                <button
                  type="submit"
                  disabled={!rasterFile || !activeProject || isUploading}
                  className="w-full py-2.5 rounded-xl bg-terra-mint text-terra-deep font-semibold text-xs hover:bg-terra-mint/90 transition shadow-md shadow-terra-mint/10 disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
                >
                  <Upload className="w-4 h-4" />
                  <span>{isUploading ? 'Validating GeoTIFF...' : 'Upload & Validate GeoTIFF'}</span>
                </button>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectsDataLibraryView;
