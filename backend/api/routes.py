"""
All backend API routes for Urban Flood Nowcasting & Flood-Safe Routing System.
Includes:
- Multi-city simulation pipeline (Mumbai, Delhi, Chennai)
- Historical test scenario replay mode isolated from live nowcasting
- Dynamic flood-aware routing (Fastest, Flood-Safe, Alternative)
- Officer Alert dashboard endpoints with status management (Active, Acknowledged, Resolved, Dismissed)
- Verified historical flood observation ground-truth feeds
- DEM & terrain susceptibility endpoints
- Nominatim geocoding with city-aware bounds and fallbacks
"""
from fastapi import APIRouter, Query, HTTPException, Body
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional, Dict, Any, List
import time
import io
import json
import os
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
    OfficerAlert,
    AlertStatusUpdateRequest,
    HistoricalEventSummary,
)
from ..simulation.flood_engine import get_flood_engine, reset_flood_engine
from ..simulation.routing import RoutingEngine
from ..simulation.radar_fetcher import RealTimeRainfallFetcher
from ..data.city_generator import get_city_data, reset_city_instance, CityData
from ..data.city_configs import (
    CITY_REGISTRY,
    set_active_city_key,
    get_active_city_key,
    get_city_config,
    get_city_presets,
    get_city_pois,
    get_historical_events,
)
from ..data.validation import FloodValidator
from ..ml.train_model import train_surrogate_model
from ..ml.model import get_ml_model

router = APIRouter()

validator = FloodValidator()
ml_model = get_ml_model()


def current_city() -> CityData:
    """Returns CityData for active city."""
    return get_city_data(city_key=get_active_city_key())


def current_engine():
    """Returns FloodEngine for active city."""
    return get_flood_engine(get_active_city_key())


def current_router() -> RoutingEngine:
    """Returns RoutingEngine configured for active city."""
    return RoutingEngine(current_city())


# ---------------------------------------------------------------
# Core simulation & status
# ---------------------------------------------------------------

@router.get("/status")
def get_status() -> Dict[str, Any]:
    """System health check and multi-city engine metadata."""
    city = current_city()
    engine = current_engine()
    active_key = get_active_city_key()
    city_cfg = get_city_config(active_key)

    return {
        "status": "healthy",
        "service": "Urban Flood Nowcasting & Flood-Safe Routing System v2",
        "version": "2.0.0-sih-enhanced",
        "engine_ready": True,
        "ml_model_trained": ml_model.is_trained,
        "active_city": active_key,
        "city_name": city.city_name,
        "data_sources": {
            "dem": "real_srtm" if getattr(city, "using_real_dem", False) else "dem_georeferenced_model",
            "roads": "osm_network" if getattr(city, "using_real_roads", False) else "osm_topological_graph",
            "drainage": "municipal_network_verified_inferred",
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
            "simulation_mode": getattr(engine.last_result, "simulation_mode", "live") if engine.last_result else "live",
            "execution_time_ms": engine.last_result.execution_time_ms if engine.last_result else None,
        },
        "active_alerts_count": len(engine.active_alerts),
    }


@router.get("/scenarios")
def get_scenarios() -> Dict[str, Any]:
    """List available predefined synthetic and historical rainfall scenarios."""
    engine = current_engine()
    return engine.rainfall_module.get_available_scenarios()


@router.post("/simulate", response_model=SimulationResponse)
def simulate_flood(request: SimulationRequest) -> SimulationResponse:
    """
    Run fast flood nowcasting simulation across 0-3 hour timeline for active city.
    Supports both coupled hydrodynamic physics and trained AI/ML surrogate mode.
    """
    active_key = get_active_city_key()
    target_key = getattr(request, "city_key", None) or active_key
    if target_key != active_key and target_key in CITY_REGISTRY:
        set_active_city_key(target_key)

    engine = current_engine()
    response = engine.run_simulation(
        scenario=request.scenario or "extreme",
        custom_forecast=request.rainfall,
        duration_minutes=request.duration_minutes,
        soil_absorption_rate=request.soil_absorption_rate or 4.0,
        engine_mode=request.engine_mode or "physics",
        simulation_mode="live"
    )
    return response


# ---------------------------------------------------------------
# Historical Scenario Endpoints (Dedicated Historical Mode)
# ---------------------------------------------------------------

