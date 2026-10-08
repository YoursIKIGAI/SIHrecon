from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict, Any, List
import time
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
from ..data.city_generator import get_city_data
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

@router.get("/status")
def get_status() -> Dict[str, Any]:
    """System health check and engine metadata."""
    return {
        "status": "healthy",
        "service": "Urban Flood Nowcasting & Flood-Safe Routing System",
        "version": "1.1.0-ai-enhanced",
        "engine_ready": True,
        "ml_model_trained": ml_model.is_trained,
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
    """
    Return GeoJSON containing predicted flood polygons and flooded roads for a specific timestep.
    """
    return engine.get_flood_geojson(timestep_minute=timestep)

@router.get("/drainage")
def get_drainage_network() -> Dict[str, Any]:
    """
    Return the drainage network directed graph in GeoJSON format.
    Includes pipes, manholes, inlets, capacities, and overflow state.
    """
    return engine.drainage_model.to_geojson()

@router.post("/route", response_model=RouteResponse)
def compute_flood_safe_route(request: RouteRequest) -> RouteResponse:
    """
    Compute optimal flood-safe route avoiding high water depths (>40cm blocked)
    and compare it against the standard shortest route.
    """
    timestep = request.timestep_minutes if request.timestep_minutes is not None else 60
    
    # Get road flood depths at specified timestep
    road_states = engine.cached_road_states.get(timestep)
    if road_states is None:
        if engine.cached_road_states:
            closest_ts = min(engine.cached_road_states.keys(), key=lambda t: abs(t - timestep))
            road_states = engine.cached_road_states[closest_ts]
        else:
            road_states = []

    result = router_engine.calculate_routes(
        origin_lon=request.origin[0],
        origin_lat=request.origin[1],
        dest_lon=request.destination[0],
        dest_lat=request.destination[1],
        road_depths=road_states,
        timestep_minutes=timestep
    )
    return result

@router.get("/predictions", response_model=List[FloodPredictionRecord])
def get_predictions(timestep: int = Query(default=60, description="Forecast minute")) -> List[FloodPredictionRecord]:
    """
    Structured flood prediction records at grid points per hackathon specification:
    { "location": {lat, lon}, "timestamp": ..., "water_depth_cm": 37, "risk_level": "Severe" }
    """
    return engine.get_prediction_records(timestep_minute=timestep)

@router.post("/validate", response_model=ValidationMetrics)
def validate_simulation(timestep: int = Query(default=90)) -> ValidationMetrics:
    """
    Assess prediction accuracy against demonstration benchmark ground-truth.
    Returns Precision, Recall, F1-Score, and RMSE for water depth.
    """
    depth_grid = engine.cached_depth_grids.get(timestep)
    if depth_grid is None:
        depth_grid = list(engine.cached_depth_grids.values())[0]

    return validator.evaluate_predictions(predicted_depth_grid=depth_grid)

@router.post("/train", response_model=MLTrainingResponse)
def train_model(request: MLTrainingRequest = MLTrainingRequest()) -> MLTrainingResponse:
    """
    Trains the Machine Learning Flood Depth Surrogate Model on synthetic storm events.
    Computes R² score, RMSE, MAE, and feature importances.
    """
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
        "training_history": ml_model.training_history[-10:] if ml_model.training_history else []
    }

@router.get("/search-locations", response_model=List[LocationSearchResult])
def search_locations(q: str = Query(default="", description="Search query string")) -> List[LocationSearchResult]:
    """Search urban landmarks, intersections, and choke points for map navigation."""
    results = []
    q_lower = q.lower().strip()

    # Pre-defined major metropolitan POIs
    pois = [
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

    for p in pois:
        if not q_lower or q_lower in p["name"].lower() or q_lower in p["category"].lower():
            r, c = city.lat_lon_to_cell(p["lat"], p["lon"])
            elev = float(city.dem[r, c])
            results.append(LocationSearchResult(
                id=p["id"],
                name=p["name"],
                lat=p["lat"],
                lon=p["lon"],
                category=p["category"],
                elevation_m=elev
            ))

    return results

@router.get("/dem")
def get_dem_grid() -> Dict[str, Any]:
    """Returns DEM elevation grid and terrain statistics."""
    return {
        "rows": city.rows,
        "cols": city.cols,
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
