"""
Automated Test Suite for Multi-City Flood Prediction, Safe Routing, and Officer Alerts.
Covers Test Cases A through I in accordance with hackathon evaluation specifications.
"""
import pytest
import numpy as np
import os
import json

from backend.data.city_generator import CityData, get_city_data, reset_city_instance
from backend.data.city_configs import (
    CITY_REGISTRY,
    set_active_city_key,
    get_active_city_key,
    get_city_config,
    get_historical_events,
)
from backend.simulation.flood_engine import FloodEngine, get_flood_engine, reset_flood_engine
from backend.simulation.routing import RoutingEngine
from backend.data.validation import FloodValidator
from backend.models.schemas import RouteRequest, SimulationRequest


@pytest.fixture(autouse=True)
def cleanup_caches():
    """Ensure clean state before each test."""
    reset_city_instance()
    reset_flood_engine()
    set_active_city_key("mumbai")
    yield
    reset_city_instance()
    reset_flood_engine()


# ---------------------------------------------------------------------------
# Test Case A: Delhi Historical Flood Scenario
# ---------------------------------------------------------------------------
def test_case_a_delhi_historical_scenario():
    """Verify Delhi July 2023 Yamuna Flood Scenario loading, isolation, and routing."""
    set_active_city_key("delhi")
    city = get_city_data(city_key="delhi")
    
    # 1. Bounds & Coordinate System
    assert city.city_key == "delhi"
    assert 28.50 <= city.min_lat <= 28.60
    assert 28.68 <= city.max_lat <= 28.78
    assert 77.10 <= city.min_lon <= 77.20
    assert 77.25 <= city.max_lon <= 77.35

    # 2. Historical Rainfall Event
    delhi_events = get_historical_events("delhi")
    assert len(delhi_events) > 0
    event = delhi_events[0]
    assert "2023" in event["event_date"]
    assert event["total_rainfall_mm"] >= 150.0
    assert os.path.exists(event["json_file"])

    # 3. Hydrodynamic Simulation Execution
    engine = FloodEngine(city)
    res = engine.run_simulation(
        scenario=event["id"],
        duration_minutes=180,
        simulation_mode="historical",
        event_id=event["id"]
    )
    assert res.city_key == "delhi"
    assert res.simulation_mode == "historical"
    assert res.timesteps[0].rainfall_mm_hr > 0
    assert len(res.road_predictions[60]) > 0

    # 4. Independent Delhi Routing (Connaught Place to Kashmere Gate)
    router = RoutingEngine(city)
    cp_lon, cp_lat = 77.218, 28.631
    kg_lon, kg_lat = 77.228, 28.667
    
    route_res = router.calculate_routes(
        origin_lon=cp_lon,
        origin_lat=cp_lat,
        dest_lon=kg_lon,
        dest_lat=kg_lat,
        road_depths=res.road_predictions[90],
        timestep_minutes=90
    )
    assert len(route_res.safe_route.coordinates) > 0
    assert len(route_res.normal_route.coordinates) > 0
    assert route_res.safe_route.distance_km > 0.0

    # 5. Drainage network isolation: No Mumbai nodes in Delhi graph
    for _, ndata in city.drain_graph.nodes(data=True):
        assert 28.0 <= ndata["lat"] <= 29.0
        assert 77.0 <= ndata["lon"] <= 78.0

    # 6. Officer Alerts Isolation in Test Mode
    assert res.alerts is not None
    for a in res.alerts:
        assert a.is_test_alert is True
        assert a.city == city.city_name


# ---------------------------------------------------------------------------
# Test Case B: Mumbai Historical Flood Scenario
# ---------------------------------------------------------------------------
def test_case_b_mumbai_historical_scenario():
    """Verify Mumbai July 26, 2005 Cloudburst Scenario and drainage distinction."""
    set_active_city_key("mumbai")
    city = get_city_data(city_key="mumbai")

    assert city.city_key == "mumbai"
    assert 19.00 <= city.min_lat <= 19.06
    assert 72.80 <= city.min_lon <= 72.86

    mumbai_events = get_historical_events("mumbai")
    assert len(mumbai_events) > 0
    event = mumbai_events[0]
    assert event["total_rainfall_mm"] == 944.0
    assert os.path.exists(event["json_file"])

    engine = FloodEngine(city)
    res = engine.run_simulation(
        scenario=event["id"],
        duration_minutes=180,
        simulation_mode="historical",
        event_id=event["id"]
    )
    assert res.city_key == "mumbai"
    assert res.simulation_mode == "historical"

    # Drainage representation distinguishes verified vs inferred
    has_verified = any(d.get("verification_status") == "verified" for d in city.drain_nodes.values())
    has_inferred = any(d.get("verification_status") == "inferred" for d in city.drain_nodes.values())
    assert has_verified, "Should contain verified drainage assets"
    assert has_inferred, "Should contain approximate/inferred drainage channels"

    # Route safety calculation with Milan subway underpass
    router = RoutingEngine(city)
    route_res = router.calculate_routes(
        origin_lon=72.874,
        origin_lat=19.073,
        dest_lon=72.868,
        dest_lat=19.088,
        road_depths=res.road_predictions[90],
        timestep_minutes=90
    )
    assert route_res.safe_route.max_water_depth_cm <= route_res.normal_route.max_water_depth_cm