@router.get("/scenarios/historical")
def get_historical_scenarios(city_key: Optional[str] = Query(default=None)) -> List[Dict[str, Any]]:
    """
    Lists documented historical flood scenarios for specified or all cities.
    Includes Delhi July 2023, Mumbai July 2005, and Chennai Dec 2015 events.
    """
    events = get_historical_events(city_key)
    return events


@router.post("/simulate/historical", response_model=SimulationResponse)
def simulate_historical_scenario(
    body: Dict[str, Any] = Body(..., examples=[{"city_key": "delhi", "event_id": "delhi_2023_yamuna"}])
) -> SimulationResponse:
    """
    Runs historical replay simulation in isolated Historical Test Mode.
    Loads documented event rainfall, historical flood observations, and city infrastructure.
    Test alerts are flagged as test-only and isolated from live feeds.
    """
    city_key = body.get("city_key") or get_active_city_key()
    event_id = body.get("event_id")

    if city_key not in CITY_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unknown city: {city_key}. Valid: {list(CITY_REGISTRY.keys())}")

    # Switch active city if required
    set_active_city_key(city_key)
    engine = current_engine()

    # Determine default event_id if not provided
    if not event_id:
        city_events = get_historical_events(city_key)
        if city_events:
            event_id = city_events[0]["id"]

    response = engine.run_simulation(
        scenario=event_id or "historical",
        duration_minutes=body.get("duration_minutes", 180),
        soil_absorption_rate=body.get("soil_absorption_rate", 3.0),
        engine_mode=body.get("engine_mode", "physics"),
        city_key=city_key,
        simulation_mode="historical",
        event_id=event_id,
    )
    return response


@router.get("/historical-observations")
def get_historical_observations(city_key: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    """
    Returns verified ground-truth historical observation points for active or specified city.
    Visualized on map to evaluate prediction accuracy against documented ground truth.
    """
    ckey = city_key or get_active_city_key()
    raw_points = validator.get_observation_points(ckey)

    features = []
    for p in raw_points:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [p["lon"], p["lat"]]
            },
            "properties": {
                "id": p["id"],
                "name": p["location_name"],
                "city_key": p["city_key"],
                "observed_depth_cm": p["observed_depth_cm"],
                "source": p["source"],
                "category": "historical_observation"
            }
        })

    return {
        "type": "FeatureCollection",
        "city_key": ckey,
        "features": features
    }


# ---------------------------------------------------------------
# Officer Alert Dashboard Endpoints
# ---------------------------------------------------------------

@router.get("/alerts", response_model=List[OfficerAlert])
def get_officer_alerts() -> List[OfficerAlert]:
    """
    Returns active officer alerts generated by the active simulation.
    Includes trigger condition, supporting data, confidence, and status.
    """
    engine = current_engine()
    return engine.active_alerts


@router.post("/alerts/{alert_id}/status")
def update_officer_alert_status(alert_id: str, request: AlertStatusUpdateRequest) -> Dict[str, Any]:
    """
    Allows authorized officers to acknowledge, resolve, or dismiss alerts.
    Does NOT modify the underlying hydrodynamic flood prediction.
    """
    engine = current_engine()
    success = engine.update_alert_status(alert_id, request.status)
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert ID '{alert_id}' not found in active alerts.")

    return {
        "alert_id": alert_id,
        "new_status": request.status,
        "officer_notes": request.notes,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }


# ---------------------------------------------------------------
# Map and Network Visualizations
# ---------------------------------------------------------------

@router.get("/flood-map")
def get_flood_map(timestep: int = Query(default=60, description="Forecast minute (0, 30, 60, 90, 120, 180)")) -> Dict[str, Any]:
    """Return GeoJSON containing predicted flood polygons and flooded roads for a specific timestep."""
    engine = current_engine()
    return engine.get_flood_geojson(timestep_minute=timestep)


@router.get("/drainage")
def get_drainage_network() -> Dict[str, Any]:
    """Return the drainage network directed graph in GeoJSON format with verified vs. inferred labels."""
    engine = current_engine()
    return engine.drainage_model.to_geojson()


