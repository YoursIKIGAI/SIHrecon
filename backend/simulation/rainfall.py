import numpy as np
from typing import List, Dict, Any, Optional
import json
import csv
import io
from ..models.schemas import RainfallPoint

class RainfallModule:
    """
    Rainfall ingestion and scenario generation module.
    Handles temporal rainfall time-series, preset scenarios, and external radar/sensor ingestion.
    """

    SCENARIOS = {
        "light": {
            "name": "Light Rain (20 mm/hr)",
            "description": "Typical steady urban monsoon shower. Well within drainage design capacity.",
            "forecast": [
                {"minutes": 0, "rainfall_mm_hr": 15.0},
                {"minutes": 30, "rainfall_mm_hr": 20.0},
                {"minutes": 60, "rainfall_mm_hr": 22.0},
                {"minutes": 90, "rainfall_mm_hr": 20.0},
                {"minutes": 120, "rainfall_mm_hr": 15.0},
                {"minutes": 180, "rainfall_mm_hr": 10.0},
            ]
        },
        "heavy": {
            "name": "Heavy Rain (70 mm/hr)",
            "description": "Intense tropical convective downpour. Approaches urban drain design capacity.",
            "forecast": [
                {"minutes": 0, "rainfall_mm_hr": 35.0},
                {"minutes": 30, "rainfall_mm_hr": 65.0},
                {"minutes": 60, "rainfall_mm_hr": 80.0},
                {"minutes": 90, "rainfall_mm_hr": 70.0},
                {"minutes": 120, "rainfall_mm_hr": 45.0},
                {"minutes": 180, "rainfall_mm_hr": 25.0},
            ]
        },
        "extreme": {
            "name": "Extreme Cloudburst (120+ mm/hr)",
            "description": "Severe catastrophic cloudburst event (e.g. Mumbai 26 July style). Severely surcharges drains, causing widespread street inundation.",
            "forecast": [
                {"minutes": 0, "rainfall_mm_hr": 30.0},
                {"minutes": 30, "rainfall_mm_hr": 85.0},
                {"minutes": 60, "rainfall_mm_hr": 125.0},
                {"minutes": 90, "rainfall_mm_hr": 140.0},
                {"minutes": 120, "rainfall_mm_hr": 95.0},
                {"minutes": 180, "rainfall_mm_hr": 40.0},
            ]
        },
        "flash_flood": {
            "name": "Rapid Flash Surge",
            "description": "Sudden localized thunderstorm cell dumping massive rainfall over a short 60-minute burst.",
            "forecast": [
                {"minutes": 0, "rainfall_mm_hr": 20.0},
                {"minutes": 30, "rainfall_mm_hr": 110.0},
                {"minutes": 60, "rainfall_mm_hr": 135.0},
                {"minutes": 90, "rainfall_mm_hr": 60.0},
                {"minutes": 120, "rainfall_mm_hr": 25.0},
                {"minutes": 180, "rainfall_mm_hr": 10.0},
            ]
        }
    }

    def __init__(self):
        pass

    def get_scenario_forecast(self, scenario_key: str = "extreme") -> List[RainfallPoint]:
        """Returns rainfall forecast points for standard scenarios."""
        key = scenario_key.lower() if scenario_key else "extreme"
        scenario_data = self.SCENARIOS.get(key, self.SCENARIOS["extreme"])
        return [RainfallPoint(**pt) for pt in scenario_data["forecast"]]

    def get_available_scenarios(self) -> Dict[str, Any]:
        """List all available preset scenarios."""
        return {
            k: {
                "id": k,
                "name": v["name"],
                "description": v["description"],
                "forecast": v["forecast"]
            }
            for k, v in self.SCENARIOS.items()
        }

    def parse_csv(self, csv_content: str) -> List[RainfallPoint]:
        """
        Parses CSV input with header: minutes,rainfall_mm_hr
        """
        points = []
        reader = csv.DictReader(io.StringIO(csv_content))
        for row in reader:
            minutes = int(row.get("minutes", 0))
            rain = float(row.get("rainfall_mm_hr", 0.0))
            points.append(RainfallPoint(minutes=minutes, rainfall_mm_hr=rain))
        points.sort(key=lambda p: p.minutes)
        return points

    def interpolate_intensity(self, forecast: List[RainfallPoint], target_minute: float) -> float:
        """
        Linearly interpolates rainfall intensity (mm/hr) at a specific minute.
        """
        if not forecast:
            return 0.0
        
        times = [p.minutes for p in forecast]
        values = [p.rainfall_mm_hr for p in forecast]

        if target_minute <= times[0]:
            return values[0]
        if target_minute >= times[-1]:
            return values[-1]

        return float(np.interp(target_minute, times, values))

    def generate_spatial_grid(self, rows: int, cols: int, base_intensity_mm_hr: float) -> np.ndarray:
        """
        Future extension hook for IMD Doppler Radar spatial rainfall grids.
        Applies a localized convective storm core cell centered on the city.
        """
        grid = np.full((rows, cols), base_intensity_mm_hr, dtype=np.float32)
        # Add slight spatial variance (+-15%) across terrain to mimic real convective cells
        center_r, center_c = rows // 2, cols // 2
        r_coords, c_coords = np.ogrid[:rows, :cols]
        dist_sq = (r_coords - center_r)**2 + (c_coords - center_c)**2
        storm_core = 1.0 + 0.25 * np.exp(-dist_sq / (2 * (rows / 3)**2))
        return grid * storm_core.astype(np.float32)
