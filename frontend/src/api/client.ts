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
  OfficerAlert,
  HistoricalEventInfo,
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
    engineMode: EngineMode = 'physics',
    cityKey?: string
  ): Promise<SimulationResponse> {
    const body: any = {
      scenario,
      duration_minutes: durationMinutes,
      engine_mode: engineMode,
      city_key: cityKey,
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

  // Dedicated Historical Simulation Replay Mode
  async getHistoricalScenarios(cityKey?: string): Promise<HistoricalEventInfo[]> {
    const url = cityKey ? `${API_BASE}/scenarios/historical?city_key=${encodeURIComponent(cityKey)}` : `${API_BASE}/scenarios/historical`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to load historical scenarios: ${res.statusText}`);
    return res.json();
  },

  async runHistoricalSimulation(
    cityKey: string,
    eventId: string,
    durationMinutes: number = 180
  ): Promise<SimulationResponse> {
    const res = await fetch(`${API_BASE}/simulate/historical`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        city_key: cityKey,
        event_id: eventId,
        duration_minutes: durationMinutes,
        engine_mode: 'physics',
      }),
    });
    if (!res.ok) throw new Error(`Historical simulation replay failed: ${res.statusText}`);
    return res.json();
  },

  async getHistoricalObservations(cityKey?: string): Promise<any> {
    const url = cityKey ? `${API_BASE}/historical-observations?city_key=${encodeURIComponent(cityKey)}` : `${API_BASE}/historical-observations`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to load historical observations: ${res.statusText}`);
    return res.json();
  },

  async getTerrainSusceptibility(): Promise<any> {
    const res = await fetch(`${API_BASE}/terrain-susceptibility`);
    if (!res.ok) throw new Error(`Failed to load terrain susceptibility: ${res.statusText}`);
    return res.json();
  },

  // Officer Alert Dashboard Endpoints
  async getOfficerAlerts(): Promise<OfficerAlert[]> {
    const res = await fetch(`${API_BASE}/alerts`);
    if (!res.ok) throw new Error(`Failed to load officer alerts: ${res.statusText}`);
    return res.json();
  },

  async updateAlertStatus(
    alertId: string,
    status: 'active' | 'acknowledged' | 'resolved' | 'dismissed',
    notes?: string
  ): Promise<any> {
    const res = await fetch(`${API_BASE}/alerts/${encodeURIComponent(alertId)}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status,
        notes: notes || '',
      }),
    });
    if (!res.ok) throw new Error(`Failed to update alert status: ${res.statusText}`);
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
    mode: string = 'car',
    cityKey?: string
  ): Promise<RouteResponse> {
    const res = await fetch(`${API_BASE}/route`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        origin,
        destination,
        timestep_minutes: timestep,
        mode,
        city_key: cityKey,
      }),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Routing failed: ${res.statusText}`);
    }
    return res.json();
  },

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

  async searchLocations(query: string): Promise<LocationSearchResult[]> {
    const res = await fetch(`${API_BASE}/search-locations?q=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error(`Search failed: ${res.statusText}`);
    return res.json();
  },

  async getRadarFeed(
    source: string = 'imd_historical',
    apiKey?: string,
    event?: string
  ): Promise<RadarFeedResult> {
    const params = new URLSearchParams({
      source,
      event: event || '',
      api_key: apiKey || '',
    });
    const res = await fetch(`${API_BASE}/radar-feed?${params.toString()}`);
    if (!res.ok) throw new Error(`Radar feed fetch failed: ${res.statusText}`);
    return res.json();
  },

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

  getExportGeoTIFFUrl(timestep: number = 60): string {
    return `${API_BASE}/export/geotiff?timestep=${timestep}`;
  },

  getExportGeoJSONUrl(timestep: number = 60): string {
    return `${API_BASE}/export/geojson?timestep=${timestep}`;
  },
};
