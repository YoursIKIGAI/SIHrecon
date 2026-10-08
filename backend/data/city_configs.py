"""
Fix 8 — Multi-City Configuration Registry.
Add new cities by extending CITY_REGISTRY.
"""
import os

BASE_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

CITY_REGISTRY = {
    "mumbai": {
        "name": "Mumbai Metropolitan Region",
        "min_lat": 19.055,
        "max_lat": 19.095,
        "min_lon": 72.850,
        "max_lon": 72.905,
        "rows": 40,
        "cols": 50,
        "dem_file": os.path.join(BASE_DATA_DIR, "dem", "mumbai_srtm.tif"),
        "description": "Financial capital — prone to June–Sept monsoon flooding (ref: 26 July 2005 cloudburst, 944 mm/24h)",
        "center_lat": 19.075,
        "center_lon": 72.877,
        "timezone": "Asia/Kolkata",
    },
    "delhi": {
        "name": "Delhi NCR — Yamuna Floodplain",
        "min_lat": 28.580,
        "max_lat": 28.720,
        "min_lon": 77.100,
        "max_lon": 77.280,
        "rows": 40,
        "cols": 50,
        "dem_file": os.path.join(BASE_DATA_DIR, "dem", "delhi_srtm.tif"),
        "description": "Yamuna river floodplain — flash floods and waterlogging during monsoon (ref: Aug 2023 floods)",
        "center_lat": 28.650,
        "center_lon": 77.190,
        "timezone": "Asia/Kolkata",
    },
    "chennai": {
        "name": "Chennai Metro Basin — Adyar River",
        "min_lat": 13.000,
        "max_lat": 13.120,
        "min_lon": 80.220,
        "max_lon": 80.320,
        "rows": 40,
        "cols": 50,
        "dem_file": os.path.join(BASE_DATA_DIR, "dem", "chennai_srtm.tif"),
        "description": "Adyar river basin and coastal flood plain — ref: 2015 Chennai mega floods",
        "center_lat": 13.060,
        "center_lon": 80.270,
        "timezone": "Asia/Kolkata",
    },
}

# Active city (can be changed at runtime via POST /api/switch-city)
_active_city_key = "mumbai"


def get_active_city_key() -> str:
    return _active_city_key


def set_active_city_key(key: str) -> bool:
    global _active_city_key
    if key in CITY_REGISTRY:
        _active_city_key = key
        return True
    return False


def get_city_config(key: str = None) -> dict:
    k = key or _active_city_key
    return CITY_REGISTRY.get(k, CITY_REGISTRY["mumbai"])
