from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class RainfallPoint(BaseModel):
    minutes: int = Field(..., description="Minutes from simulation start (0 to 180)")
    rainfall_mm_hr: float = Field(..., description="Rainfall intensity in mm/hour")

class RainfallInput(BaseModel):
    timestamp: Optional[str] = Field(default="2026-10-08T10:00:00", description="ISO timestamp")
    scenario: Optional[str] = Field(default="extreme", description="Scenario: light, heavy, extreme, custom")
    forecast: List[RainfallPoint] = Field(default_factory=list, description="Rainfall forecast points")

class SimulationRequest(BaseModel):
    rainfall: Optional[List[RainfallPoint]] = None
    scenario: Optional[str] = "extreme"
    duration_minutes: int = 180
    soil_absorption_rate: Optional[float] = 5.0  # mm/hr infiltration capacity
    engine_mode: Optional[str] = "physics"       # "physics" or "ml_surrogate"

class LocationCoord(BaseModel):
    lat: float
    lon: float

class FloodPredictionRecord(BaseModel):
    location: LocationCoord
    timestamp: str
    water_depth_cm: float
    risk_level: str
    elevation_m: float
    grid_row: int
    grid_col: int

class FloodedRoadSegment(BaseModel):
    road_id: str
    name: str
    water_depth_cm: float
    risk_level: str
    length_m: float
    coordinates: List[List[float]]  # [[lon, lat], [lon, lat]]
    is_blocked: bool

class DrainNodeStatus(BaseModel):
    node_id: str
    name: str
    type: str  # inlet, manhole, junction, outfall
    lat: float
    lon: float
    elevation_m: float
    storage_capacity_m3: float
    current_water_m3: float
    is_overflowing: bool
    overflow_rate_m3_s: float
    street_location: str

class TimestepSummary(BaseModel):
    minutes: int
    timestamp: str
    rainfall_mm_hr: float
    flooded_roads_count: int
    critical_zones_count: int
    max_depth_cm: float
    mean_depth_cm: float
    overflow_nodes_count: int
    total_surface_volume_m3: float
    total_drainage_volume_m3: float

class SimulationResponse(BaseModel):
    execution_time_ms: float
    scenario: str
    engine_mode: str = "physics"
    duration_minutes: int
    timesteps: List[TimestepSummary]
    road_predictions: Dict[int, List[FloodedRoadSegment]]  # timestep (min) -> list of flooded roads
    overflow_nodes: Dict[int, List[DrainNodeStatus]]       # timestep (min) -> list of overflowing nodes
    grid_bounds: Dict[str, float]                          # min_lat, max_lat, min_lon, max_lon
    grid_resolution: Dict[str, int]                        # rows, cols
    radar_reflectivity_dbz: Optional[float] = 52.0

class RouteRequest(BaseModel):
    origin: List[float] = Field(..., description="[longitude, latitude]")
    destination: List[float] = Field(..., description="[longitude, latitude]")
    mode: Optional[str] = "car"
    timestep_minutes: Optional[int] = 60

class RouteSegmentDetail(BaseModel):
    road_id: str
    name: str
    length_m: float
    water_depth_cm: float
    risk_level: str
    coordinates: List[List[float]]

class RouteOption(BaseModel):
    route_type: str  # "normal" or "flood_safe"
    coordinates: List[List[float]]  # GeoJSON LineString coordinates [[lon, lat], ...]
    distance_km: float
    estimated_time_minutes: float
    flood_risk: str
    max_water_depth_cm: float
    flooded_segments_count: int
    segments: List[RouteSegmentDetail]

class RouteResponse(BaseModel):
    normal_route: RouteOption
    safe_route: RouteOption
    distance_difference_km: float
    time_difference_minutes: float
    avoided_flooded_roads: int
    timestep_minutes: int
    is_rerouted: bool
    summary: str

class ValidationMetrics(BaseModel):
    dataset_type: str
    num_samples: int
    precision: float
    recall: float
    f1_score: float
    rmse_depth_cm: float
    confusion_matrix: Dict[str, int]
    status_label: str
    notes: str

class MLTrainingRequest(BaseModel):
    epochs: int = 150
    learning_rate: float = 0.04
    num_storm_scenarios: int = 12

class MLTrainingResponse(BaseModel):
    status: str
    r2_score: float
    rmse_depth_cm: float
    mae_depth_cm: float
    training_time_ms: float
    train_samples: int
    val_samples: int
    feature_importances: Dict[str, float]
    training_history: List[Dict[str, Any]]
    trained_at: str

class LocationSearchResult(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    category: str
    elevation_m: float
