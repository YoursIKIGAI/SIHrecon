import numpy as np
from typing import Tuple, List, Dict, Any

class SurfaceFlowModel:
    """
    DEM-based hydrodynamic surface flow model using D8 flow direction and
    topological sorting for vectorized water routing across urban terrain.
    Precomputes slopes, flow vectors, and depression basins.
    """

    def __init__(self, dem: np.ndarray, cell_width_m: float, cell_height_m: float):
        self.dem = dem.astype(np.float32)
        self.rows, self.cols = dem.shape
        self.cell_width_m = cell_width_m
        self.cell_height_m = cell_height_m
        self.cell_area_m2 = cell_width_m * cell_height_m

        # 8-directional neighbor offsets (dy, dx, distance)
        # N, NE, E, SE, S, SW, W, NW
        diag_dist = np.sqrt(cell_width_m**2 + cell_height_m**2)
        self.neighbors = [
            (-1, 0, cell_height_m),
            (-1, 1, diag_dist),
            (0, 1, cell_width_m),
            (1, 1, diag_dist),
            (1, 0, cell_height_m),
            (1, -1, diag_dist),
            (0, -1, cell_width_m),
            (-1, -1, diag_dist),
        ]

        # Precompute flow directions and topological sort order
        self._precompute_flow_geometry()

    def _precompute_flow_geometry(self):
        """
        Precomputes:
        1. Downhill target cell (r_to, c_to) for each cell (D8 steepest descent).
        2. Steepest slope.
        3. Depression (sink) masks where no lower neighbor exists.
        4. Topological sort order (descending elevation) for single-pass upstream-to-downstream routing.
        """
        self.downhill_target_r = np.full((self.rows, self.cols), -1, dtype=np.int32)
        self.downhill_target_c = np.full((self.rows, self.cols), -1, dtype=np.int32)
        self.steepest_slope = np.zeros((self.rows, self.cols), dtype=np.float32)
        self.is_sink = np.zeros((self.rows, self.cols), dtype=bool)

        for r in range(self.rows):
            for c in range(self.cols):
                curr_elev = self.dem[r, c]
                max_slope = 0.0
                best_nr, best_nc = -1, -1

                for dr, dc, dist in self.neighbors:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < self.rows and 0 <= nc < self.cols:
                        n_elev = self.dem[nr, nc]
                        drop = curr_elev - n_elev
                        if drop > 0:
                            slope = drop / dist
                            if slope > max_slope:
                                max_slope = slope
                                best_nr, best_nc = nr, nc

                if best_nr != -1:
                    self.downhill_target_r[r, c] = best_nr
                    self.downhill_target_c[r, c] = best_nc
                    self.steepest_slope[r, c] = max_slope
                else:
                    self.is_sink[r, c] = True

        # Precompute indices sorted by descending elevation
        # Flow travels strictly from higher elevations to lower elevations
        flat_indices = np.argsort(-self.dem.ravel())
        self.sorted_r = flat_indices // self.cols
        self.sorted_c = flat_indices % self.cols

    def route_surface_flow(
        self,
        surface_water_volume_m3: np.ndarray,
        friction_retention: float = 0.25
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Routes surface water downhill according to topography.
        
        Args:
            surface_water_volume_m3: Initial water on surface (prior ponding + new runoff)
            friction_retention: Fraction of water retained on surface due to urban surface roughness
            
        Returns:
            accumulated_water_volume_m3: Water volume in each cell after routing
            downstream_flow_volume_m3: Inflow volume each cell received from upstream
        """
        current_water = surface_water_volume_m3.copy().astype(np.float32)
        inflow_tracker = np.zeros_like(current_water)

        # Iterate through cells in topological order (highest to lowest)
        for idx in range(len(self.sorted_r)):
            r = self.sorted_r[idx]
            c = self.sorted_c[idx]
            tr = self.downhill_target_r[r, c]
            tc = self.downhill_target_c[r, c]

            # If not a sink and has a downhill neighbor
            if tr != -1 and tc != -1:
                water = current_water[r, c]
                if water > 0.0:
                    # Flow rate proportional to slope and mobile fraction
                    slope = self.steepest_slope[r, c]
                    flow_fraction = min(0.70, max(0.15, slope * 15.0)) * (1.0 - friction_retention)
                    transferred_vol = water * flow_fraction

                    current_water[r, c] -= transferred_vol
                    current_water[tr, tc] += transferred_vol
                    inflow_tracker[tr, tc] += transferred_vol

        return current_water, inflow_tracker

    def get_depressions(self) -> List[Dict[str, Any]]:
        """Identify significant depression zones and their characteristics."""
        sinks = []
        sink_indices = np.argwhere(self.is_sink)
        for r, c in sink_indices:
            sinks.append({
                "grid_r": int(r),
                "grid_c": int(c),
                "elevation_m": float(self.dem[r, c]),
                "lat": float(self.dem[r, c]), # will be mapped
            })
        return sinks
