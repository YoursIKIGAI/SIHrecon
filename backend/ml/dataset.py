import numpy as np
from typing import Dict, List, Tuple, Any
from ..data.city_generator import CityData, get_city_data
from ..simulation.rainfall import RainfallModule
from ..simulation.runoff import RunoffModel
from ..simulation.surface_flow import SurfaceFlowModel
from ..simulation.drainage import DrainageModel

class FloodDatasetGenerator:
    """
    Generates hydrodynamically consistent training and test datasets
    by running diverse storm parameterizations through the coupled physics engine.
    Extracts multi-scale spatial and temporal features per grid cell.
    """

    FEATURE_NAMES = [
        "rainfall_intensity_mm_hr",
        "cumulative_rainfall_mm",
        "dem_elevation_m",
        "slope",
        "is_sink",
        "dist_to_drain_m",
        "drain_capacity_m3_s",
        "upstream_inflow_proxy",
    ]

    def __init__(self, city_data: CityData = None):
        self.city = city_data if city_data is not None else get_city_data()
        self._precompute_static_spatial_features()

    def _precompute_static_spatial_features(self):
        """Precomputes static geographic features for all 2,000 DEM cells."""
        rows, cols = self.city.rows, self.city.cols
        self.elevation_feat = self.city.dem.astype(np.float32)

        # 1. Slope & Sink detection
        flow_model = SurfaceFlowModel(self.city.dem, self.city.cell_width_m, self.city.cell_height_m)
        self.slope_feat = flow_model.steepest_slope.astype(np.float32)
        self.is_sink_feat = flow_model.is_sink.astype(np.float32)

        # 2. Distance to nearest drainage inlet and nearest inlet capacity
        self.dist_to_drain_feat = np.zeros((rows, cols), dtype=np.float32)
        self.drain_cap_feat = np.zeros((rows, cols), dtype=np.float32)

        drain_coords = []
        drain_caps = []
        for nid, data in self.city.drain_nodes.items():
            r, c = data["grid_r"], data["grid_c"]
            drain_coords.append((r, c))
            drain_caps.append(data.get("storage_capacity_m3", 10.0) / 10.0)

        for r in range(rows):
            for c in range(cols):
                min_dist = float("inf")
                best_cap = 0.0
                for (dr, dc), cap in zip(drain_coords, drain_caps):
                    dist = np.sqrt(((r - dr) * self.city.cell_height_m)**2 + ((c - dc) * self.city.cell_width_m)**2)
                    if dist < min_dist:
                        min_dist = dist
                        best_cap = cap
                self.dist_to_drain_feat[r, c] = min_dist
                self.drain_cap_feat[r, c] = best_cap

        # 3. Flow accumulation / upstream proxy (cells with lower elevation accumulate more)
        max_elev = np.max(self.city.dem)
        self.upstream_proxy_feat = ((max_elev - self.city.dem) / (max_elev - np.min(self.city.dem))).astype(np.float32)

    def generate_training_data(self, num_storm_scenarios: int = 12) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Runs multiple randomized rainfall storm hydrographs to synthesize
        labeled feature matrices X (samples x features) and y (target depth in cm).
        """
        X_list = []
        y_list = []

        # Diverse rainfall storm scenarios: from moderate showers to catastrophic cloudbursts
        intensities = [20.0, 35.0, 50.0, 65.0, 80.0, 95.0, 110.0, 125.0, 140.0, 155.0, 170.0, 190.0]
        timesteps = [30, 60, 90, 120]

        runoff_model = RunoffModel(self.city.rows, self.city.cols, self.city.cell_area_m2)
        flow_model = SurfaceFlowModel(self.city.dem, self.city.cell_width_m, self.city.cell_height_m)
        drain_model = DrainageModel(self.city.drain_graph, self.city.drain_nodes, self.city.drain_edges)

        np.random.seed(1337)

        for storm_idx, peak_intensity in enumerate(intensities[:num_storm_scenarios]):
            drain_model.reset_state()
            surface_water_m3 = np.zeros((self.city.rows, self.city.cols), dtype=np.float32)
            cum_rain = 0.0

            for minute in timesteps:
                # Shape hydrograph: ramp up then gradual recession
                if minute <= 60:
                    current_rain = peak_intensity * (minute / 60.0)
                else:
                    current_rain = peak_intensity * max(0.2, 1.0 - (minute - 60) / 120.0)

                cum_rain += current_rain * 0.5  # 30 min duration
                delta_sec = 1800.0

                rain_grid = np.full((self.city.rows, self.city.cols), current_rain, dtype=np.float32)
                runoff_m3, _ = runoff_model.compute_runoff_volume_m3(rain_grid, delta_sec)
                surface_water_m3 += runoff_m3

                # Surface routing & drainage
                surface_water_m3, inflow = flow_model.route_surface_flow(surface_water_m3)
                drain_model.simulate_timestep(surface_water_m3, delta_sec)
                surface_water_m3, _ = flow_model.route_surface_flow(surface_water_m3, friction_retention=0.35)

                target_depth_cm = np.round((surface_water_m3 / self.city.cell_area_m2) * 100.0, 2)

                # Flatten features across all cells for this timestep
                for r in range(self.city.rows):
                    for c in range(self.city.cols):
                        feat_row = [
                            float(current_rain),
                            float(cum_rain),
                            float(self.elevation_feat[r, c]),
                            float(self.slope_feat[r, c]),
                            float(self.is_sink_feat[r, c]),
                            float(self.dist_to_drain_feat[r, c]),
                            float(self.drain_cap_feat[r, c]),
                            float(self.upstream_proxy_feat[r, c]),
                        ]
                        X_list.append(feat_row)
                        y_list.append(float(target_depth_cm[r, c]))

        X = np.array(X_list, dtype=np.float32)
        y = np.array(y_list, dtype=np.float32)

        stats = {
            "num_samples": len(X),
            "num_features": len(self.FEATURE_NAMES),
            "feature_names": self.FEATURE_NAMES,
            "mean_depth_cm": float(np.mean(y)),
            "max_depth_cm": float(np.max(y)),
        }

        return X, y, stats
