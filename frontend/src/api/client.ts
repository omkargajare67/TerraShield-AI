import type {
  ProjectMetadata,
  RecommendationRunResponse,
  SystemHealth,
  VectorReport,
  CaseStudy,
  LaunchWorkspaceResponse,
  CaseStudyComparisonResult,
} from './types';

export const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');

class ApiClient {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers: Record<string, string> = {
      ...((options.headers as Record<string, string>) || {}),
    };

    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    try {
      const response = await fetch(url, { ...options, headers });
      if (!response.ok) {
        const errText = await response.text();
        let message = `API Error (${response.status}): ${response.statusText}`;
        try {
          const json = JSON.parse(errText);
          if (json.detail) {
            message = typeof json.detail === 'string' ? json.detail : JSON.stringify(json.detail);
          }
        } catch {
          if (errText) message = errText;
        }

        if (response.status === 405) {
          message = `Method Not Allowed (HTTP 405) for ${url}. The server may be running an older build that requires a restart, or the route configuration does not support this HTTP method.`;
        }

        throw new Error(message);
      }
      return (await response.json()) as T;
    } catch (err: any) {
      console.error(`Request to ${url} failed:`, err);
      throw err;
    }
  }

  async getHealth(): Promise<SystemHealth> {
    return this.request<SystemHealth>('/health');
  }

  async getProjects(): Promise<ProjectMetadata[]> {
    return this.request<ProjectMetadata[]>('/api/v1/projects');
  }

  async getProject(id: string): Promise<ProjectMetadata> {
    return this.request<ProjectMetadata>(`/api/v1/projects/${id}`);
  }

  async createProject(payload: {
    name: string;
    description?: string;
    study_area_type?: string;
    bounds?: { minx: number; miny: number; maxx: number; maxy: number };
    geotech_preset_id?: string;
  }): Promise<ProjectMetadata> {
    return this.request<ProjectMetadata>('/api/v1/projects', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async updateProject(id: string, payload: Partial<ProjectMetadata>): Promise<ProjectMetadata> {
    return this.request<ProjectMetadata>(`/api/v1/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  async deleteProject(id: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/projects/${id}`, {
      method: 'DELETE',
    });
  }

  async getPresets(): Promise<Record<string, any>> {
    return this.request<Record<string, any>>('/api/v1/projects/presets');
  }

  async uploadVector(
    projectId: string,
    file: File,
    purpose: 'boundary' | 'exclusion' = 'boundary'
  ): Promise<{ message: string; report: VectorReport }> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('purpose', purpose);

    return this.request<{ message: string; report: VectorReport }>(
      `/api/v1/projects/${projectId}/upload-vector`,
      {
        method: 'POST',
        body: formData,
      }
    );
  }

  async uploadRaster(
    projectId: string,
    file: File,
    layerType: 'dem' | 'ndvi' | 'red' | 'nir' = 'dem'
  ): Promise<{ message: string; validation: any }> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('layer_type', layerType);

    return this.request<{ message: string; validation: any }>(
      `/api/v1/projects/${projectId}/upload-raster`,
      {
        method: 'POST',
        body: formData,
      }
    );
  }

  async processTerrain(projectId: string): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/process-terrain`, {
      method: 'POST',
    });
  }

  async processGeotechnical(projectId: string): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/process-geotechnical`, {
      method: 'POST',
    });
  }

  async runRecommendations(payload: any): Promise<RecommendationRunResponse> {
    return this.request<RecommendationRunResponse>('/api/v1/recommendations/run', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  getArtifactUrl(artifactId: string): string {
    return `${API_BASE_URL}/api/v1/recommendations/artifacts/${encodeURIComponent(artifactId)}`;
  }

  async fetchArtifactJson(artifactId: string): Promise<any> {
    return this.request<any>(`/api/v1/recommendations/artifacts/${encodeURIComponent(artifactId)}`);
  }

  async validateAOI(payload: {
    bounds?: { minx: number; miny: number; maxx: number; maxy: number };
    boundary_geojson?: any;
  }): Promise<{ is_valid: boolean; bounds: any; boundary_geojson: any; area_ha: number }> {
    return this.request('/api/v1/projects/validate-aoi', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async autoAnalyze(payload: {
    name?: string;
    project_id?: string;
    bounds?: { minx: number; miny: number; maxx: number; maxy: number };
    boundary_geojson?: any;
    geotech_preset_id?: string;
    cell_size_m?: number;
    priority_preset?: string;
    async_job?: boolean;
  }): Promise<any> {
    return this.request('/api/v1/projects/auto-analyze', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getAutoAnalyzeStatus(jobId: string): Promise<{
    job_id: string;
    status: 'RUNNING' | 'COMPLETED' | 'FAILED';
    stage_number: number;
    stage_title: string;
    stage_message: string;
    project_id?: string;
    result?: any;
    error?: string;
  }> {
    return this.request(`/api/v1/projects/auto-analyze/status/${encodeURIComponent(jobId)}`);
  }

  async getRunSummary(runId: string): Promise<RecommendationRunResponse> {
    return this.request<RecommendationRunResponse>(`/api/v1/recommendations/runs/${encodeURIComponent(runId)}`);
  }

  async getCaseStudies(region?: string, readiness?: string): Promise<CaseStudy[]> {
    const params = new URLSearchParams();
    if (region) params.append('region', region);
    if (readiness) params.append('readiness', readiness);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return this.request<CaseStudy[]>(`/api/v1/case-studies${qs}`);
  }

  async getCaseStudy(caseId: string): Promise<CaseStudy> {
    return this.request<CaseStudy>(`/api/v1/case-studies/${encodeURIComponent(caseId)}`);
  }

  async getCaseStudyObservedInventory(caseId: string): Promise<any> {
    return this.request<any>(`/api/v1/case-studies/${encodeURIComponent(caseId)}/observed-inventory`);
  }

  async launchCaseStudyWorkspace(caseId: string): Promise<LaunchWorkspaceResponse> {
    return this.request<LaunchWorkspaceResponse>(`/api/v1/case-studies/${encodeURIComponent(caseId)}/launch-workspace`, {
      method: 'POST',
    });
  }

  async compareCaseStudyResults(
    caseId: string,
    payload: { run_id?: string; parcels_geojson?: any; concern_fs_threshold?: number }
  ): Promise<CaseStudyComparisonResult> {
    return this.request<CaseStudyComparisonResult>(`/api/v1/case-studies/${encodeURIComponent(caseId)}/compare`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getRecommendationStatus(): Promise<any> {
    return this.request<any>('/api/v1/recommendations/status');
  }

  async queryParcelSpecies(parcelId: string, elevationM?: number, slopeDeg?: number): Promise<any> {
    const params = new URLSearchParams();
    if (elevationM !== undefined) params.append('elevation_m', elevationM.toString());
    if (slopeDeg !== undefined) params.append('slope_deg', slopeDeg.toString());
    const qs = params.toString() ? `?${params.toString()}` : '';
    return this.request<any>(`/api/v1/recommendations/species/${encodeURIComponent(parcelId)}${qs}`);
  }

  async getReportHtml(artifactId: string): Promise<string> {
    const url = `${API_BASE_URL}/api/v1/recommendations/artifacts/${encodeURIComponent(artifactId)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to load report artifact: ${res.statusText}`);
    return res.text();
  }
}

export const api = new ApiClient();

