"""
All backend API routes — includes all fixes:
Fix 2: /api/radar-feed (real rainfall sources)
Fix 3: /api/validate?mode=... (proper validation modes)
Fix 5: /api/search-locations (Nominatim geocoding)
Fix 6: /api/trigger-auto-update (WebSocket control)
Fix 8: /api/cities + /api/switch-city (multi-city)
Fix 9: /api/export/geotiff + /api/export/geojson (export)
"""
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional, Dict, Any, List
import time
import io
import json
import numpy as np

from ..models.schemas import (
    SimulationRequest,
    SimulationResponse,
    RouteRequest,
    RouteResponse,
    ValidationMetrics,
    FloodPredictionRecord,
    MLTrainingRequest,
    MLTrainingResponse,
    LocationSearchResult,
)
from ..simulation.flood_engine import get_flood_engine
from ..simulation.routing import RoutingEngine
from ..simulation.radar_fetcher import RealTimeRainfallFetcher
from ..data.city_generator import get_city_data, reset_city_instance
from ..data.city_configs import CITY_REGISTRY, set_active_city_key, get_active_city_key
from ..data.validation import FloodValidator
from ..ml.train_model import train_surrogate_model
from ..ml.model import get_ml_model

router = APIRouter()

# Initialize engines
engine = get_flood_engine()
city = get_city_data()
router_engine = RoutingEngine(city)
validator = FloodValidator()
ml_model = get_ml_model()


# ---------------------------------------------------------------
# Core simulation & status
# ---------------------------------------------------------------

@router.get("/status")
def get_status() -> Dict[str, Any]:
    """System health check and engine metadata."""
    return {
        "status": "healthy",
        "service": "Urban Flood Nowcasting & Flood-Safe Routing System v2",
        "version": "2.0.0-sih-enhanced",
        "engine_ready": True,
        "ml_model_trained": ml_model.is_trained,
        "active_city": get_active_city_key(),
        "data_sources": {
            "dem": "real_srtm" if getattr(city, "using_real_dem", False) else "synthetic_fallback",
            "roads": "osm_real" if getattr(city, "using_real_roads", False) else "synthetic_fallback",
        },
        "grid": {
            "rows": city.rows,
            "cols": city.cols,
            "cell_area_m2": round(city.cell_area_m2, 1),
            "bounds": {
                "min_lat": city.min_lat,
                "max_lat": city.max_lat,
                "min_lon": city.min_lon,
                "max_lon": city.max_lon,
            }
        },
        "network": {
            "road_nodes": len(city.road_nodes),
            "road_edges": len(city.road_edges),
            "drain_nodes": len(city.drain_nodes),
            "drain_edges": len(city.drain_edges),
        },
        "last_simulation": {
            "scenario": engine.last_result.scenario if engine.last_result else None,
            "engine_mode": engine.last_result.engine_mode if engine.last_result else "physics",
            "execution_time_ms": engine.last_result.execution_time_ms if engine.last_result else None,
        }
    }


@router.get("/scenarios")
def get_scenarios() -> Dict[str, Any]:
    """List available predefined rainfall scenarios."""
    return engine.rainfall_module.get_available_scenarios()


@router.post("/simulate", response_model=SimulationResponse)
def simulate_flood(request: SimulationRequest) -> SimulationResponse:
    """
    Run fast flood nowcasting simulation across 0-3 hour timeline.
    Supports both coupled hydrodynamic physics and trained AI/ML surrogate mode.
    """
    response = engine.run_simulation(
        scenario=request.scenario or "extreme",
        custom_forecast=request.rainfall,
        duration_minutes=request.duration_minutes,
        soil_absorption_rate=request.soil_absorption_rate or 4.0,
        engine_mode=request.engine_mode or "physics"
    )
    return response


