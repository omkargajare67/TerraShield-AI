import type {
  ProjectMetadata,
  RecommendationRunResponse,
  SystemHealth,
  VectorReport,
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
          if (json.detail) message = json.detail;
        } catch {
          if (errText) message = errText;
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

  async getRunSummary(runId: string): Promise<RecommendationRunResponse> {
    return this.request<RecommendationRunResponse>(`/api/v1/recommendations/runs/${encodeURIComponent(runId)}`);
  }
}

export const api = new ApiClient();
