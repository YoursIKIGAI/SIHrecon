import numpy as np
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional

from ..data.city_generator import CityData, get_city_data
from .rainfall import RainfallModule
from .runoff import RunoffModel
from .surface_flow import SurfaceFlowModel
from .drainage import DrainageModel
from ..ml.model import get_ml_model
from ..ml.dataset import FloodDatasetGenerator
from ..models.schemas import (
    RainfallPoint,
    SimulationRequest,
    SimulationResponse,
    TimestepSummary,
    FloodedRoadSegment,
    DrainNodeStatus,
    FloodPredictionRecord,
    LocationCoord,
)

class FloodEngine:
    """
    Core Hydrodynamic Flood Simulation Engine.
    Executes coupled physics pipeline:
    Rainfall -> Surface Runoff -> DEM Surface Flow Routing -> Subsurface Drainage Graph -> Flood Depth & Risk.
    Supports both High-Fidelity Physics and Trained AI/ML Surrogate Mode.
    """

    # Configurable risk thresholds (in cm)
    RISK_THRESHOLDS = {
        "Safe": (0.0, 5.0),
        "Minor": (5.0, 15.0),
        "Moderate": (15.0, 30.0),
        "Severe": (30.0, 50.0),
        "Critical": (50.0, 9999.0),
    }

    def __init__(self, city_data: Optional[CityData] = None):
        self.city = city_data if city_data is not None else get_city_data()
        self.rainfall_module = RainfallModule()
        self.runoff_model = RunoffModel(
            rows=self.city.rows,
            cols=self.city.cols,
            cell_area_m2=self.city.cell_area_m2
        )
        self.surface_flow_model = SurfaceFlowModel(
            dem=self.city.dem,
            cell_width_m=self.city.cell_width_m,
            cell_height_m=self.city.cell_height_m
        )
        self.drainage_model = DrainageModel(
            drain_graph=self.city.drain_graph,
            drain_nodes=self.city.drain_nodes,
            drain_edges=self.city.drain_edges
        )

        # ML Surrogate Model & Precomputed Static Features
        self.ml_model = get_ml_model()
        self.dataset_gen = FloodDatasetGenerator(self.city)

        # Pre-train ML model if not already saved
        if not self.ml_model.is_trained:
            X, y, _ = self.dataset_gen.generate_training_data(num_storm_scenarios=8)
            self.ml_model.train(X, y, epochs=100)

        # Cached simulation state
        self.last_result: Optional[SimulationResponse] = None
        self.cached_depth_grids: Dict[int, np.ndarray] = {}  # timestep (min) -> depth_cm grid
        self.cached_road_states: Dict[int, List[FloodedRoadSegment]] = {}
        self.cached_overflow_nodes: Dict[int, List[DrainNodeStatus]] = {}

        # Initial warm-up simulation
        self.run_simulation(scenario="extreme", duration_minutes=180, engine_mode="physics")

    @staticmethod
    def classify_risk(depth_cm: float) -> str:
        """Classify flood depth into risk levels."""
        if depth_cm < 5.0:
            return "Safe"
        elif depth_cm < 15.0:
            return "Minor"
        elif depth_cm < 30.0:
            return "Moderate"
        elif depth_cm < 50.0:
            return "Severe"
        else:
            return "Critical"

    @staticmethod
    def rainfall_to_dbz(intensity_mm_hr: float) -> float:
        """
        Converts rainfall rate R (mm/hr) to Doppler Radar Reflectivity Factor (dBZ)
        using the empirical Marshall-Palmer relation: Z = 200 * R^1.6
        """
        if intensity_mm_hr <= 0.1:
            return 10.0
        z = 200.0 * (intensity_mm_hr ** 1.6)
        dbz = 10.0 * np.log10(max(1.0, z))
        return round(float(np.clip(dbz, 15.0, 68.0)), 1)

    def run_simulation(
        self,
        scenario: str = "extreme",
        custom_forecast: Optional[List[RainfallPoint]] = None,
        duration_minutes: int = 180,
        soil_absorption_rate: float = 4.0,
        engine_mode: str = "physics"
    ) -> SimulationResponse:
        """
        Runs the full 0-3 hour simulation dynamically.
        Supports both 'physics' and 'ml_surrogate' inference.
        """
        start_time = time.perf_counter()

        # Update soil absorption rate if provided
        self.runoff_model.infiltration_rate_mm_hr = soil_absorption_rate

        # Get rainfall forecast points
        if custom_forecast and len(custom_forecast) > 0:
            forecast_points = custom_forecast
            effective_scenario = "custom"
        else:
            forecast_points = self.rainfall_module.get_scenario_forecast(scenario)
            effective_scenario = scenario

        # Discrete timesteps to simulate: 0, 30, 60, 90, 120, 180 minutes
        timestep_minutes = [0, 30, 60, 90, 120, 180]
        timestep_minutes = [m for m in timestep_minutes if m <= duration_minutes]

        base_time = datetime(2026, 10, 8, 10, 0, 0)

        # Clear state
        self.drainage_model.reset_state()
        self.rainfall_module.reset_storm_track(self.city.rows, self.city.cols)
        surface_water_volume_m3 = np.zeros((self.city.rows, self.city.cols), dtype=np.float32)

        self.cached_depth_grids.clear()
        self.cached_road_states.clear()
        self.cached_overflow_nodes.clear()

        timesteps_summary: List[TimestepSummary] = []
        road_predictions: Dict[int, List[FloodedRoadSegment]] = {}
        overflow_nodes_dict: Dict[int, List[DrainNodeStatus]] = {}

        prev_minute = 0
        cumulative_rainfall_mm = 0.0
        peak_intensity = 0.0

        for timestep_idx, minute in enumerate(timestep_minutes):
            delta_min = minute - prev_minute
            prev_minute = minute
            delta_sec = max(1.0, float(delta_min * 60))

            # 1. Rainfall intensity for this interval
            intensity_mm_hr = self.rainfall_module.interpolate_intensity(forecast_points, minute)
            cumulative_rainfall_mm += intensity_mm_hr * (delta_min / 60.0)
            if intensity_mm_hr > peak_intensity:
                peak_intensity = intensity_mm_hr

            rain_grid_mm_hr = self.rainfall_module.generate_spatial_grid(
                self.city.rows, self.city.cols, intensity_mm_hr, timestep_idx=timestep_idx
            )
            storm_lat, storm_lon = self.city.cell_to_lat_lon(
                int(self.rainfall_module.storm_center_r),
                int(self.rainfall_module.storm_center_c)
            )
            self.rainfall_module.record_storm_position(minute, intensity_mm_hr, storm_lat, storm_lon)

            if engine_mode == "ml_surrogate" and self.ml_model.is_trained:
                # ==========================================
                # AI / MACHINE LEARNING SURROGATE INFERENCE
                # ==========================================
                if delta_min > 0:
                    depth_cm = self.ml_model.predict_grid(
                        rainfall_intensity_mm_hr=intensity_mm_hr,
                        cumulative_rain_mm=cumulative_rainfall_mm,
                        dem_elevation=self.dataset_gen.elevation_feat,
                        slope=self.dataset_gen.slope_feat,
                        is_sink=self.dataset_gen.is_sink_feat,
                        dist_to_drain=self.dataset_gen.dist_to_drain_feat,
                        drain_cap=self.dataset_gen.drain_cap_feat,
                        upstream_proxy=self.dataset_gen.upstream_proxy_feat,
                    )
                else:
                    depth_cm = np.zeros((self.city.rows, self.city.cols), dtype=np.float32)

                # Identify overflowing manholes from predicted depth
                overflow_nodes = []
                for nid, ndata in self.city.drain_nodes.items():
                    r, c = ndata["grid_r"], ndata["grid_c"]
                    cell_d = depth_cm[r, c]
                    if cell_d >= 20.0 and ndata["type"] != "outfall":
                        overflow_rate = round(float((cell_d / 50.0) * 2.2), 2)
                        overflow_nodes.append(
                            DrainNodeStatus(
                                node_id=nid,
                                name=ndata["name"],
                                type=ndata["type"],
                                lat=ndata["lat"],
                                lon=ndata["lon"],
                                elevation_m=ndata["elevation_m"],
                                storage_capacity_m3=ndata["storage_capacity_m3"],
                                current_water_m3=ndata["storage_capacity_m3"],
                                is_overflowing=True,
                                overflow_rate_m3_s=overflow_rate,
                                street_location=ndata["street_location"],
                            )
                        )
                drain_stats = {"total_intake_m3": float(intensity_mm_hr * 400.0)}

            else:
                # ==========================================
                # COUPLED HYDRODYNAMIC PHYSICS INFERENCE
                # ==========================================
                if delta_min > 0:
                    # 2. Runoff generation
                    runoff_vol_m3, _ = self.runoff_model.compute_runoff_volume_m3(
                        rain_grid_mm_hr, delta_sec
                    )
                    surface_water_volume_m3 += runoff_vol_m3

                    # 3. DEM Surface flow routing downhill
                    surface_water_volume_m3, _ = self.surface_flow_model.route_surface_flow(
                        surface_water_volume_m3
                    )

                    # 4. Subsurface Drainage Intake & Hydraulic Routing
                    _, overflow_nodes, drain_stats = self.drainage_model.simulate_timestep(
                        surface_water_volume_m3, delta_sec
                    )

                    # 5. Secondary surface redistribution of overflow in low areas
                    surface_water_volume_m3, _ = self.surface_flow_model.route_surface_flow(
                        surface_water_volume_m3, friction_retention=0.40
                    )
                else:
                    overflow_nodes = []
                    drain_stats = {"total_intake_m3": 0.0, "total_overflow_m3": 0.0, "total_discharged_m3": 0.0}

                # Convert surface water volume to depth (cm)
                depth_m = surface_water_volume_m3 / self.city.cell_area_m2
                depth_cm = np.round(depth_m * 100.0, 1)

            # Cache results
            self.cached_depth_grids[minute] = depth_cm.copy()
            self.cached_overflow_nodes[minute] = overflow_nodes
            overflow_nodes_dict[minute] = overflow_nodes

            # Map water depths onto road network
            road_segments_status = self._compute_road_depths(depth_cm)
            self.cached_road_states[minute] = road_segments_status
            road_predictions[minute] = road_segments_status

            # Summary metrics
            flooded_roads_count = sum(1 for r in road_segments_status if r.water_depth_cm >= 5.0)
            critical_zones_count = int(np.sum(depth_cm >= 50.0))
            max_depth = float(np.max(depth_cm))
            mean_depth = float(np.mean(depth_cm))

            step_time = base_time + timedelta(minutes=minute)
            summary = TimestepSummary(
                minutes=minute,
                timestamp=step_time.isoformat(),
                rainfall_mm_hr=round(intensity_mm_hr, 1),
                flooded_roads_count=flooded_roads_count,
                critical_zones_count=critical_zones_count,
                max_depth_cm=round(max_depth, 1),
                mean_depth_cm=round(mean_depth, 1),
                overflow_nodes_count=len(overflow_nodes),
                total_surface_volume_m3=round(float(np.sum(depth_cm / 100.0 * self.city.cell_area_m2)), 1),
                total_drainage_volume_m3=round(float(drain_stats.get("total_intake_m3", 0.0)), 1)
            )
            timesteps_summary.append(summary)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        response = SimulationResponse(
            execution_time_ms=round(elapsed_ms, 2),
            scenario=effective_scenario,
            engine_mode=engine_mode,
            duration_minutes=duration_minutes,
            timesteps=timesteps_summary,
            road_predictions=road_predictions,
            overflow_nodes=overflow_nodes_dict,
            grid_bounds={
                "min_lat": self.city.min_lat,
                "max_lat": self.city.max_lat,
                "min_lon": self.city.min_lon,
                "max_lon": self.city.max_lon,
            },
            grid_resolution={
                "rows": self.city.rows,
                "cols": self.city.cols,
            },
            radar_reflectivity_dbz=self.rainfall_to_dbz(peak_intensity),
            storm_track=list(self.rainfall_module.storm_track),
        )
        self.last_result = response
        return response

    def _compute_road_depths(self, depth_cm_grid: np.ndarray) -> List[FloodedRoadSegment]:
        """Calculates water depth for each road segment in the network."""
        road_statuses = []

        for edge in self.city.road_edges:
            if edge.get("is_elevated", False):
                road_depth = 0.0
            else:
                sampled_depths = [float(depth_cm_grid[r, c]) for (r, c) in edge["cells"]]
                if sampled_depths:
                    road_depth = float(np.max(sampled_depths))
                else:
                    road_depth = 0.0

            road_depth = round(road_depth, 1)
            risk = self.classify_risk(road_depth)
            is_blocked = (road_depth > 40.0)

            road_statuses.append(
                FloodedRoadSegment(
                    road_id=edge["id"],
                    name=edge["name"],
                    water_depth_cm=road_depth,
                    risk_level=risk,
                    length_m=edge["length_m"],
                    coordinates=edge["coordinates"],
                    is_blocked=is_blocked
                )
            )

        return road_statuses

    def get_flood_geojson(self, timestep_minute: int = 60) -> Dict[str, Any]:
        """
        Generates GeoJSON FeatureCollection of flood polygons and road depths for the specified timestep.
        """
        if timestep_minute not in self.cached_depth_grids:
            available = sorted(list(self.cached_depth_grids.keys()))
            if not available:
                self.run_simulation()
                available = sorted(list(self.cached_depth_grids.keys()))
            timestep_minute = min(available, key=lambda t: abs(t - timestep_minute))

        depth_grid = self.cached_depth_grids[timestep_minute]
        features = []

        # Generate grid cell flood polygons for cells with water > 3 cm
        for r in range(self.city.rows):
            for c in range(self.city.cols):
                depth = float(depth_grid[r, c])
                if depth >= 3.0:
                    lat_center, lon_center = self.city.cell_to_lat_lon(r, c)
                    dlat = (self.city.max_lat - self.city.min_lat) / (self.city.rows - 1) / 2.0
                    dlon = (self.city.max_lon - self.city.min_lon) / (self.city.cols - 1) / 2.0

                    poly_coords = [
                        [lon_center - dlon, lat_center - dlat],
                        [lon_center + dlon, lat_center - dlat],
                        [lon_center + dlon, lat_center + dlat],
                        [lon_center - dlon, lat_center + dlat],
                        [lon_center - dlon, lat_center - dlat],
                    ]

                    risk = self.classify_risk(depth)
                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [poly_coords]
                        },
                        "properties": {
                            "type": "grid_cell",
                            "row": r,
                            "col": c,
                            "elevation_m": float(self.city.dem[r, c]),
                            "water_depth_cm": depth,
                            "risk_level": risk,
                        }
                    })

        # Add road segment geometries with flood status
        road_segments = self.cached_road_states.get(timestep_minute, [])
        for road in road_segments:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": road.coordinates
                },
                "properties": {
                    "type": "road",
                    "road_id": road.road_id,
                    "name": road.name,
                    "water_depth_cm": road.water_depth_cm,
                    "risk_level": road.risk_level,
                    "is_blocked": road.is_blocked,
                    "length_m": road.length_m
                }
            })

        return {
            "type": "FeatureCollection",
            "timestep_minutes": timestep_minute,
            "features": features
        }

    def get_prediction_records(self, timestep_minute: int = 60) -> List[FloodPredictionRecord]:
        """
        Returns structured prediction records in the exact format required:
        { "location": { "lat": ..., "lon": ... }, "timestamp": ..., "water_depth_cm": 37, "risk_level": "Severe" }
        """
        if timestep_minute not in self.cached_depth_grids:
            timestep_minute = 60
        depth_grid = self.cached_depth_grids.get(timestep_minute, np.zeros((self.city.rows, self.city.cols)))

        base_time = datetime(2026, 10, 8, 10, 0, 0) + timedelta(minutes=timestep_minute)
        timestamp_str = base_time.isoformat()

        records = []
        for r in range(self.city.rows):
            for c in range(self.city.cols):
                depth = float(depth_grid[r, c])
                lat, lon = self.city.cell_to_lat_lon(r, c)
                records.append(
                    FloodPredictionRecord(
                        location=LocationCoord(lat=round(lat, 5), lon=round(lon, 5)),
                        timestamp=timestamp_str,
                        water_depth_cm=round(depth, 1),
                        risk_level=self.classify_risk(depth),
                        elevation_m=float(self.city.dem[r, c]),
                        grid_row=r,
                        grid_col=c
                    )
                )
        return records

# Singleton instance
_engine_instance = None

def get_flood_engine() -> FloodEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = FloodEngine()
    return _engine_instance
