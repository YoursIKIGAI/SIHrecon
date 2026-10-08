import numpy as np
from typing import Tuple

class RunoffModel:
    """
    Computes hydrological runoff volume for each DEM grid cell based on
    rainfall intensity, land imperviousness, and initial soil infiltration.
    """

    def __init__(self, rows: int, cols: int, cell_area_m2: float):
        self.rows = rows
        self.cols = cols
        self.cell_area_m2 = cell_area_m2

        # Urban land use runoff coefficient C (Rational method / SCS curve approach)
        # Commercial / road grid cells: ~0.85 - 0.90
        # Eastern hills / greener buffer: ~0.60 - 0.70
        col_grid, _ = np.meshgrid(np.arange(cols), np.arange(rows))
        # West is heavily paved urban center (C ~ 0.85), East is suburban/hillside (C ~ 0.65)
        self.runoff_coefficient = 0.85 - 0.20 * (col_grid / (cols - 1))
        self.runoff_coefficient = np.clip(self.runoff_coefficient, 0.55, 0.92).astype(np.float32)

        # Soil / depression storage absorption capacity (mm/hr)
        self.infiltration_rate_mm_hr = 4.0

    def compute_runoff_volume_m3(
        self,
        rainfall_grid_mm_hr: np.ndarray,
        timestep_seconds: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculates runoff volume (m3) and effective runoff depth (mm) generated in this timestep.
        
        Args:
            rainfall_grid_mm_hr: 2D array of rainfall intensity in mm/hr
            timestep_seconds: duration of time step in seconds (e.g. 1800s for 30 min)
            
        Returns:
            runoff_volume_m3: 2D array of water volume added to surface
            effective_runoff_mm: 2D array of effective runoff depth in mm
        """
        # Net rainfall exceeding initial infiltration rate
        net_intensity_mm_hr = np.maximum(0.0, rainfall_grid_mm_hr - self.infiltration_rate_mm_hr)

        # Duration in hours
        duration_hr = timestep_seconds / 3600.0

        # Effective runoff depth (mm) = C * (Net Intensity * duration_hr)
        effective_runoff_mm = self.runoff_coefficient * (net_intensity_mm_hr * duration_hr)

        # Convert mm to meters: mm / 1000
        depth_m = effective_runoff_mm / 1000.0

        # Volume (m3) = depth (m) * cell_area (m2)
        runoff_volume_m3 = (depth_m * self.cell_area_m2).astype(np.float32)

        return runoff_volume_m3, effective_runoff_mm.astype(np.float32)