@router.get("/flood-map")
def get_flood_map(timestep: int = Query(default=60, description="Forecast minute (0, 30, 60, 90, 120, 180)")) -> Dict[str, Any]:
    """Return GeoJSON containing predicted flood polygons and flooded roads for a specific timestep."""
    return engine.get_flood_geojson(timestep_minute=timestep)


@router.get("/drainage")
def get_drainage_network() -> Dict[str, Any]:
    """Return the drainage network directed graph in GeoJSON format."""
    return engine.drainage_model.to_geojson()


@router.post("/route", response_model=RouteResponse)
def compute_flood_safe_route(request: RouteRequest) -> RouteResponse:
    """Compute optimal flood-safe route avoiding high water depths (>40cm blocked)."""
    timestep = request.timestep_minutes if request.timestep_minutes is not None else 60
    road_states = engine.cached_road_states.get(timestep)
    if road_states is None:
        if engine.cached_road_states:
            closest_ts = min(engine.cached_road_states.keys(), key=lambda t: abs(t - timestep))
            road_states = engine.cached_road_states[closest_ts]
        else:
            road_states = []

    return router_engine.calculate_routes(
        origin_lon=request.origin[0],
        origin_lat=request.origin[1],
        dest_lon=request.destination[0],
        dest_lat=request.destination[1],
        road_depths=road_states,
        timestep_minutes=timestep
    )


@router.get("/predictions", response_model=List[FloodPredictionRecord])
def get_predictions(timestep: int = Query(default=60)) -> List[FloodPredictionRecord]:
    """Structured flood prediction records per hackathon specification."""
    return engine.get_prediction_records(timestep_minute=timestep)


# ---------------------------------------------------------------
# Fix 3: Validation with real ground truth modes
# ---------------------------------------------------------------

@router.post("/validate", response_model=ValidationMetrics)
def validate_simulation(
    timestep: int = Query(default=90),
    mode: str = Query(default="benchmark_physics", description="benchmark_physics | historical_event | self_noise")
) -> ValidationMetrics:
    """
    Fix 3: Assess prediction accuracy with real validation modes.
    - benchmark_physics: independent physics run with different params
    - historical_event: compare against field observation CSV points
    - self_noise: old synthetic benchmark (clearly labeled as demo only)
    """
    depth_grid = engine.cached_depth_grids.get(timestep)
    if depth_grid is None:
        available = list(engine.cached_depth_grids.keys())
        depth_grid = engine.cached_depth_grids[available[0]] if available else np.zeros((city.rows, city.cols))

    return validator.evaluate_predictions(
        predicted_depth_grid=depth_grid,
        mode=mode,
        city_data=city,
    )


# ---------------------------------------------------------------
# ML model training and status
# ---------------------------------------------------------------