@router.get("/terrain-susceptibility")
def get_terrain_susceptibility() -> Dict[str, Any]:
    """
    Returns terrain-derived flood susceptibility features for the active city.
    Distinguishes static topographic depressions from dynamic rainfall predictions.
    """
    city = current_city()
    dem = city.dem
    dem_mean = float(np.mean(dem))
    dem_std = float(np.std(dem))

    depressions = []
    step_r = max(1, city.rows // 10)
    step_c = max(1, city.cols // 10)

    for r in range(0, city.rows, step_r):
        for c in range(0, city.cols, step_c):
            elev = float(dem[r, c])
            # Susceptibility score based on local elevation relative to city mean
            if elev < dem_mean:
                susceptibility = "High" if elev < (dem_mean - dem_std) else "Moderate"
                lat, lon = city.cell_to_lat_lon(r, c)
                depressions.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [round(lon, 5), round(lat, 5)]
                    },
                    "properties": {
                        "elevation_m": round(elev, 1),
                        "susceptibility": susceptibility,
                        "category": "terrain_depression",
                        "description": f"Topographic depression ({elev:.1f}m ASL)"
                    }
                })

    return {
        "type": "FeatureCollection",
        "city_key": city.city_key,
        "mean_elevation_m": round(dem_mean, 1),
        "features": depressions
    }


# ---------------------------------------------------------------
# Flood-Aware Routing
# ---------------------------------------------------------------

@router.post("/route", response_model=RouteResponse)
def compute_flood_safe_route(request: RouteRequest) -> RouteResponse:
    """
    Compute optimal flood-safe route avoiding high water depths (>40cm blocked).
    Returns Fastest Route, Flood-Safe Route, and Alternative Route.
    Validates coordinate bounds against active city.
    """
    # If request specifies a city_key that differs from active, switch to it
    if request.city_key and request.city_key.lower().strip() in CITY_REGISTRY:
        if request.city_key.lower().strip() != get_active_city_key():
            set_active_city_key(request.city_key)

    city = current_city()
    engine = current_engine()
    router_engine = current_router()

    timestep = request.timestep_minutes if request.timestep_minutes is not None else 60
    road_states = engine.cached_road_states.get(timestep)
    if road_states is None:
        if engine.cached_road_states:
            closest_ts = min(engine.cached_road_states.keys(), key=lambda t: abs(t - timestep))
            road_states = engine.cached_road_states[closest_ts]
        else:
            road_states = []

    try:
        return router_engine.calculate_routes(
            origin_lon=request.origin[0],
            origin_lat=request.origin[1],
            dest_lon=request.destination[0],
            dest_lat=request.destination[1],
            road_depths=road_states,
            timestep_minutes=timestep
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.get("/predictions", response_model=List[FloodPredictionRecord])
def get_predictions(timestep: int = Query(default=60)) -> List[FloodPredictionRecord]:
    """Structured flood prediction records per hackathon specification."""
    engine = current_engine()
    return engine.get_prediction_records(timestep_minute=timestep)


# ---------------------------------------------------------------
# Validation
# ---------------------------------------------------------------

@router.post("/validate", response_model=ValidationMetrics)
def validate_simulation(
    timestep: int = Query(default=90),
    mode: str = Query(default="benchmark_physics", description="benchmark_physics | historical_event | self_noise")
) -> ValidationMetrics:
    """
    Assess prediction accuracy with real validation modes.
    - benchmark_physics: independent physics run with different params
    - historical_event: compare against field observation CSV points
    - self_noise: synthetic benchmark (clearly labeled as demo only)
    """
    engine = current_engine()
    city = current_city()

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
    """Trains the Machine Learning Flood Depth Surrogate Model (NumPy MLP)."""
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
        "architecture": "Dense(10->32, ReLU) -> Dense(32->16, ReLU) -> Dense(16->1, Linear)",
        "inputs": [
            "surface_water_volume_m3", "elevation_m", "slope_degrees",
            "distance_to_nearest_drain_m", "drain_capacity_utilization",
            "impervious_fraction", "soil_absorption_rate", "accumulated_rain_mm",
            "current_rain_intensity_mm_hr", "upstream_accumulated_area_cells"
        ],
        "training_history": ml_model.training_history[-20:] if ml_model.training_history else [],
    }


# ---------------------------------------------------------------
# Radar / Rainfall feed
# ---------------------------------------------------------------

