import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X, FolderPlus, AlertCircle, RefreshCw } from 'lucide-react';
import type { ProjectMetadata, RecommendationRunResponse, SystemHealth } from './api/types';
import { api } from './api/client';

// Layout & Common Components
import { Navbar } from './components/common/Navbar';
import { Sidebar, type ViewTab } from './components/common/Sidebar';

// Views
import { OverviewView } from './views/OverviewView';
import { AnalysisWizardView } from './views/AnalysisWizardView';
import { MapExplorerView } from './views/MapExplorerView';
import { ResultsView } from './views/ResultsView';
import { GeotechnicalStudioView } from './views/GeotechnicalStudioView';
import { ProjectsDataLibraryView } from './views/ProjectsDataLibraryView';

export function App() {
  const [activeTab, setActiveTab] = useState<ViewTab>('overview');
  const [projects, setProjects] = useState<ProjectMetadata[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [latestRun, setLatestRun] = useState<RecommendationRunResponse | null>(null);
  const [parcelsGeojson, setParcelsGeojson] = useState<any>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [createFormData, setCreateFormData] = useState({
    name: '',
    description: '',
    study_area_type: 'Western Ghats Catchment',
    geotech_preset_id: 'wayanad',
  });
  const [isSubmittingProject, setIsSubmittingProject] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  // Health check function
  const checkHealth = useCallback(async () => {
    try {
      const h = await api.getHealth();
      setHealth(h);
    } catch (err) {
      console.warn('API health check returned offline:', err);
      setHealth({ status: 'offline', version: 'unknown' });
    }
  }, []);

  // Load initial health and project list
  const refreshProjects = useCallback(async () => {
    try {
      const data = await api.getProjects();
      setProjects(data);
      if (data.length > 0 && !selectedProjectId) {
        setSelectedProjectId(data[0].id);
      }
    } catch (err) {
      console.warn('Could not fetch projects list:', err);
    }
  }, [selectedProjectId]);

  useEffect(() => {
    checkHealth();
    refreshProjects();
  }, [checkHealth, refreshProjects]);

  const activeProject = projects.find((p) => p.id === selectedProjectId) || null;

  // Whenever selected project changes, check if it has saved runs and load latest run data
  useEffect(() => {
    if (!activeProject) return;

    const savedRuns = activeProject.saved_runs || [];
    const runIdToLoad = activeProject.latest_run_id || (savedRuns.length > 0 ? savedRuns[savedRuns.length - 1].run_id : null);

    if (runIdToLoad && (!latestRun || latestRun.run_id !== runIdToLoad)) {
      api
        .getRunSummary(runIdToLoad)
        .then((summary) => {
          setLatestRun(summary);
          if (summary.artifacts?.geojson) {
            api
              .fetchArtifactJson(summary.artifacts.geojson)
              .then((geo) => setParcelsGeojson(geo))
              .catch((e) => console.warn('Could not load artifact GeoJSON:', e));
          }
        })
        .catch((err) => {
          console.warn('Could not load saved run summary for project:', err);
        });
    }
  }, [activeProject, latestRun]);

  // When a new analysis finishes in wizard
  const handleAnalysisComplete = (result: RecommendationRunResponse) => {
    setLatestRun(result);

    // If an artifact was produced, load its GeoJSON for the interactive map
    if (result.artifacts?.geojson) {
      api
        .fetchArtifactJson(result.artifacts.geojson)
        .then((geo) => {
          setParcelsGeojson(geo);
        })
        .catch((err) => {
          console.warn('Could not load artifact GeoJSON directly:', err);
        });
    }

    refreshProjects();
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createFormData.name.trim()) return;

    setIsSubmittingProject(true);
    setModalError(null);

    try {
      const created = await api.createProject({
        name: createFormData.name.trim(),
        description: createFormData.description.trim() || undefined,
        study_area_type: createFormData.study_area_type,
        geotech_preset_id: createFormData.geotech_preset_id,
      });

      setProjects((prev) => [created, ...prev]);
      setSelectedProjectId(created.id);
      setIsCreateModalOpen(false);
      setCreateFormData({
        name: '',
        description: '',
        study_area_type: 'Western Ghats Catchment',
        geotech_preset_id: 'wayanad',
      });
    } catch (err: any) {
      setModalError(err.message || 'Failed to create project');
    } finally {
      setIsSubmittingProject(false);
    }
  };

  return (
    <div className="min-h-screen bg-terra-deep text-terra-ivory font-sans flex flex-col selection:bg-terra-mint selection:text-terra-deep">
      {/* Top Navbar */}
      <Navbar
        projects={projects}
        selectedProjectId={selectedProjectId}
        onSelectProject={(id) => setSelectedProjectId(id)}
        onOpenCreateModal={() => setIsCreateModalOpen(true)}
        health={health}
        onRetryHealth={checkHealth}
      />

      {/* Backend Offline Advisory Banner */}
      {health && health.status === 'offline' && (
        <div className="bg-amber-500/15 border-b border-amber-500/30 px-6 py-2.5 text-xs text-amber-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              Backend API is currently offline. Ensure the FastAPI server is running on port 8000.
            </span>
          </div>
          <button
            onClick={checkHealth}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 font-semibold transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry Connection</span>
          </button>
        </div>
      )}

      {/* Main App Body with Sidebar + Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Navigation Sidebar */}
        <Sidebar currentTab={activeTab} onTabChange={(tab: ViewTab) => setActiveTab(tab)} />

        {/* Dynamic Main View Area */}
        <main className="flex-1 overflow-y-auto relative">
          <AnimatePresence mode="wait">
            {activeTab === 'overview' && (
              <motion.div
                key="overview"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2 }}
              >
                <OverviewView
                  activeProject={activeProject}
                  latestRun={latestRun}
                  onStartAnalysis={() => setActiveTab('wizard')}
                  onOpenDataLibrary={() => setActiveTab('projects')}
                  onSelectProject={(id) => setSelectedProjectId(id)}
                  onOpenResults={() => setActiveTab('results')}
                  onOpenCreateModal={() => setIsCreateModalOpen(true)}
                />
              </motion.div>
            )}

            {activeTab === 'wizard' && (
              <motion.div
                key="wizard"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2 }}
              >
                <AnalysisWizardView
                  project={activeProject}
                  projects={projects}
                  onSelectProject={(id) => setSelectedProjectId(id)}
                  onAnalysisComplete={handleAnalysisComplete}
                  onNavigateTab={(tab) => setActiveTab(tab)}
                />
              </motion.div>
            )}

            {activeTab === 'map' && (
              <motion.div
                key="map"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2 }}
                className="py-4"
              >
                <MapExplorerView
                  activeProject={activeProject}
                  parcelsGeojson={parcelsGeojson}
                  latestRun={latestRun}
                  onNavigateToWizard={() => setActiveTab('wizard')}
                />
              </motion.div>
            )}

            {activeTab === 'results' && (
              <motion.div
                key="results"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2 }}
              >
                <ResultsView
                  latestRun={latestRun}
                  parcelsGeojson={parcelsGeojson}
                  onNavigateToWizard={() => setActiveTab('wizard')}
                  onNavigateToMap={() => setActiveTab('map')}
                />
              </motion.div>
            )}

            {activeTab === 'geotech' && (
              <motion.div
                key="geotech"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2 }}
              >
                <GeotechnicalStudioView
                  activeProject={activeProject}
                  onRunComplete={() => refreshProjects()}
                />
              </motion.div>
            )}

            {activeTab === 'projects' && (
              <motion.div
                key="projects"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2 }}
              >
                <ProjectsDataLibraryView
                  projects={projects}
                  selectedProjectId={selectedProjectId}
                  onSelectProject={(id) => setSelectedProjectId(id)}
                  onRefreshProjects={refreshProjects}
                  onOpenCreateModal={() => setIsCreateModalOpen(true)}
                  onNavigateToWizard={() => setActiveTab('wizard')}
                  onNavigateToResults={() => setActiveTab('results')}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      </div>

      {/* New Project Dialog Modal */}
      <AnimatePresence>
        {isCreateModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsCreateModalOpen(false)}
              className="fixed inset-0 bg-terra-deep/75 backdrop-blur-md"
            />

            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 10 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 10 }}
              transition={{ type: 'spring', damping: 25, stiffness: 220 }}
              className="relative w-full max-w-lg rounded-3xl bg-terra-forest/90 border border-terra-border/60 p-6 md:p-8 backdrop-blur-2xl shadow-2xl z-10"
            >
              <div className="flex items-start justify-between pb-4 border-b border-terra-border/40 mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-terra-mint/10 border border-terra-mint/20 text-terra-mint flex items-center justify-center shadow-inner">
                    <FolderPlus className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-lg font-display font-semibold text-terra-ivory">
                      Initialize Environmental Project
                    </h3>
                    <p className="text-xs text-terra-slate">
                      Create an isolated workspace for terrain modeling and parcel prioritization.
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => setIsCreateModalOpen(false)}
                  className="p-1.5 rounded-xl bg-terra-deep/40 hover:bg-terra-deep text-terra-slate hover:text-terra-ivory border border-terra-border/30 transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {modalError && (
                <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-mono flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{modalError}</span>
                </div>
              )}

              <form onSubmit={handleCreateProject} className="space-y-4">
                <div>
                  <label className="block text-xs font-mono text-terra-muted mb-1.5">
                    Project Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={createFormData.name}
                    onChange={(e) => setCreateFormData({ ...createFormData, name: e.target.value })}
                    placeholder="e.g. Meppadi Catchment Stabilization"
                    className="w-full px-4 py-2.5 rounded-xl bg-terra-deep/80 border border-terra-border/60 text-terra-ivory text-xs placeholder:text-terra-slate focus:outline-none focus:border-terra-mint"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-terra-muted mb-1.5">
                    Description & Objectives
                  </label>
                  <textarea
                    rows={2}
                    value={createFormData.description}
                    onChange={(e) =>
                      setCreateFormData({ ...createFormData, description: e.target.value })
                    }
                    placeholder="Brief scope, geomorphic risks, or targeted planting goals..."
                    className="w-full px-4 py-2.5 rounded-xl bg-terra-deep/80 border border-terra-border/60 text-terra-ivory text-xs placeholder:text-terra-slate focus:outline-none focus:border-terra-mint resize-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-mono text-terra-muted mb-1.5">
                      Terrain Setting
                    </label>
                    <select
                      value={createFormData.study_area_type}
                      onChange={(e) =>
                        setCreateFormData({ ...createFormData, study_area_type: e.target.value })
                      }
                      className="w-full px-3 py-2 rounded-xl bg-terra-deep/80 border border-terra-border/60 text-terra-ivory text-xs font-mono focus:outline-none focus:border-terra-mint"
                    >
                      <option value="Western Ghats Catchment">Western Ghats Catchment</option>
                      <option value="Himalayan Foothills">Himalayan Foothills</option>
                      <option value="Tropical Humid Escarpment">Tropical Humid Escarpment</option>
                      <option value="Custom Domain">Custom Domain</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-mono text-terra-muted mb-1.5">
                      Geotech Preset
                    </label>
                    <select
                      value={createFormData.geotech_preset_id}
                      onChange={(e) =>
                        setCreateFormData({ ...createFormData, geotech_preset_id: e.target.value })
                      }
                      className="w-full px-3 py-2 rounded-xl bg-terra-deep/80 border border-terra-border/60 text-terra-ivory text-xs font-mono focus:outline-none focus:border-terra-mint"
                    >
                      <option value="wayanad">Wayanad Saprolite</option>
                      <option value="claySilt">Colluvial Clay-Silt</option>
                      <option value="sandyLoam">Residual Sandy Loam</option>
                      <option value="cohesionless">Debris Flow Colluvium</option>
                    </select>
                  </div>
                </div>

                <div className="pt-4 border-t border-terra-border/40 flex items-center justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setIsCreateModalOpen(false)}
                    className="px-4 py-2.5 rounded-xl text-terra-slate hover:text-terra-ivory text-xs font-semibold transition cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmittingProject || !createFormData.name.trim()}
                    className="px-6 py-2.5 rounded-xl bg-terra-mint text-terra-deep font-semibold text-xs hover:bg-terra-mint/90 transition shadow-lg shadow-terra-mint/10 disabled:opacity-50 cursor-pointer"
                  >
                    {isSubmittingProject ? 'Creating...' : 'Create Workspace'}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
