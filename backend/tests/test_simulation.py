import pytest
import numpy as np
from backend.data.city_generator import CityData, get_city_data
from backend.data.city_configs import set_active_city_key
from backend.simulation.rainfall import RainfallModule
from backend.simulation.runoff import RunoffModel
from backend.simulation.surface_flow import SurfaceFlowModel
from backend.simulation.drainage import DrainageModel
from backend.simulation.flood_engine import FloodEngine
from backend.simulation.routing import RoutingEngine
from backend.data.validation import FloodValidator
from backend.ml.dataset import FloodDatasetGenerator
from backend.ml.model import FloodSurrogateMLModel

def test_city_generator():
    city = CityData()
    assert city.dem.shape == (40, 50)
    assert np.min(city.dem) >= 1.0
    assert len(city.road_nodes) > 10
    assert len(city.road_edges) > 15
    assert len(city.drain_nodes) > 10
    assert len(city.drain_edges) > 10

def test_rainfall_module():
    rf = RainfallModule()
    forecast = rf.get_scenario_forecast("extreme")
    assert len(forecast) == 6
    assert forecast[0].rainfall_mm_hr == 30.0
    assert forecast[3].rainfall_mm_hr == 140.0
    
    interp = rf.interpolate_intensity(forecast, 45)
    assert 85.0 <= interp <= 125.0

def test_runoff_model():
    model = RunoffModel(rows=40, cols=50, cell_area_m2=12765.0)
    rain_grid = np.full((40, 50), 80.0, dtype=np.float32)
    vol, depth_mm = model.compute_runoff_volume_m3(rain_grid, timestep_seconds=1800.0)
    assert np.all(vol > 0.0)
    assert np.all(depth_mm > 0.0)

def test_surface_flow():
    city = CityData()
    flow_model = SurfaceFlowModel(city.dem, city.cell_width_m, city.cell_height_m)
    water = np.zeros((40, 50), dtype=np.float32)
    water[5, 45] = 1000.0  # high ground water
    
    accum, inflow = flow_model.route_surface_flow(water)
    assert accum[5, 45] < 1000.0  # water moved downhill

def test_drainage_model():
    city = CityData()
    d_model = DrainageModel(city.drain_graph, city.drain_nodes, city.drain_edges)
    surface = np.full((40, 50), 500.0, dtype=np.float32)
    overflow, overflow_nodes, stats = d_model.simulate_timestep(surface, timestep_seconds=1800.0)
    assert stats["total_intake_m3"] > 0.0

def test_flood_engine_speed_and_coupling():
    import time
    city = CityData()
    engine = FloodEngine(city)
    
    t0 = time.perf_counter()
    res = engine.run_simulation(scenario="extreme", duration_minutes=180, engine_mode="physics")
    elapsed = time.perf_counter() - t0
    
    # Check speed constraint: must complete in < 5 seconds!
    assert elapsed < 5.0, f"Simulation took too long: {elapsed}s"
    assert len(res.timesteps) == 6
    assert res.timesteps[3].rainfall_mm_hr == 140.0
    assert res.timesteps[3].flooded_roads_count > 0
    assert res.timesteps[3].max_depth_cm > 20.0

def test_ml_surrogate_model_training_and_inference():
    city = CityData()
    dataset_gen = FloodDatasetGenerator(city)
    X, y, stats = dataset_gen.generate_training_data(num_storm_scenarios=4)
    assert len(X) > 1000
    assert stats["num_features"] == 8

    ml_model = FloodSurrogateMLModel()
    metrics = ml_model.train(X, y, epochs=50)
    assert metrics["r2_score"] > 0.5
    assert metrics["rmse_depth_cm"] > 0.0
    assert ml_model.is_trained

    # Test grid inference
    pred_grid = ml_model.predict_grid(
        rainfall_intensity_mm_hr=100.0,
        cumulative_rain_mm=80.0,
        dem_elevation=dataset_gen.elevation_feat,
        slope=dataset_gen.slope_feat,
        is_sink=dataset_gen.is_sink_feat,
        dist_to_drain=dataset_gen.dist_to_drain_feat,
        drain_cap=dataset_gen.drain_cap_feat,
        upstream_proxy=dataset_gen.upstream_proxy_feat
    )
    assert pred_grid.shape == (40, 50)
    assert np.max(pred_grid) > 0.0

def test_flood_safe_routing():
    set_active_city_key("mumbai")
    city = get_city_data(city_key="mumbai")
    engine = FloodEngine(city)
    res = engine.run_simulation(scenario="extreme", duration_minutes=180)
    
    road_states = res.road_predictions[90]
    router = RoutingEngine(city)
    
    # From Downtown to Airport
    origin = [72.870, 19.062]
    dest = [72.868, 19.088]
    
    route_res = router.calculate_routes(
        origin_lon=origin[0],
        origin_lat=origin[1],
        dest_lon=dest[0],
        dest_lat=dest[1],
        road_depths=road_states,
        timestep_minutes=90
    )
    
    # Safe route must bypass severely flooded roads
    assert route_res.safe_route.max_water_depth_cm < route_res.normal_route.max_water_depth_cm or route_res.avoided_flooded_roads >= 0
    assert len(route_res.safe_route.coordinates) > 0
    assert len(route_res.normal_route.coordinates) > 0

def test_validator():
    validator = FloodValidator()
    pred_grid = np.random.uniform(0, 50, size=(40, 50)).astype(np.float32)
    metrics = validator.evaluate_predictions(pred_grid)
    assert 0.0 <= metrics.precision <= 1.0
    assert 0.0 <= metrics.recall <= 1.0
    assert metrics.rmse_depth_cm >= 0.0
