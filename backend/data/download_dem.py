"""
Fix 1 helper — Download SRTM DEM script.
Run this ONCE to download real elevation data for all supported cities.

Usage:
  pip install elevation  (wraps the SRTM CGIAR dataset)
  python backend/data/download_dem.py
"""
import os
import sys


DEM_DIR = os.path.join(os.path.dirname(__file__), "dem")

CITIES = {
    "mumbai": {
        "bounds": (72.850, 19.055, 72.905, 19.095),
        "output": "mumbai_srtm.tif",
    },
    "delhi": {
        "bounds": (77.100, 28.580, 77.280, 28.720),
        "output": "delhi_srtm.tif",
    },
    "chennai": {
        "bounds": (80.220, 13.000, 80.320, 13.120),
        "output": "chennai_srtm.tif",
    },
}


def download_with_elevation_package(city_key: str, bounds: tuple, output_file: str):
    """Uses the `elevation` Python package (wraps CGIAR SRTM 30m)."""
    try:
        import elevation
        west, south, east, north = bounds
        output_path = os.path.join(DEM_DIR, output_file)
        print(f"[DEM] Downloading {city_key} SRTM DEM to {output_path}...")
        elevation.clip(bounds=(west, south, east, north), output=output_path)
        elevation.clean()
        print(f"[DEM] ✅ {city_key} done: {output_path}")
        return True
    except ImportError:
        print("[DEM] `elevation` package not found. Trying manual curl method...")
        return False
    except Exception as e:
        print(f"[DEM] Error: {e}")
        return False


def download_manual_instructions():
    print("""
=== Manual DEM Download Instructions ===

1. Go to https://earthexplorer.usgs.gov/ (free, requires login)
2. Search for SRTM 1 Arc-Second Global
3. Download GeoTIFF for each bounding box:
   - Mumbai:  W:72.850  S:19.055  E:72.905  N:19.095
   - Delhi:   W:77.100  S:28.580  E:77.280  N:28.720
   - Chennai: W:80.220  S:13.000  E:80.320  N:13.120

4. Save files to: backend/data/dem/
   - mumbai_srtm.tif
   - delhi_srtm.tif
   - chennai_srtm.tif

Alternatively, use the `elevation` Python package:
  pip install elevation
  python backend/data/download_dem.py

Or use OpenTopography API (requires free API key):
  https://opentopography.org/
""")


if __name__ == "__main__":
    os.makedirs(DEM_DIR, exist_ok=True)
    print(f"[DEM] Saving files to: {DEM_DIR}")

    success = False
    for city_key, info in CITIES.items():
        result = download_with_elevation_package(city_key, info["bounds"], info["output"])
        if result:
            success = True

    if not success:
        download_manual_instructions()