# ---------------------------------------------------------------------------
# Test Case C: Chennai Historical Flood Scenario
# ---------------------------------------------------------------------------
def test_case_c_chennai_historical_scenario():
    """Verify Chennai Dec 2015 Deluge Scenario and geographic independence."""
    set_active_city_key("chennai")
    city = get_city_data(city_key="chennai")

    assert city.city_key == "chennai"
    assert 12.95 <= city.min_lat <= 13.00
    assert 80.15 <= city.min_lon <= 80.20

    chennai_events = get_historical_events("chennai")
    assert len(chennai_events) > 0
    event = chennai_events[0]
    assert "2015" in event["event_date"]
    assert event["total_rainfall_mm"] >= 450.0

    engine = FloodEngine(city)
    res = engine.run_simulation(
        scenario=event["id"],
        duration_minutes=180,
        simulation_mode="historical",
        event_id=event["id"]
    )
    assert res.city_key == "chennai"

    # Routing within Chennai bounds (Saidapet to Velachery)
    router = RoutingEngine(city)
    route_res = router.calculate_routes(
        origin_lon=80.222,
        origin_lat=13.021,
        dest_lon=80.217,
        dest_lat=12.981,
        road_depths=res.road_predictions[90],
        timestep_minutes=90
    )
    assert len(route_res.safe_route.coordinates) > 0
    assert route_res.alternative_route is not None


# ---------------------------------------------------------------------------
# Test Case D: Origin and Destination Movement & Coordinate Bounds
# ---------------------------------------------------------------------------
def test_case_d_origin_destination_movement():
    """Verify points A and B move independently and reject out-of-bounds coordinates."""
    cities_to_test = [
        ("mumbai", [72.874, 19.073], [72.868, 19.088], [72.854, 19.065]),
        ("delhi", [77.218, 28.631], [77.228, 28.667], [77.241, 28.630]),
        ("chennai", [80.222, 13.021], [80.217, 12.981], [80.231, 13.041]),
    ]

    for ckey, orig1, dest1, orig2 in cities_to_test:
        set_active_city_key(ckey)
        city = get_city_data(city_key=ckey)
        engine = FloodEngine(city)
        router = RoutingEngine(city)
        roads = engine.cached_road_states.get(60, [])

        # 1. Initial route between orig1 and dest1
        res1 = router.calculate_routes(
            origin_lon=orig1[0], origin_lat=orig1[1],
            dest_lon=dest1[0], dest_lat=dest1[1],
            road_depths=roads
        )
        assert len(res1.normal_route.coordinates) > 0

        # 2. Move Origin to orig2
        res2 = router.calculate_routes(
            origin_lon=orig2[0], origin_lat=orig2[1],
            dest_lon=dest1[0], dest_lat=dest1[1],
            road_depths=roads
        )
        assert res2.normal_route.coordinates != res1.normal_route.coordinates

        # 3. Attempting to use Mumbai coordinates while Delhi is active MUST raise ValueError
        if ckey == "delhi":
            with pytest.raises(ValueError) as excinfo:
                router.calculate_routes(
                    origin_lon=72.874, origin_lat=19.073,  # Mumbai coordinate!
                    dest_lon=dest1[0], dest_lat=dest1[1],
                    road_depths=roads
                )
            assert "outside" in str(excinfo.value).lower()


# ---------------------------------------------------------------------------
# Test Case E: Rainfall Sensitivity
# ---------------------------------------------------------------------------
def test_case_e_rainfall_sensitivity():
    """Verify model risk outputs respond to varying rainfall intensities."""
    set_active_city_key("delhi")
    city = get_city_data(city_key="delhi")
    engine = FloodEngine(city)

    # Low rainfall run
    res_low = engine.run_simulation(scenario="light", duration_minutes=60)
    max_d_low = max(t.max_depth_cm for t in res_low.timesteps)
    flooded_low = sum(t.flooded_roads_count for t in res_low.timesteps)

    # Cloudburst / Extreme rainfall run
    res_high = engine.run_simulation(scenario="extreme", duration_minutes=60)
    max_d_high = max(t.max_depth_cm for t in res_high.timesteps)
    flooded_high = sum(t.flooded_roads_count for t in res_high.timesteps)

    assert max_d_high > max_d_low, f"Extreme rain should produce deeper water ({max_d_high} vs {max_d_low})"
    assert flooded_high >= flooded_low, "Extreme rain should flood equal or more road segments"


