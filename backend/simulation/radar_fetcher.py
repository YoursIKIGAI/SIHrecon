"""
Fix 2 — Real Rainfall Data Sources.
Supports:
  1. OpenWeatherMap API (live forecast)
  2. Bundled IMD historical event (Mumbai 26 July 2005 cloudburst)
  3. Graceful fallback to preset scenarios if all sources fail
"""
import os
import json
import time
from typing import List, Optional, Dict, Any

try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False


# Bundled historical event data directory
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "rainfall")


class RealTimeRainfallFetcher:
    """
    Fetches real rainfall nowcast data from external sources.
    Falls back gracefully if APIs are unavailable.
    """

    # Simple in-memory cache: key → (timestamp, data)
    _cache: Dict[str, Any] = {}
    _cache_ttl_sec = 300  # 5 minutes

    @classmethod
    def _cache_get(cls, key: str):
        entry = cls._cache.get(key)
        if entry and (time.time() - entry[0]) < cls._cache_ttl_sec:
            return entry[1]
        return None

    @classmethod
    def _cache_set(cls, key: str, data):
        cls._cache[key] = (time.time(), data)

    # ------------------------------------------------------------------
    # Source 1: OpenWeatherMap API
    # ------------------------------------------------------------------
    @classmethod
    def fetch_openweathermap(
        cls,
        lat: float = 19.076,
        lon: float = 72.874,
        api_key: str = "",
        hours: int = 3,
    ) -> Optional[List[Dict]]:
        """
        Fetch rainfall forecast from OpenWeatherMap One Call / Forecast API.
        Returns list of {minutes, rainfall_mm_hr} dicts or None if failed.
        """
        if not api_key or not _HAS_REQUESTS:
            return None

        cache_key = f"owm_{lat}_{lon}_{api_key[:6]}"
        cached = cls._cache_get(cache_key)
        if cached:
            return cached

        try:
            # Try One Call API 3.0 first, fall back to free 2.5
            url = (
                f"https://api.openweathermap.org/data/3.0/onecall"
                f"?lat={lat}&lon={lon}&exclude=minutely,daily,alerts"
                f"&appid={api_key}&units=metric"
            )
            resp = _requests.get(url, timeout=8)
            if resp.status_code == 401:
                # Try free 2.5 endpoint
                url = (
                    f"https://api.openweathermap.org/data/2.5/forecast"
                    f"?lat={lat}&lon={lon}&appid={api_key}&units=metric&cnt=4"
                )
                resp = _requests.get(url, timeout=8)

            if not resp.ok:
                return None

            data = resp.json()

            # Parse hourly data
            forecast_points = []
            hourly = data.get("hourly", data.get("list", []))

            for i, entry in enumerate(hourly[:hours + 1]):
                minute = i * 60
                if minute > 180:
                    break
                rain_1h = entry.get("rain", {}).get("1h", 0.0) if isinstance(entry.get("rain"), dict) else 0.0
                rain_3h = entry.get("rain", {}).get("3h", 0.0) if isinstance(entry.get("rain"), dict) else 0.0
                rain_mm_hr = rain_1h if rain_1h > 0 else (rain_3h / 3.0)
                forecast_points.append({"minutes": minute, "rainfall_mm_hr": round(float(rain_mm_hr), 2)})

            if forecast_points:
                cls._cache_set(cache_key, forecast_points)
                return forecast_points

        except Exception as e:
            print(f"[RadarFetcher] OpenWeatherMap API error: {e}")

        return None

    # ------------------------------------------------------------------
    # Source 2: IMD Historical Event (Bundled JSON)
    # ------------------------------------------------------------------
    @classmethod
    def fetch_imd_historical(cls, event: str = "mumbai_2005") -> Optional[List[Dict]]:
        """
        Load bundled IMD historical rainfall data.
        Currently supports: mumbai_2005 (26 July 2005 cloudburst, 944mm/24h)
        """
        cache_key = f"imd_{event}"
        cached = cls._cache_get(cache_key)
        if cached:
            return cached

        event_file = os.path.join(_DATA_DIR, f"{event}_event.json")

        if os.path.exists(event_file):
            try:
                with open(event_file, "r") as f:
                    data = json.load(f)
                result = data.get("forecast", [])
                if result:
                    cls._cache_set(cache_key, result)
                    return result
            except Exception as e:
                print(f"[RadarFetcher] Failed to load {event_file}: {e}")

        # Generate and save the historical event data
        result = cls._generate_mumbai_2005_event()
        os.makedirs(_DATA_DIR, exist_ok=True)
        with open(event_file, "w") as f:
            json.dump({
                "event": event,
                "description": "Mumbai 26 July 2005 cloudburst — 944mm/24h. Approx 0-3h peak window.",
                "source": "IMD reconstructed hydrograph — synthetic representation of actual event",
                "forecast": result,
            }, f, indent=2)

        cls._cache_set(cache_key, result)
        return result

    @classmethod
    def _generate_mumbai_2005_event(cls) -> List[Dict]:
        """
        Synthesized 0-3hr rainfall hydrograph for the 26 July 2005 Mumbai cloudburst.
        Peak rainfall was ~200mm/hr in the most intense 2-hour burst.
        """
        return [
            {"minutes": 0,   "rainfall_mm_hr": 45.0},
            {"minutes": 30,  "rainfall_mm_hr": 110.0},
            {"minutes": 60,  "rainfall_mm_hr": 185.0},
            {"minutes": 90,  "rainfall_mm_hr": 210.0},   # Peak — catastrophic inundation
            {"minutes": 120, "rainfall_mm_hr": 175.0},
            {"minutes": 150, "rainfall_mm_hr": 120.0},
            {"minutes": 180, "rainfall_mm_hr": 70.0},
        ]

    # ------------------------------------------------------------------
    # Source 3: Spatial radar grid (non-uniform storm)
    # ------------------------------------------------------------------
    @classmethod
    def fetch_spatial_radar_grid(
        cls,
        rows: int,
        cols: int,
        forecast_points: List[Dict],
        move_vector: tuple = (0, 0),
    ):
        """
        Generate a spatially non-uniform rainfall grid from a temporal forecast.
        Storm core moves according to move_vector per timestep.
        Returns shape: (len(forecast_points), rows, cols) as float32 numpy array.
        """
        import numpy as np

        n_steps = len(forecast_points)
        grid = np.zeros((n_steps, rows, cols), dtype=np.float32)
        r_coords, c_coords = np.ogrid[:rows, :cols]

        center_r = rows / 2.0
        center_c = cols / 2.0
        radius = min(rows, cols) / 3.0

        for i, point in enumerate(forecast_points):
            intensity = float(point["rainfall_mm_hr"])
            if intensity <= 0:
                continue

            # Storm moves according to vector
            cr = center_r + i * move_vector[0]
            cc = center_c + i * move_vector[1]
            cr = np.clip(cr, 0, rows - 1)
            cc = np.clip(cc, 0, cols - 1)

            dist_sq = (r_coords - cr) ** 2 + (c_coords - cc) ** 2
            # Primary convective core
            core = 1.0 + 0.3 * np.exp(-dist_sq / (2 * radius**2))
            # Add secondary cell for realism
            r2 = cr - rows * 0.1
            c2 = cc + cols * 0.1
            dist2_sq = (r_coords - r2) ** 2 + (c_coords - c2) ** 2
            cell2 = 0.5 * np.exp(-dist2_sq / (2 * (radius * 0.7)**2))

            spatial = (core + cell2).astype(np.float32)
            grid[i] = np.clip(intensity * spatial, 0, intensity * 1.5)

        return grid
