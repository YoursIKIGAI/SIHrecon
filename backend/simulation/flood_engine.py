import numpy as np
import time
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional

from ..data.city_generator import CityData, get_city_data
from ..data.city_configs import get_city_config, get_historical_events, get_active_city_key
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
    OfficerAlert,
)


class FloodEngine:
    """
    Core Hydrodynamic Flood Simulation Engine.
    Executes coupled physics pipeline:
    Rainfall -> Surface Runoff -> DEM Surface Flow Routing -> Subsurface Drainage Graph -> Flood Depth & Risk.
    Supports both High-Fidelity Physics and Trained AI/ML Surrogate Mode across multiple cities.
    """

    RISK_THRESHOLDS = {
        "Safe": (0.0, 5.0),
        "Minor": (5.0, 15.0),
        "Moderate": (15.0, 30.0),
        "Severe": (30.0, 50.0),
        "Critical": (50.0, 9999.0),
    }

    def __init__(self, city_data: Optional[CityData] = None):
        self.city = city_data if city_data is not None else get_city_data()
        self._init_submodules()

        # ML Surrogate Model & Precomputed Static Features
        self.ml_model = get_ml_model()
        self.dataset_gen = FloodDatasetGenerator(self.city)

        if not self.ml_model.is_trained:
            X, y, _ = self.dataset_gen.generate_training_data(num_storm_scenarios=8)
            self.ml_model.train(X, y, epochs=100)

        # Cached simulation state
        self.last_result: Optional[SimulationResponse] = None
        self.cached_depth_grids: Dict[int, np.ndarray] = {}  # timestep (min) -> depth_cm grid
        self.cached_road_states: Dict[int, List[FloodedRoadSegment]] = {}
        self.cached_overflow_nodes: Dict[int, List[DrainNodeStatus]] = {}
        self.active_alerts: List[OfficerAlert] = []

        # Warm-up simulation for active city
        self.run_simulation(scenario="extreme", duration_minutes=180, engine_mode="physics", simulation_mode="live")

    def _init_submodules(self):
        """Initializes hydrologic submodels bound to active city terrain and drainage."""
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

    def set_city(self, city_data: CityData):
        """Re-binds engine to a different city and clears stale caches."""
        self.city = city_data
        self._init_submodules()
        self.dataset_gen = FloodDatasetGenerator(self.city)
        self.cached_depth_grids.clear()
        self.cached_road_states.clear()
        self.cached_overflow_nodes.clear()
        self.active_alerts.clear()
        self.last_result = None

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
        """Marshall-Palmer relation: Z = 200 * R^1.6 -> dBZ."""
        if intensity_mm_hr <= 0.1:
            return 10.0
        z = 200.0 * (intensity_mm_hr ** 1.6)
        dbz = 10.0 * np.log10(max(1.0, z))
        return round(float(np.clip(dbz, 15.0, 68.0)), 1)

    def generate_officer_alerts(
        self,
        depth_cm: np.ndarray,
        road_segments: List[FloodedRoadSegment],
        overflow_nodes: List[DrainNodeStatus],
        timestep_minutes: int,
        intensity_mm_hr: float,
        simulation_mode: str = "live"
    ) -> List[OfficerAlert]:
        """
        Generates evidence-backed officer alerts based on active simulation outcomes.
        Maintains status separately so officers can acknowledge/resolve.
        """
        alerts: List[OfficerAlert] = []
        is_test = (simulation_mode != "live")
        base_time = datetime(2026, 10, 8, 10, 0, 0) + timedelta(minutes=timestep_minutes)
        ts_str = base_time.isoformat()
        city_prefix = self.city.city_key.upper()[:3]
        alert_idx = 1

        # Alert Rule 1: Extreme Cloudburst Precipitation Trigger
        if intensity_mm_hr >= 100.0:
            alerts.append(OfficerAlert(
                alert_id=f"ALT_{city_prefix}_RAIN_{timestep_minutes}M",
                city=self.city.city_name,
                locality=f"{self.city.city_name} Metro Catchment",
                severity="Critical",
                timestamp=ts_str,
                trigger_condition=f"Rainfall intensity reached {intensity_mm_hr:.1f} mm/hr (exceeds cloudburst limit of 100 mm/hr)",
                supporting_data=f"Radar reflectivity {self.rainfall_to_dbz(intensity_mm_hr)} dBZ. High runoff volume imminent.",
                confidence="High (Meteorological sensor/hydrograph)",
                recommended_action="Sound municipal siren; alert NDRF/SDRF battallions; activate emergency pumping stations.",
                status="active",
                is_test_alert=is_test,
            ))
            alert_idx += 1

        # Alert Rule 2: Impassable Roadway Cut-offs (>40cm water)
        blocked_roads = [r for r in road_segments if r.water_depth_cm > 40.0]
        for r in blocked_roads[:4]:
            alerts.append(OfficerAlert(
                alert_id=f"ALT_{city_prefix}_ROAD_{r.road_id}_{timestep_minutes}M",
                city=self.city.city_name,
                locality=r.name,
                severity="Critical",
                timestamp=ts_str,
                trigger_condition=f"Water depth {r.water_depth_cm} cm exceeds impassable vehicle safety threshold (>40 cm)",
                supporting_data=f"Segment {r.name} length {r.length_m}m submerged. Risk: {r.risk_level}.",
                confidence="High (Topographic ponding & DEM simulation)",
                recommended_action=f"Deploy traffic barricades at {r.name}; divert ambulances and civilian traffic to elevated routes.",
                status="active",
                is_test_alert=is_test,
            ))
            alert_idx += 1

        # Alert Rule 3: High-Hazard Roads (20cm - 40cm water)
        severe_roads = [r for r in road_segments if 20.0 < r.water_depth_cm <= 40.0]
        for r in severe_roads[:3]:
            alerts.append(OfficerAlert(
                alert_id=f"ALT_{city_prefix}_SEV_{r.road_id}_{timestep_minutes}M",
                city=self.city.city_name,
                locality=r.name,
                severity="High",
                timestamp=ts_str,
                trigger_condition=f"Water depth {r.water_depth_cm} cm threatens low-clearance passenger cars (20-40 cm hazard)",
                supporting_data=f"Hazard penalty factor 15.0x applied. High splash risk.",
                confidence="High (Hydrodynamic physics model)",
                recommended_action=f"Restrict two-wheeler and sedan traffic on {r.name}; permit heavy rescue vehicles only.",
                status="active",
                is_test_alert=is_test,
            ))
            alert_idx += 1

        # Alert Rule 4: Subsurface Drainage Surcharge Eruptions
        severe_overflows = [n for n in overflow_nodes if n.overflow_rate_m3_s >= 1.0]
        for node in severe_overflows[:3]:
            alerts.append(OfficerAlert(
                alert_id=f"ALT_{city_prefix}_DRAIN_{node.node_id}_{timestep_minutes}M",
                city=self.city.city_name,
                locality=node.street_location,
                severity="High",
                timestamp=ts_str,
                trigger_condition=f"Manhole surcharge overflow rate {node.overflow_rate_m3_s} m³/s with 100% capacity saturation",
                supporting_data=f"Node {node.name} chamber storage {node.storage_capacity_m3} m³ fully surcharged. Water erupting onto surface.",
                confidence="High (Pipe network graph simulation)",
                recommended_action=f"Deploy de-watering suction pumps to relieve chamber at {node.street_location}.",
                status="active",
                is_test_alert=is_test,
            ))
            alert_idx += 1

        # Alert Rule 5: Widespread Inundation Advisory
        flooded_count = sum(1 for r in road_segments if r.water_depth_cm >= 10.0)
        if flooded_count >= 5:
            alerts.append(OfficerAlert(
                alert_id=f"ALT_{city_prefix}_GEN_{timestep_minutes}M",
                city=self.city.city_name,
                locality=f"{self.city.city_name} Multi-Sector Network",
                severity="Moderate",
                timestamp=ts_str,
                trigger_condition=f"Widespread waterlogging: {flooded_count} road segments concurrently inundated (depth >=10 cm)",
                supporting_data=f"Max surface depth: {float(np.max(depth_cm)):.1f} cm across terrain depressions.",
                confidence="Moderate (Network-wide aggregation)",
                recommended_action="Issue city-wide traffic advisory; urge commuters to utilize flood-safe navigation recommendations.",
                status="active",
                is_test_alert=is_test,
            ))

        return alerts

    def update_alert_status(self, alert_id: str, new_status: str) -> bool:
        """Allows officers to acknowledge, resolve, or dismiss alerts."""
        for a in self.active_alerts:
            if a.alert_id == alert_id:
                a.status = new_status
                return True
        return False

    def run_simulation(
        self,
        scenario: str = "extreme",
        custom_forecast: Optional[List[RainfallPoint]] = None,
        duration_minutes: int = 180,
        soil_absorption_rate: float = 4.0,
        engine_mode: str = "physics",
        city_key: Optional[str] = None,
        simulation_mode: str = "live",
        event_id: Optional[str] = None,
    ) -> SimulationResponse:
        """
        Runs city-independent 0-3 hour flood simulation.
        Supports both Coupled Hydrodynamic Physics and Pure NumPy ML Surrogate.
        """
        start_time = time.perf_counter()

        # Check if city switch is requested
        if city_key and city_key.lower().strip() != self.city.city_key:
            target_city = get_city_data(city_key=city_key)
            self.set_city(target_city)

        # Update soil absorption rate
        self.runoff_model.infiltration_rate_mm_hr = soil_absorption_rate

        # Resolve rainfall forecast points
        effective_scenario = scenario
        forecast_points = []

        if custom_forecast and len(custom_forecast) > 0:
            forecast_points = custom_forecast
            effective_scenario = "custom"
        elif event_id:
            # Historical event requested
            hist_events = get_historical_events(self.city.city_key)
            target_event = next((e for e in hist_events if e["id"] == event_id), None)
            if target_event and "json_file" in target_event and os.path.exists(target_event["json_file"]):
                try:
                    with open(target_event["json_file"], "r") as f:
                        data = json.load(f)
                    forecast_points = [RainfallPoint(**p) for p in data.get("forecast", [])]
                    effective_scenario = event_id
                except Exception:
                    forecast_points = self.rainfall_module.get_scenario_forecast(scenario)
            else:
                forecast_points = self.rainfall_module.get_scenario_forecast(scenario)
        else:
            forecast_points = self.rainfall_module.get_scenario_forecast(scenario)

        # Simulation timesteps: 0, 30, 60, 90, 120, 180
        timestep_minutes = [0, 30, 60, 90, 120, 180]
        timestep_minutes = [m for m in timestep_minutes if m <= duration_minutes]

        base_time = datetime(2026, 10, 8, 10, 0, 0)

        # Reset states
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
                # -----------------------------------------------
                # AI / ML SURROGATE INFERENCE (Pure NumPy MLP)
                # -----------------------------------------------
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
                                verification_status=ndata.get("verification_status", "verified"),
                                is_bottleneck=ndata.get("is_bottleneck", False),
                            )
                        )
                drain_stats = {"total_intake_m3": float(intensity_mm_hr * 400.0)}

            else:
                # -----------------------------------------------
                # COUPLED HYDRODYNAMIC PHYSICS ENGINE
                # -----------------------------------------------
                if delta_min > 0:
                    runoff_vol_m3, _ = self.runoff_model.compute_runoff_volume_m3(
                        rain_grid_mm_hr, delta_sec
                    )
                    surface_water_volume_m3 += runoff_vol_m3

                    surface_water_volume_m3, _ = self.surface_flow_model.route_surface_flow(
                        surface_water_volume_m3
                    )

                    _, overflow_nodes, drain_stats = self.drainage_model.simulate_timestep(
                        surface_water_volume_m3, delta_sec
                    )

                    surface_water_volume_m3, _ = self.surface_flow_model.route_surface_flow(
                        surface_water_volume_m3, friction_retention=0.40
                    )
                else:
                    overflow_nodes = []
                    drain_stats = {"total_intake_m3": 0.0, "total_overflow_m3": 0.0, "total_discharged_m3": 0.0}

                depth_m = surface_water_volume_m3 / self.city.cell_area_m2
                depth_cm = np.round(depth_m * 100.0, 1)

            # Cache results
            self.cached_depth_grids[minute] = depth_cm.copy()
            self.cached_overflow_nodes[minute] = overflow_nodes
            overflow_nodes_dict[minute] = overflow_nodes

            # Road network depth assignment
            road_segments_status = self._compute_road_depths(depth_cm)
            self.cached_road_states[minute] = road_segments_status
            road_predictions[minute] = road_segments_status

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

        # Generate Officer Alerts for the peak/selected timestep
        peak_minute = 90 if 90 in self.cached_depth_grids else (max(self.cached_depth_grids.keys()) if self.cached_depth_grids else 60)
        peak_depth_grid = self.cached_depth_grids.get(peak_minute, np.zeros((self.city.rows, self.city.cols)))
        peak_roads = self.cached_road_states.get(peak_minute, [])
        peak_overflows = self.cached_overflow_nodes.get(peak_minute, [])

        self.active_alerts = self.generate_officer_alerts(
            depth_cm=peak_depth_grid,
            road_segments=peak_roads,
            overflow_nodes=peak_overflows,
            timestep_minutes=peak_minute,
            intensity_mm_hr=peak_intensity,
            simulation_mode=simulation_mode
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Retrieve count of verified field points for this city
        hist_events = get_historical_events(self.city.city_key)
        obs_count = hist_events[0]["observation_points_count"] if hist_events else 12

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
            city_key=self.city.city_key,
            city_name=self.city.city_name,
            simulation_mode=simulation_mode,
            event_id=event_id,
            alerts=self.active_alerts,
            historical_observations_count=obs_count,
        )
        self.last_result = response
        return response

    def _compute_road_depths(self, depth_cm_grid: np.ndarray) -> List[FloodedRoadSegment]:
        """Calculates water depth for each road segment in the active network."""
        road_statuses = []

        for edge in self.city.road_edges:
            if edge.get("is_elevated", False):
                road_depth = 0.0
            else:
                sampled_depths = [float(depth_cm_grid[r, c]) for (r, c) in edge["cells"]]
                road_depth = float(np.max(sampled_depths)) if sampled_depths else 0.0

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
                    is_blocked=is_blocked,
                    elevation_m=edge.get("avg_elevation_m"),
                    speed_kmh=edge.get("speed_kmh", 40.0),
                )
            )

        return road_statuses

    def get_flood_geojson(self, timestep_minute: int = 60) -> Dict[str, Any]:
        """Generates GeoJSON FeatureCollection of flood polygons and road depths."""
        if timestep_minute not in self.cached_depth_grids:
            available = sorted(list(self.cached_depth_grids.keys()))
            if not available:
                self.run_simulation()
                available = sorted(list(self.cached_depth_grids.keys()))
            timestep_minute = min(available, key=lambda t: abs(t - timestep_minute))

        depth_grid = self.cached_depth_grids[timestep_minute]
        features = []

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
            "city_key": self.city.city_key,
            "features": features
        }

    def get_prediction_records(self, timestep_minute: int = 60) -> List[FloodPredictionRecord]:
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


# Multi-City Flood Engine Registry
_engine_instances: Dict[str, FloodEngine] = {}


def get_flood_engine(city_key: Optional[str] = None, force_new: bool = False) -> FloodEngine:
    """
    Returns FloodEngine for requested city (or active city).
    Guarantees city independence and prevents state contamination.
    """
    global _engine_instances
    target_key = (city_key or get_active_city_key()).lower().strip()
    if target_key not in ["mumbai", "delhi", "chennai"]:
        target_key = "mumbai"

    if force_new or target_key not in _engine_instances:
        city = get_city_data(city_key=target_key)
        _engine_instances[target_key] = FloodEngine(city)

    return _engine_instances[target_key]


def reset_flood_engine(city_key: Optional[str] = None):
    """Resets cached flood engines."""
    global _engine_instances
    if city_key:
        _engine_instances.pop(city_key.lower().strip(), None)
    else:
        _engine_instances.clear()