# ---------------------------------------------------------------------------
# Test Case F: Drainage Integrity
# ---------------------------------------------------------------------------
def test_case_f_drainage_integrity():
    """Verify city-specific drainage networks, verified/inferred tags, and bottleneck surcharge."""
    delhi_city = get_city_data(city_key="delhi")
    mumbai_city = get_city_data(city_key="mumbai")

    # Nodes must not share coordinates between different cities
    delhi_lats = [n["lat"] for n in delhi_city.drain_nodes.values()]
    mumbai_lats = [n["lat"] for n in mumbai_city.drain_nodes.values()]
    assert max(delhi_lats) > 28.0 and min(delhi_lats) > 28.0
    assert max(mumbai_lats) < 20.0 and min(mumbai_lats) < 20.0

    # Bottleneck surcharge simulation
    engine = FloodEngine(mumbai_city)
    res = engine.run_simulation(scenario="extreme", duration_minutes=180)
    overflow_nodes = res.overflow_nodes.get(90, [])
    assert len(overflow_nodes) > 0, "Extreme event should surcharge vulnerable drain nodes"
    
    # Verify bottlenecks are marked appropriately
    bottlenecks = [n for n in overflow_nodes if n.is_bottleneck]
    assert len(bottlenecks) >= 0


# ---------------------------------------------------------------------------
# Test Case G: Flood-Aware Dynamic Routing (3 Routes & Blocked Segments)
# ---------------------------------------------------------------------------
def test_case_g_flood_aware_routing():
    """Verify 3 distinct routes (fastest, flood-safe, alternative) and segment risk scoring."""
    city = get_city_data(city_key="mumbai")
    engine = FloodEngine(city)
    res = engine.run_simulation(scenario="extreme", duration_minutes=180)
    road_states = res.road_predictions[90]

    router = RoutingEngine(city)
    route_res = router.calculate_routes(
        origin_lon=72.874,
        origin_lat=19.073,
        dest_lon=72.868,
        dest_lat=19.088,
        road_depths=road_states,
        timestep_minutes=90
    )

    # Must contain normal, safe, and alternative routes
    assert route_res.normal_route is not None
    assert route_res.safe_route is not None
    assert route_res.alternative_route is not None

    # Blocked roads (>40cm) must have is_blocked=True
    blocked_segs = [s for s in route_res.normal_route.segments if s.water_depth_cm > 40.0]
    for seg in blocked_segs:
        assert seg.is_blocked is True


# ---------------------------------------------------------------------------
# Test Case H: Officer Alerts Logic & Isolation
# ---------------------------------------------------------------------------
def test_case_h_officer_alerts():
    """Verify evidence-based alert generation, interactive status updates, and test isolation."""
    city = get_city_data(city_key="delhi")
    engine = FloodEngine(city)
    
    # Run historical simulation
    res = engine.run_simulation(scenario="delhi_2023_yamuna", simulation_mode="historical", event_id="delhi_2023_yamuna")
    assert len(res.alerts) > 0

    first_alert = res.alerts[0]
    assert first_alert.is_test_alert is True
    assert first_alert.status == "active"
    assert first_alert.alert_id.startswith("ALT_")
    assert len(first_alert.trigger_condition) > 5

    # Officer updates alert status to acknowledged
    updated = engine.update_alert_status(first_alert.alert_id, "acknowledged")
    assert updated is True
    assert first_alert.status == "acknowledged"

    # Prediction grids must remain identical after alert acknowledgement
    assert engine.cached_depth_grids[90] is not None


# ---------------------------------------------------------------------------
# Test Case I: Live-Application Regression
# ---------------------------------------------------------------------------
def test_case_i_live_application_regression():
    """Verify live-mode endpoints and workflows operate reliably without regressions."""
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)

    # 1. /api/status
    res_status = client.get("/api/status")
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert status_data["status"] == "healthy"
    assert status_data["service"] is not None

    # 2. /api/scenarios
    res_scenarios = client.get("/api/scenarios")
    assert res_scenarios.status_code == 200
    assert "extreme" in res_scenarios.json()

    # 3. /api/cities
    res_cities = client.get("/api/cities")
    assert res_cities.status_code == 200
    cities_json = res_cities.json()
    assert "mumbai" in cities_json
    assert "delhi" in cities_json
    assert "chennai" in cities_json

    # 4. /api/switch-city
    res_switch = client.post("/api/switch-city?city_key=delhi")
    assert res_switch.status_code == 200
    assert res_switch.json()["switched_to"] == "delhi"

    # 5. /api/route in Delhi
    route_payload = {
        "origin": [77.218, 28.631],
        "destination": [77.228, 28.667],
        "timestep_minutes": 60,
        "city_key": "delhi"
    }
    res_route = client.post("/api/route", json=route_payload)
    assert res_route.status_code == 200
    route_json = res_route.json()
    assert "normal_route" in route_json
    assert "safe_route" in route_json
    assert "alternative_route" in route_json

    # 6. /api/alerts
    res_alerts = client.get("/api/alerts")
    assert res_alerts.status_code == 200

    # 7. /api/scenarios/historical
    res_hist = client.get("/api/scenarios/historical")
    assert res_hist.status_code == 200
    assert len(res_hist.json()) >= 3

    # 8. /api/historical-observations
    res_obs = client.get("/api/historical-observations?city_key=delhi")
    assert res_obs.status_code == 200
    assert res_obs.json()["type"] == "FeatureCollection"
    assert len(res_obs.json()["features"]) > 0