@router.post("/train", response_model=MLTrainingResponse)
def train_model(request: MLTrainingRequest = MLTrainingRequest()) -> MLTrainingResponse:
    """Trains the Machine Learning Flood Depth Surrogate Model (Fix 10: MLP)."""
    metrics = train_surrogate_model(
        epochs=request.epochs,
        num_storm_scenarios=request.num_storm_scenarios
    )
    return MLTrainingResponse(
        status="TRAINED_SUCCESSFULLY",
        r2_score=metrics["r2_score"],
        rmse_depth_cm=metrics["rmse_depth_cm"],
        mae_depth_cm=metrics["mae_depth_cm"],
        training_time_ms=metrics["training_time_ms"],
        train_samples=metrics["train_samples"],
        val_samples=metrics["val_samples"],
        feature_importances=metrics["feature_importances"],
        training_history=ml_model.training_history,
        trained_at=metrics.get("trained_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    )


@router.get("/ml-status")
def get_ml_status() -> Dict[str, Any]:
    """Returns current state, accuracy metrics, and feature importances of the trained ML model."""
    return {
        "is_trained": ml_model.is_trained,
        "metrics": ml_model.metrics,
        "feature_names": ml_model.feature_names,
        "model_type": getattr(ml_model, "model_type", "mlp_surrogate"),
        "training_history": ml_model.training_history[-20:] if ml_model.training_history else [],
    }


# ---------------------------------------------------------------
# Fix 2: Real rainfall / radar feed endpoint
# ---------------------------------------------------------------

@router.get("/radar-feed")
def get_radar_feed(
    source: str = Query(default="imd_historical", description="openweathermap | imd_historical"),
    event: str = Query(default="mumbai_2005"),
    api_key: str = Query(default=""),
    lat: float = Query(default=19.076),
    lon: float = Query(default=72.874),
) -> Dict[str, Any]:
    """
    Fix 2: Fetch rainfall data from real external sources.
    source='imd_historical': bundled Mumbai 2005 cloudburst event.
    source='openweathermap': live API forecast (requires api_key).
    """
    fetcher = RealTimeRainfallFetcher()

    if source == "openweathermap" and api_key:
        data = fetcher.fetch_openweathermap(lat=lat, lon=lon, api_key=api_key)
        if data:
            return {
                "source": "openweathermap_live",
                "lat": lat,
                "lon": lon,
                "forecast": data,
                "note": "Live forecast from OpenWeatherMap API",
            }

    # Fall back to historical event
    data = fetcher.fetch_imd_historical(event=event)
    return {
        "source": "imd_historical",
        "event": event,
        "forecast": data or [],
        "note": f"Bundled historical event: {event}. Use source=openweathermap with api_key for live data.",
    }


# ---------------------------------------------------------------
# Fix 5: Real geocoding with Nominatim
# ---------------------------------------------------------------

_LOCATION_CACHE: Dict[str, Any] = {}
_LOCATION_CACHE_TIME: Dict[str, float] = {}
_CACHE_TTL = 300  # seconds

_FALLBACK_POIS = [
    {"id": "POI_1", "name": "Downtown Central Station", "lat": 19.062, "lon": 72.870, "category": "transit"},
    {"id": "POI_2", "name": "Milan Subway Underpass", "lat": 19.073, "lon": 72.874, "category": "chokepoint"},
    {"id": "POI_3", "name": "Metro Airport Terminal 2", "lat": 19.088, "lon": 72.868, "category": "airport"},
    {"id": "POI_4", "name": "King's Circle Junction", "lat": 19.067, "lon": 72.864, "category": "basin"},
    {"id": "POI_5", "name": "Central Trauma Hospital", "lat": 19.076, "lon": 72.888, "category": "hospital"},
    {"id": "POI_6", "name": "East Tech City Cyberpark", "lat": 19.085, "lon": 72.898, "category": "commercial"},
    {"id": "POI_7", "name": "West Coast Harbor Gate", "lat": 19.065, "lon": 72.854, "category": "maritime"},
    {"id": "POI_8", "name": "Elevated Expressway Interchange", "lat": 19.086, "lon": 72.890, "category": "highway"},
    {"id": "POI_9", "name": "Kurla Creek Bridge Link", "lat": 19.082, "lon": 72.883, "category": "bridge"},
    {"id": "POI_10", "name": "South Port Entrance Gate", "lat": 19.058, "lon": 72.862, "category": "port"},
]


@router.get("/search-locations", response_model=List[LocationSearchResult])
def search_locations(q: str = Query(default="", description="Search query string")) -> List[LocationSearchResult]:
    """
    Fix 5: Real geocoding via Nominatim API with fallback to hardcoded POIs.
    Nominatim is free and requires no API key.
    """
    import requests as req

    q_lower = q.lower().strip()
    results = []

    # Check cache
    cache_key = f"nominatim_{q_lower}"
    if cache_key in _LOCATION_CACHE and (time.time() - _LOCATION_CACHE_TIME.get(cache_key, 0)) < _CACHE_TTL:
        return _LOCATION_CACHE[cache_key]

    # Try Nominatim
    if q_lower and len(q_lower) >= 2:
        try:
            active_city_cfg = CITY_REGISTRY.get(get_active_city_key(), CITY_REGISTRY["mumbai"])
            viewbox = (
                f"{active_city_cfg['min_lon']},{active_city_cfg['max_lat']},"
                f"{active_city_cfg['max_lon']},{active_city_cfg['min_lat']}"
            )
            url = (
                f"https://nominatim.openstreetmap.org/search"
                f"?q={q}+Mumbai&format=json&viewbox={viewbox}&bounded=0&limit=6&addressdetails=0"
            )
            headers = {"User-Agent": "SIHFloodNowcast/2.0 flood-nowcast@sih.gov.in"}
            resp = req.get(url, headers=headers, timeout=4)
            if resp.ok:
                places = resp.json()
                for place in places[:6]:
                    lat = float(place.get("lat", 0))
                    lon = float(place.get("lon", 0))
                    r, c = city.lat_lon_to_cell(lat, lon)
                    elev = float(city.dem[r, c])
                    results.append(LocationSearchResult(
                        id=f"NOM_{place.get('osm_id', 'x')}",
                        name=place.get("display_name", "Unknown")[:60],
                        lat=lat,
                        lon=lon,
                        category=place.get("type", "place"),
                        elevation_m=elev,
                    ))
        except Exception as e:
            print(f"[Search] Nominatim failed: {e}")

    # Fallback: hardcoded POIs
    if not results:
        for p in _FALLBACK_POIS:
            if not q_lower or q_lower in p["name"].lower() or q_lower in p["category"].lower():
                r, c = city.lat_lon_to_cell(p["lat"], p["lon"])
                elev = float(city.dem[r, c])
                results.append(LocationSearchResult(
                    id=p["id"], name=p["name"], lat=p["lat"], lon=p["lon"],
                    category=p["category"], elevation_m=elev,
                ))

    _LOCATION_CACHE[cache_key] = results
    _LOCATION_CACHE_TIME[cache_key] = time.time()
    return results


# ---------------------------------------------------------------
# Fix 6: WebSocket auto-update control
# ---------------------------------------------------------------

@router.post("/trigger-auto-update")
def trigger_auto_update(
    enabled: bool = Query(default=True),
    interval_seconds: int = Query(default=60),
    scenario: str = Query(default="extreme"),
    body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Fix 6: Enable/disable background WebSocket auto-update loop.
    When enabled, a new simulation runs every interval_seconds and
    is pushed to all connected WebSocket clients.
    """
    if body:
        enabled = body.get("enabled", enabled)
        interval_seconds = body.get("interval_seconds", interval_seconds)
        scenario = body.get("scenario", scenario)

    import backend.main as _main
    _main._auto_update_enabled = bool(enabled)
    _main._auto_update_interval = max(10, int(interval_seconds))
    _main._auto_update_scenario = str(scenario)
    return {
        "auto_update_enabled": _main._auto_update_enabled,
        "interval_seconds": _main._auto_update_interval,
        "scenario": _main._auto_update_scenario,
        "connected_clients": len(_main.manager.active) if hasattr(_main, "manager") else 0,
    }


# ---------------------------------------------------------------
# Fix 8: Multi-city endpoints
# ---------------------------------------------------------------

@router.get("/cities")
def get_cities() -> Dict[str, Any]:
    """Fix 8: List all supported city profiles."""
    return {
        k: {
            "name": v["name"],
            "description": v["description"],
            "center_lat": v.get("center_lat", (v["min_lat"] + v["max_lat"]) / 2),
            "center_lon": v.get("center_lon", (v["min_lon"] + v["max_lon"]) / 2),
            "bounds": {
                "min_lat": v["min_lat"], "max_lat": v["max_lat"],
                "min_lon": v["min_lon"], "max_lon": v["max_lon"],
            },
            "dem_available": False,  # Will be True once real DEM files are downloaded
        }
        for k, v in CITY_REGISTRY.items()
    }


@router.post("/switch-city")
def switch_city(
    city_key: Optional[str] = Query(default=None, description="mumbai | delhi | chennai"),
    body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Fix 8: Switch the active simulation city.
    Re-initializes the flood engine with the new city's terrain data.
    """
    global engine, city, router_engine, validator

    target_key = city_key or (body.get("city") or body.get("city_key") if body else None) or "mumbai"

    if not set_active_city_key(target_key):
        raise HTTPException(status_code=400, detail=f"Unknown city key: {target_key}. Valid: {list(CITY_REGISTRY.keys())}")

    reset_city_instance()
    city = get_city_data()
    engine = get_flood_engine()
    router_engine = RoutingEngine(city)
    validator = FloodValidator()

    return {
        "switched_to": target_key,
        "city_name": CITY_REGISTRY[target_key]["name"],
        "grid": {"rows": city.rows, "cols": city.cols},
        "using_real_dem": getattr(city, "using_real_dem", False),
        "using_real_roads": getattr(city, "using_real_roads", False),
    }


# ---------------------------------------------------------------
# Fix 9: Export endpoints (GeoTIFF and GeoJSON download)
# ---------------------------------------------------------------

@router.get("/export/geojson")
def export_geojson(timestep: int = Query(default=60)) -> StreamingResponse:
    """Fix 9: Export flood map as downloadable GeoJSON file."""
    data = engine.get_flood_geojson(timestep_minute=timestep)
    content = json.dumps(data, indent=2).encode("utf-8")
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/geo+json",
        headers={"Content-Disposition": f"attachment; filename=flood_map_t{timestep}min.geojson"},
    )


@router.get("/export/geotiff")
def export_geotiff(timestep: int = Query(default=60)) -> StreamingResponse:
    """Fix 9: Export flood depth grid as downloadable GeoTIFF raster."""
    try:
        import rasterio
        from rasterio.transform import from_bounds
        from rasterio.crs import CRS

        depth_grid = engine.cached_depth_grids.get(timestep)
        if depth_grid is None:
            available = sorted(engine.cached_depth_grids.keys())
            if available:
                depth_grid = engine.cached_depth_grids[available[-1]]
            else:
                depth_grid = np.zeros((city.rows, city.cols), dtype=np.float32)

        transform = from_bounds(
            city.min_lon, city.min_lat, city.max_lon, city.max_lat,
            city.cols, city.rows,
        )
        buf = io.BytesIO()
        with rasterio.open(
            buf, "w",
            driver="GTiff",
            height=city.rows,
            width=city.cols,
            count=1,
            dtype="float32",
            crs=CRS.from_epsg(4326),
            transform=transform,
        ) as dst:
            dst.write(depth_grid.astype(np.float32), 1)
            dst.update_tags(
                description="Urban flood depth prediction (cm)",
                timestep_minutes=str(timestep),
                scenario=engine.last_result.scenario if engine.last_result else "unknown",
            )

        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="image/tiff",
            headers={"Content-Disposition": f"attachment; filename=flood_depth_t{timestep}min.tif"},
        )

    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="rasterio not installed. Install it with: pip install rasterio"
        )


@router.get("/dem")
def get_dem_grid() -> Dict[str, Any]:
    """Returns DEM elevation grid and terrain statistics."""
    return {
        "rows": city.rows,
        "cols": city.cols,
        "using_real_dem": getattr(city, "using_real_dem", False),
        "min_elevation_m": float(np.min(city.dem)),
        "max_elevation_m": float(np.max(city.dem)),
        "mean_elevation_m": float(np.mean(city.dem)),
        "elevation_matrix": city.dem.tolist(),
        "bounds": {
            "min_lat": city.min_lat,
            "max_lat": city.max_lat,
            "min_lon": city.min_lon,
            "max_lon": city.max_lon,
        }
    }