@router.get("/radar-feed")
def get_radar_feed(
    source: str = Query(default="imd_historical", description="openweathermap | imd_historical"),
    event: Optional[str] = Query(default=None),
    api_key: str = Query(default=""),
    lat: Optional[float] = Query(default=None),
    lon: Optional[float] = Query(default=None),
) -> Dict[str, Any]:
    """
    Fetch rainfall data from external sources or bundled historical events for active city.
    """
    city = current_city()
    active_key = city.city_key
    target_lat = lat if lat is not None else (city.min_lat + city.max_lat) / 2.0
    target_lon = lon if lon is not None else (city.min_lon + city.max_lon) / 2.0

    fetcher = RealTimeRainfallFetcher()

    if source == "openweathermap" and api_key:
        data = fetcher.fetch_openweathermap(lat=target_lat, lon=target_lon, api_key=api_key)
        if data:
            return {
                "source": "openweathermap_live",
                "lat": target_lat,
                "lon": target_lon,
                "forecast": data,
                "note": "Live forecast from OpenWeatherMap API",
            }

    # Resolve city-specific historical event
    ev_key = event
    if not ev_key:
        if active_key == "delhi":
            ev_key = "delhi_2023_yamuna"
        elif active_key == "chennai":
            ev_key = "chennai_2015_deluge"
        else:
            ev_key = "mumbai_2005"

    data = fetcher.fetch_imd_historical(event=ev_key)
    return {
        "source": "imd_historical",
        "city_key": active_key,
        "event": ev_key,
        "forecast": data or [],
        "note": f"Bundled historical event for {city.city_name}: {ev_key}.",
    }


# ---------------------------------------------------------------
# Geocoding with Nominatim & City-Specific Fallbacks
# ---------------------------------------------------------------

_LOCATION_CACHE: Dict[str, Any] = {}
_LOCATION_CACHE_TIME: Dict[str, float] = {}
_CACHE_TTL = 300  # seconds


@router.get("/search-locations", response_model=List[LocationSearchResult])
def search_locations(q: str = Query(default="", description="Search query string")) -> List[LocationSearchResult]:
    """
    Real geocoding via Nominatim API with fallback to city-specific POIs.
    Dynamically scopes search to active city (Delhi, Mumbai, Chennai).
    """
    import requests as req

    active_key = get_active_city_key()
    city_cfg = get_city_config(active_key)
    city = current_city()
    q_lower = q.lower().strip()
    results = []

    # Check cache
    cache_key = f"{active_key}_nominatim_{q_lower}"
    if cache_key in _LOCATION_CACHE and (time.time() - _LOCATION_CACHE_TIME.get(cache_key, 0)) < _CACHE_TTL:
        return _LOCATION_CACHE[cache_key]

    # Try Nominatim scoped to active city
    if q_lower and len(q_lower) >= 2:
        try:
            viewbox = (
                f"{city_cfg['min_lon']},{city_cfg['max_lat']},"
                f"{city_cfg['max_lon']},{city_cfg['min_lat']}"
            )
            city_search_keyword = city_cfg["name"].split()[0]
            url = (
                f"https://nominatim.openstreetmap.org/search"
                f"?q={q}+{city_search_keyword}&format=json&viewbox={viewbox}&bounded=0&limit=6&addressdetails=0"
            )
            headers = {"User-Agent": "SIHFloodNowcast/2.0 flood-nowcast@sih.gov.in"}
            resp = req.get(url, headers=headers, timeout=4)
            if resp.ok:
                places = resp.json()
                for place in places[:6]:
                    lat = float(place.get("lat", 0))
                    lon = float(place.get("lon", 0))
                    if city.is_point_in_bounds(lat, lon):
                        r, c = city.lat_lon_to_cell(lat, lon)
                        elev = float(city.dem[r, c])
                    else:
                        elev = float(city_cfg.get("elev_mean", 15.0))

                    results.append(LocationSearchResult(
                        id=f"NOM_{place.get('osm_id', 'x')}",
                        name=place.get("display_name", "Unknown")[:60],
                        lat=lat,
                        lon=lon,
                        category=place.get("type", "place"),
                        elevation_m=round(elev, 1),
                    ))
        except Exception as e:
            print(f"[Search] Nominatim failed: {e}")

    # Fallback to city-specific POIs
    if not results:
        city_pois = get_city_pois(active_key)
        for p in city_pois:
            if not q_lower or q_lower in p["name"].lower() or q_lower in p["category"].lower():
                r, c = city.lat_lon_to_cell(p["lat"], p["lon"])
                elev = float(city.dem[r, c])
                results.append(LocationSearchResult(
                    id=p["id"], name=p["name"], lat=p["lat"], lon=p["lon"],
                    category=p["category"], elevation_m=round(elev, 1),
                ))

    _LOCATION_CACHE[cache_key] = results
    _LOCATION_CACHE_TIME[cache_key] = time.time()
    return results


# ---------------------------------------------------------------
# WebSocket auto-update control
# ---------------------------------------------------------------

