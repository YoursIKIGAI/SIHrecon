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
  RadarFeedResult,
  CityInfo,
} from '../types';

// Use local Vite proxy / direct localhost if running locally, fallback to production backend
const API_BASE =
  typeof window !== 'undefined' &&
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? '/api'
    : 'https://sihrecon.onrender.com/api';

export const apiClient = {
  getApiBase(): string {
    return API_BASE;
  },

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

  // Fix 3: Validation with mode query parameter
  async validateSimulation(
    timestep: number = 90,
    mode: string = 'benchmark_physics'
  ): Promise<ValidationMetrics> {
    const res = await fetch(`${API_BASE}/validate?timestep=${timestep}&mode=${encodeURIComponent(mode)}`, {
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

  // Fix 5: Nominatim geocoding search
  async searchLocations(query: string): Promise<LocationSearchResult[]> {
    const res = await fetch(`${API_BASE}/search-locations?q=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error(`Search failed: ${res.statusText}`);
    return res.json();
  },

  // Fix 2: Radar feed (OpenWeatherMap or IMD historical)
  async getRadarFeed(
    source: string = 'imd_historical',
    apiKey?: string,
    event: string = 'mumbai_2005'
  ): Promise<RadarFeedResult> {
    const params = new URLSearchParams({
      source,
      event,
      api_key: apiKey || '',
    });
    const res = await fetch(`${API_BASE}/radar-feed?${params.toString()}`);
    if (!res.ok) throw new Error(`Radar feed fetch failed: ${res.statusText}`);
    return res.json();
  },

  // Fix 8: Multi-city endpoints
  async getCities(): Promise<Record<string, CityInfo>> {
    const res = await fetch(`${API_BASE}/cities`);
    if (!res.ok) throw new Error(`Failed to load cities: ${res.statusText}`);
    return res.json();
  },

  async switchCity(cityKey: string): Promise<any> {
    const res = await fetch(`${API_BASE}/switch-city?city_key=${encodeURIComponent(cityKey)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ city: cityKey, city_key: cityKey }),
    });
    if (!res.ok) throw new Error(`Switch city failed: ${res.statusText}`);
    return res.json();
  },

  // Fix 6: Background auto-update trigger
  async triggerAutoUpdate(
    enabled: boolean = true,
    intervalSeconds: number = 60,
    scenario: string = 'extreme'
  ): Promise<any> {
    const res = await fetch(`${API_BASE}/trigger-auto-update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled,
        interval_seconds: intervalSeconds,
        scenario,
      }),
    });
    if (!res.ok) throw new Error(`Auto-update trigger failed: ${res.statusText}`);
    return res.json();
  },

  // Fix 9: Export file download URLs
  getExportGeoTIFFUrl(timestep: number = 60): string {
    return `${API_BASE}/export/geotiff?timestep=${timestep}`;
  },

  getExportGeoJSONUrl(timestep: number = 60): string {
    return `${API_BASE}/export/geojson?timestep=${timestep}`;
  },
};
