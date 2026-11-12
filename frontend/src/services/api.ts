/**
 * Typed API client for the UAV-QAOA-SAR FastAPI backend.
 */
import {
  CompareRequestDTO,
  CompareResponseDTO,
  HistoryDetailDTO,
  HistoryListDTO,
  OptimizationResponseDTO,
  OptimizeRequestDTO,
  RFSimulationRequestDTO,
  RFSimulationResponseDTO,
  ScenarioDetailDTO,
  ScenarioSummaryDTO,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail || `Request failed with status ${res.status}`);
  }
  return res.json();
}

export const apiService = {
  /** Check backend connectivity and status */
  async getHealth(): Promise<{ status: string; service: string }> {
    const res = await fetch(`${API_BASE_URL}/health`);
    return handleResponse<{ status: string; service: string }>(res);
  },

  /** List available SAR scenarios */
  async listScenarios(): Promise<ScenarioSummaryDTO[]> {
    const res = await fetch(`${API_BASE_URL}/scenarios`);
    return handleResponse<ScenarioSummaryDTO[]>(res);
  },

  /** Get the standard canonical 5-target, 6-waypoint, k=3 benchmark scenario */
  async getCanonicalScenario(): Promise<ScenarioDetailDTO> {
    const res = await fetch(`${API_BASE_URL}/scenarios/canonical`);
    return handleResponse<ScenarioDetailDTO>(res);
  },

  /** Get the deterministic RF demonstration scenario with 3D link budget */
  async getRFDemonstrationScenario(): Promise<ScenarioDetailDTO> {
    const res = await fetch(`${API_BASE_URL}/scenarios/rf-demonstration`);
    return handleResponse<ScenarioDetailDTO>(res);
  },

  /** Retrieve scenario details by ID */
  async getScenario(id: string): Promise<ScenarioDetailDTO> {
    const res = await fetch(`${API_BASE_URL}/scenarios/${encodeURIComponent(id)}`);
    return handleResponse<ScenarioDetailDTO>(res);
  },

  /** Simulate RF link budgets and regenerate coverage matrix */
  async simulateRF(req: RFSimulationRequestDTO): Promise<RFSimulationResponseDTO> {
    const res = await fetch(`${API_BASE_URL}/scenarios/rf-simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse<RFSimulationResponseDTO>(res);
  },

  /** Run a single optimization */
  async runOptimization(req: OptimizeRequestDTO): Promise<OptimizationResponseDTO> {
    const res = await fetch(`${API_BASE_URL}/optimize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse<OptimizationResponseDTO>(res);
  },

  /** Run a multi-solver benchmark comparison */
  async compareSolvers(req: CompareRequestDTO): Promise<CompareResponseDTO> {
    const res = await fetch(`${API_BASE_URL}/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse<CompareResponseDTO>(res);
  },

  /** Retrieve paginated history of optimization runs */
  async getHistory(limit: number = 20, offset: number = 0): Promise<HistoryListDTO> {
    const res = await fetch(`${API_BASE_URL}/history?limit=${limit}&offset=${offset}`);
    return handleResponse<HistoryListDTO>(res);
  },

  /** Get full details of a specific historical run */
  async getHistoryDetail(runId: string): Promise<HistoryDetailDTO> {
    const res = await fetch(`${API_BASE_URL}/history/${encodeURIComponent(runId)}`);
    return handleResponse<HistoryDetailDTO>(res);
  },

  /** Delete a historical run by run_id */
  async deleteHistoryItem(runId: string): Promise<{ status: string; run_id: string }> {
    const res = await fetch(`${API_BASE_URL}/history/${encodeURIComponent(runId)}`, {
      method: 'DELETE',
    });
    return handleResponse<{ status: string; run_id: string }>(res);
  },
};