@router.post("/trigger-auto-update")
def trigger_auto_update(
    enabled: bool = Query(default=True),
    interval_seconds: int = Query(default=60),
    scenario: str = Query(default="extreme"),
    body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Enable/disable background WebSocket auto-update loop."""
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
# Multi-city endpoints
# ---------------------------------------------------------------

@router.get("/cities")
def get_cities() -> Dict[str, Any]:
    """List all supported city profiles with bounds, presets, and historical events."""
    out = {}
    for k, v in CITY_REGISTRY.items():
        out[k] = {
            "name": v["name"],
            "state": v.get("state", ""),
            "description": v["description"],
            "center_lat": v.get("center_lat", (v["min_lat"] + v["max_lat"]) / 2),
            "center_lon": v.get("center_lon", (v["min_lon"] + v["max_lon"]) / 2),
            "bounds": {
                "min_lat": v["min_lat"], "max_lat": v["max_lat"],
                "min_lon": v["min_lon"], "max_lon": v["max_lon"],
            },
            "elevation_range": {
                "min_m": v.get("elev_min", 2.0),
                "max_m": v.get("elev_max", 50.0),
                "mean_m": v.get("elev_mean", 15.0),
            },
            "route_presets": v.get("route_presets", []),
            "historical_events": v.get("historical_events", []),
            "dem_available": os.path.exists(v.get("dem_file", "")),
        }
    return out


@router.post("/switch-city")
def switch_city(
    city_key: Optional[str] = Query(default=None, description="mumbai | delhi | chennai"),
    body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Switch the active simulation city.
    Guarantees city independence and reconfigures road graph, DEM, drainage network, and alerts.
    """
    target_key = city_key or (body.get("city") or body.get("city_key") if body else None) or "mumbai"
    target_key = str(target_key).lower().strip()

    if not set_active_city_key(target_key):
        raise HTTPException(status_code=400, detail=f"Unknown city key: {target_key}. Valid: {list(CITY_REGISTRY.keys())}")

    city = current_city()
    engine = current_engine()
    cfg = get_city_config(target_key)

    return {
        "switched_to": target_key,
        "city_name": cfg["name"],
        "bounds": {
            "min_lat": city.min_lat,
            "max_lat": city.max_lat,
            "min_lon": city.min_lon,
            "max_lon": city.max_lon,
        },
        "center": {
            "lat": cfg.get("center_lat", (city.min_lat + city.max_lat) / 2),
            "lon": cfg.get("center_lon", (city.min_lon + city.max_lon) / 2),
        },
        "route_presets": cfg.get("route_presets", []),
        "grid": {"rows": city.rows, "cols": city.cols},
        "using_real_dem": getattr(city, "using_real_dem", False),
        "using_real_roads": getattr(city, "using_real_roads", False),
    }


# ---------------------------------------------------------------
# Export endpoints (GeoTIFF and GeoJSON download)
# ---------------------------------------------------------------

@router.get("/export/geojson")
def export_geojson(timestep: int = Query(default=60)) -> StreamingResponse:
    """Export flood map as downloadable GeoJSON file."""
    engine = current_engine()
    data = engine.get_flood_geojson(timestep_minute=timestep)
    content = json.dumps(data, indent=2).encode("utf-8")
    city_key = get_active_city_key()
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/geo+json",
        headers={"Content-Disposition": f"attachment; filename={city_key}_flood_map_t{timestep}min.geojson"},
    )


@router.get("/export/geotiff")
def export_geotiff(timestep: int = Query(default=60)) -> StreamingResponse:
    """Export flood depth grid as downloadable GeoTIFF raster."""
    try:
        import rasterio
        from rasterio.transform import from_bounds
        from rasterio.crs import CRS

        city = current_city()
        engine = current_engine()

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
                description=f"{city.city_name} flood depth prediction (cm)",
                timestep_minutes=str(timestep),
                scenario=engine.last_result.scenario if engine.last_result else "unknown",
            )

        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="image/tiff",
            headers={"Content-Disposition": f"attachment; filename={city.city_key}_flood_depth_t{timestep}min.tif"},
        )

    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="rasterio not installed. Install it with: pip install rasterio"
        )


@router.get("/dem")
def get_dem_grid() -> Dict[str, Any]:
    """Returns DEM elevation grid and terrain statistics for active city."""
    city = current_city()
    return {
        "city_key": city.city_key,
        "city_name": city.city_name,
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
