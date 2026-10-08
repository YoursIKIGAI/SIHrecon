import {
  SimulationResponse,
  RouteResponse,
  ValidationMetrics,
  SystemStatus,
  ScenarioInfo,
  RainfallPoint,
  MLTrainingResponse,
  LocationSearchResult,
  EngineMode,
} from '../types';

const API_BASE = '/api';

export const apiClient = {
  async getStatus(): Promise<SystemStatus> {
    const res = await fetch(`${API_BASE}/status`);
    if (!res.ok) throw new Error(`Status check failed: ${res.statusText}`);
    return res.json();
  },

  async getScenarios(): Promise<Record<string, ScenarioInfo>> {
    const res = await fetch(`${API_BASE}/scenarios`);
    if (!res.ok) throw new Error(`Failed to load scenarios: ${res.statusText}`);
    return res.json();
  },

  async runSimulation(
    scenario: string = 'extreme',
    rainfall?: RainfallPoint[],
    durationMinutes: number = 180,
    engineMode: EngineMode = 'physics'
  ): Promise<SimulationResponse> {
    const body: any = {
      scenario,
      duration_minutes: durationMinutes,
      engine_mode: engineMode,
    };
    if (rainfall && rainfall.length > 0) {
      body.rainfall = rainfall;
    }

    const res = await fetch(`${API_BASE}/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!res.ok) throw new Error(`Simulation failed: ${res.statusText}`);
    return res.json();
  },

  async getFloodMap(timestep: number = 60): Promise<any> {
    const res = await fetch(`${API_BASE}/flood-map?timestep=${timestep}`);
    if (!res.ok) throw new Error(`Failed to load flood map: ${res.statusText}`);
    return res.json();
  },

  async getDrainageNetwork(): Promise<any> {
    const res = await fetch(`${API_BASE}/drainage`);
    if (!res.ok) throw new Error(`Failed to load drainage network: ${res.statusText}`);
    return res.json();
  },

  async getRoute(
    origin: [number, number],
    destination: [number, number],
    timestep: number = 60,
    mode: string = 'car'
  ): Promise<RouteResponse> {
    const res = await fetch(`${API_BASE}/route`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        origin,
        destination,
        timestep_minutes: timestep,
        mode,
      }),
    });

    if (!res.ok) throw new Error(`Routing failed: ${res.statusText}`);
    return res.json();
  },

  async validateSimulation(timestep: number = 90): Promise<ValidationMetrics> {
    const res = await fetch(`${API_BASE}/validate?timestep=${timestep}`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`Validation failed: ${res.statusText}`);
    return res.json();
  },

  async trainMLModel(epochs: number = 120, numStorms: number = 10): Promise<MLTrainingResponse> {
    const res = await fetch(`${API_BASE}/train`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        epochs,
        num_storm_scenarios: numStorms,
      }),
    });
    if (!res.ok) throw new Error(`Model training failed: ${res.statusText}`);
    return res.json();
  },

  async getMLStatus(): Promise<any> {
    const res = await fetch(`${API_BASE}/ml-status`);
    if (!res.ok) throw new Error(`Failed to get ML status: ${res.statusText}`);
    return res.json();
  },

  async searchLocations(query: string): Promise<LocationSearchResult[]> {
    const res = await fetch(`${API_BASE}/search-locations?q=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error(`Search failed: ${res.statusText}`);
    return res.json();
  },
};
