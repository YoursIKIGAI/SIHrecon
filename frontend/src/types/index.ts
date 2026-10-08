export type RiskLevel = 'Safe' | 'Minor' | 'Moderate' | 'Severe' | 'Critical';
export type EngineMode = 'physics' | 'ml_surrogate';
export type BasemapType = 'dark' | 'satellite' | 'streets' | 'topo';

export interface RainfallPoint {
  minutes: number;
  rainfall_mm_hr: number;
}

export interface ScenarioInfo {
  id: string;
  name: string;
  description: string;
  forecast: RainfallPoint[];
}

export interface TimestepSummary {
  minutes: number;
  timestamp: string;
  rainfall_mm_hr: number;
  flooded_roads_count: number;
  critical_zones_count: number;
  max_depth_cm: number;
  mean_depth_cm: number;
  overflow_nodes_count: number;
  total_surface_volume_m3: number;
  total_drainage_volume_m3: number;
}

export interface FloodedRoadSegment {
  road_id: string;
  name: string;
  water_depth_cm: number;
  risk_level: RiskLevel;
  length_m: number;
  coordinates: [number, number][]; // [lon, lat]
  is_blocked: boolean;
}

export interface DrainNodeStatus {
  node_id: string;
  name: string;
  type: 'inlet' | 'manhole' | 'junction' | 'outfall';
  lat: number;
  lon: number;
  elevation_m: number;
  storage_capacity_m3: number;
  current_water_m3: number;
  is_overflowing: boolean;
  overflow_rate_m3_s: number;
  street_location: string;
}

export interface SimulationResponse {
  execution_time_ms: number;
  scenario: string;
  engine_mode: EngineMode;
  duration_minutes: number;
  timesteps: TimestepSummary[];
  road_predictions: Record<number, FloodedRoadSegment[]>;
  overflow_nodes: Record<number, DrainNodeStatus[]>;
  grid_bounds: {
    min_lat: number;
    max_lat: number;
    min_lon: number;
    max_lon: number;
  };
  grid_resolution: {
    rows: number;
    cols: number;
  };
  radar_reflectivity_dbz?: number;
}

export interface RouteSegmentDetail {
  road_id: string;
  name: string;
  length_m: number;
  water_depth_cm: number;
  risk_level: RiskLevel;
  coordinates: [number, number][];
}

export interface RouteOption {
  route_type: 'normal' | 'flood_safe';
  coordinates: [number, number][];
  distance_km: number;
  estimated_time_minutes: number;
  flood_risk: string;
  max_water_depth_cm: number;
  flooded_segments_count: number;
  segments: RouteSegmentDetail[];
}

export interface RouteResponse {
  normal_route: RouteOption;
  safe_route: RouteOption;
  distance_difference_km: number;
  time_difference_minutes: number;
  avoided_flooded_roads: number;
  timestep_minutes: number;
  is_rerouted: boolean;
  summary: string;
}

export interface ValidationMetrics {
  dataset_type: string;
  num_samples: number;
  precision: number;
  recall: number;
  f1_score: number;
  rmse_depth_cm: number;
  confusion_matrix: {
    true_positive_cells: number;
    false_positive_cells: number;
    false_negative_cells: number;
    true_negative_cells: number;
  };
  status_label: string;
  notes: string;
}

export interface MLTrainingResponse {
  status: string;
  r2_score: number;
  rmse_depth_cm: number;
  mae_depth_cm: number;
  training_time_ms: number;
  train_samples: number;
  val_samples: number;
  feature_importances: Record<string, number>;
  training_history: {
    epoch: number;
    train_loss: number;
    val_loss: number;
    val_rmse: number;
    r2_score: number;
  }[];
  trained_at: string;
}

export interface LocationSearchResult {
  id: string;
  name: string;
  lat: number;
  lon: number;
  category: string;
  elevation_m: number;
}

export interface SystemStatus {
  status: string;
  service: string;
  version: string;
  engine_ready: boolean;
  ml_model_trained: boolean;
  grid: {
    rows: number;
    cols: number;
    cell_area_m2: number;
    bounds: {
      min_lat: number;
      max_lat: number;
      min_lon: number;
      max_lon: number;
    };
  };
  network: {
    road_nodes: number;
    road_edges: number;
    drain_nodes: number;
    drain_edges: number;
  };
}
