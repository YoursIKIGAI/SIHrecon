"""
Fix 1 — Real SRTM DEM integration + Fix 8 multi-city support.
Fix 4 — Real OSM road network via osmnx with caching + fallback.

Replaces the synthetic DEM generator with a real GeoTIFF loader.
Replaces the 15-node fake road graph with real OpenStreetMap roads.
Falls back to synthetic generators if real data files / osmnx unavailable.
"""
import numpy as np
import networkx as nx
import json
import os
import pickle
from typing import Dict, List, Tuple, Any, Optional

SEED = 42


class CityData:
    def __init__(self, city_config: Optional[Dict] = None):
        np.random.seed(SEED)

        # --- Load city config (Fix 8: multi-city) ---
        if city_config is None:
            from .city_configs import get_city_config
            city_config = get_city_config()

        self.city_key = city_config.get("name", "mumbai")
        self.min_lat = city_config["min_lat"]
        self.max_lat = city_config["max_lat"]
        self.min_lon = city_config["min_lon"]
        self.max_lon = city_config["max_lon"]
        self.rows = city_config.get("rows", 40)
        self.cols = city_config.get("cols", 50)
        self.cell_width_m = 115.0
        self.cell_height_m = 111.0
        self.cell_area_m2 = self.cell_width_m * self.cell_height_m

        self.lats = np.linspace(self.min_lat, self.max_lat, self.rows)
        self.lons = np.linspace(self.min_lon, self.max_lon, self.cols)

        # --- Fix 1: Try to load real SRTM DEM ---
        dem_file = city_config.get("dem_file", "")
        self.dem = self._load_real_dem(dem_file) if (dem_file and os.path.exists(dem_file)) else self._generate_dem()
        self.using_real_dem = (dem_file and os.path.exists(dem_file))

        # --- Fix 4: Try to load OSM road network ---
        osm_cache = os.path.join(os.path.dirname(__file__), "roads", f"{city_config.get('name','mumbai').split()[0].lower()}_osm.pkl")
        self.road_nodes, self.road_edges, self.road_graph = self._load_osm_road_network(osm_cache)
        self.using_real_roads = getattr(self, '_used_osm', False)

        # --- Drainage network (always generated — real topology not yet available) ---
        self.drain_nodes, self.drain_edges, self.drain_graph = self._generate_drainage_network()

    # ---------------------------------------------------------------
    # FIX 1 — Real SRTM DEM Loader
    # ---------------------------------------------------------------
    def _load_real_dem(self, tif_path: str) -> np.ndarray:
        """Load and clip a real GeoTIFF DEM to the city bounding box."""
        try:
            import rasterio
            from rasterio.windows import from_bounds
            from scipy.ndimage import zoom

            with rasterio.open(tif_path) as src:
                window = from_bounds(
                    self.min_lon, self.min_lat,
                    self.max_lon, self.max_lat,
                    src.transform
                )
                dem_raw = src.read(1, window=window).astype(np.float32)
                dem_raw = np.where(dem_raw < -9000, np.nan, dem_raw)

            # Fill NaN with interpolated values
            from scipy.ndimage import generic_filter
            nan_mask = np.isnan(dem_raw)
            if nan_mask.any():
                dem_raw[nan_mask] = np.nanmean(dem_raw)

            # Resample to target grid size
            zoom_r = self.rows / dem_raw.shape[0]
            zoom_c = self.cols / dem_raw.shape[1]
            dem_resampled = zoom(dem_raw, (zoom_r, zoom_c), order=1)
            dem_resampled = np.clip(dem_resampled, 1.0, 200.0)
            return np.round(dem_resampled.astype(np.float32), 2)

        except Exception as e:
            print(f"[CityData] Could not load real DEM from {tif_path}: {e}. Falling back to synthetic.")
            return self._generate_dem()

    # ---------------------------------------------------------------
    # Synthetic DEM fallback (unchanged from original)
    # ---------------------------------------------------------------
    def _generate_dem(self) -> np.ndarray:
        col_grid, row_grid = np.meshgrid(np.arange(self.cols), np.arange(self.rows))
        base_slope = 2.0 + (col_grid / (self.cols - 1)) ** 1.4 * 36.0
        ns_wave = 3.0 * np.sin(row_grid / 6.0) + 2.0 * np.cos(col_grid / 8.0)
        dem = base_slope + ns_wave

        # Carve known flood-prone urban depressions
        r1, c1 = 18, 22
        dist1 = np.sqrt((row_grid - r1)**2 + (col_grid - c1)**2)
        sink1 = 7.5 * np.exp(-(dist1**2) / (2 * 2.8**2))

        r2, c2 = 12, 14
        dist2 = np.sqrt((row_grid - r2)**2 + (col_grid - c2)**2)
        sink2 = 6.0 * np.exp(-(dist2**2) / (2 * 3.5**2))

        r3, c3 = 26, 28
        dist3 = np.sqrt((row_grid - r3)**2 + (col_grid - c3)**2)
        sink3 = 8.0 * np.exp(-(dist3**2) / (2 * 2.5**2))

        r4, c4 = 32, 16
        dist4 = np.sqrt((row_grid - r4)**2 + (col_grid - c4)**2)
        sink4 = 5.0 * np.exp(-(dist4**2) / (2 * 4.0**2))

        dem = dem - sink1 - sink2 - sink3 - sink4
        dem = np.clip(dem, 1.2, 55.0)

        try:
            from scipy.ndimage import gaussian_filter
            dem = gaussian_filter(dem, sigma=1.0)
        except Exception:
            pass

        return np.round(dem, 2).astype(np.float32)

    # ---------------------------------------------------------------
    # Coordinate helpers
    # ---------------------------------------------------------------
    def lat_lon_to_cell(self, lat: float, lon: float) -> Tuple[int, int]:
        r = int(np.clip(np.round((lat - self.min_lat) / (self.max_lat - self.min_lat) * (self.rows - 1)), 0, self.rows - 1))
        c = int(np.clip(np.round((lon - self.min_lon) / (self.max_lon - self.min_lon) * (self.cols - 1)), 0, self.cols - 1))
        return r, c

    def cell_to_lat_lon(self, r: int, c: int) -> Tuple[float, float]:
        lat = self.min_lat + (r / (self.rows - 1)) * (self.max_lat - self.min_lat)
        lon = self.min_lon + (c / (self.cols - 1)) * (self.max_lon - self.min_lon)
        return float(lat), float(lon)

    def _calc_dist_m(self, lat1, lon1, lat2, lon2) -> float:
        R = 6371000.0
        phi1, phi2 = np.radians(lat1), np.radians(lat2)
        dphi = np.radians(lat2 - lat1)
        dlambda = np.radians(lon2 - lon1)
        a = np.sin(dphi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2)**2
        return float(2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a)))

    # ---------------------------------------------------------------
    # FIX 4 — OSM Road Network (with cache + fallback)
    # ---------------------------------------------------------------
    def _load_osm_road_network(self, cache_path: str):
        """Try loading real OSM road graph via osmnx. Cache to disk."""
        self._used_osm = False

        # Try loading from cache first
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "rb") as f:
                    data = pickle.load(f)
                print(f"[CityData] Loaded cached OSM road network ({len(data['nodes'])} nodes, {len(data['edges'])} edges)")
                self._used_osm = True
                return data["nodes"], data["edges"], data["graph"]
            except Exception as e:
                print(f"[CityData] Cache load failed: {e}")

        # Try downloading via osmnx
        try:
            import osmnx as ox
            print("[CityData] Downloading OSM road network (this may take 30-60s)...")
            G_osm = ox.graph_from_bbox(
                north=self.max_lat, south=self.min_lat,
                east=self.max_lon, west=self.min_lon,
                network_type='drive',
                simplify=True
            )
            # Simplify if very large
            if len(G_osm.edges) > 3000:
                G_osm = ox.simplify_graph(G_osm)

            nodes, edges, graph = self._convert_osm_to_internal(G_osm)

            # Save cache
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, "wb") as f:
                pickle.dump({"nodes": nodes, "edges": edges, "graph": graph}, f)

            print(f"[CityData] OSM road network loaded: {len(nodes)} nodes, {len(edges)} edges")
            self._used_osm = True
            return nodes, edges, graph

        except ImportError:
            print("[CityData] osmnx not installed. Falling back to synthetic road network.")
        except Exception as e:
            print(f"[CityData] OSM download failed: {e}. Falling back to synthetic road network.")

        return self._generate_road_network()

    def _convert_osm_to_internal(self, G_osm):
        """Convert osmnx graph to internal format with elevation and grid cells."""
        try:
            import osmnx as ox
        except ImportError:
            return self._generate_road_network()

        G_internal = nx.DiGraph()
        nodes_dict = {}

        # Process nodes
        for nid, data in G_osm.nodes(data=True):
            lat = data.get("y", self.min_lat)
            lon = data.get("x", self.min_lon)
            r, c = self.lat_lon_to_cell(lat, lon)
            elev = float(self.dem[r, c])
            nid_str = str(nid)
            node_data = {
                "id": nid_str,
                "name": data.get("name", f"Node_{nid_str[-4:]}"),
                "lat": lat,
                "lon": lon,
                "elevation_m": elev,
                "grid_r": r,
                "grid_c": c,
            }
            nodes_dict[nid_str] = node_data
            G_internal.add_node(nid_str, **node_data)

        edges_list = []
        edge_counter = 1
        mean_elevation = float(np.mean(self.dem))

        for u, v, data in G_osm.edges(data=True):
            u_str, v_str = str(u), str(v)
            if u_str not in nodes_dict or v_str not in nodes_dict:
                continue

            nu = nodes_dict[u_str]
            nv = nodes_dict[v_str]
            length_m = float(data.get("length", self._calc_dist_m(nu["lat"], nu["lon"], nv["lat"], nv["lon"])))
            speed_kmh = float(data.get("maxspeed", 40) if isinstance(data.get("maxspeed"), (int, float)) else 40)
            speed_ms = (speed_kmh * 1000.0) / 3600.0
            base_time_sec = length_m / max(speed_ms, 1.0)

            # Interpolate path cells
            num_steps = max(3, int(length_m / 80.0))
            path_lats = np.linspace(nu["lat"], nv["lat"], num_steps)
            path_lons = np.linspace(nu["lon"], nv["lon"], num_steps)
            coords = [[float(lon), float(lat)] for lat, lon in zip(path_lats, path_lons)]
            cells = []
            elevations = []
            for lat, lon in zip(path_lats, path_lons):
                r, c = self.lat_lon_to_cell(lat, lon)
                cells.append((r, c))
                elevations.append(float(self.dem[r, c]))

            avg_elevation = float(np.mean(elevations))
            min_elevation = float(np.min(elevations))
            is_elevated = avg_elevation > (mean_elevation + 3.0)

            road_name = data.get("name", f"Road_{edge_counter:04d}")
            if isinstance(road_name, list):
                road_name = road_name[0]

            e_id = f"R_{edge_counter:04d}_F"
            edge_data = {
                "id": e_id,
                "from_node": u_str,
                "to_node": v_str,
                "name": str(road_name),
                "length_m": round(length_m, 1),
                "speed_kmh": speed_kmh,
                "base_time_sec": round(base_time_sec, 1),
                "is_elevated": is_elevated,
                "coordinates": coords,
                "cells": list(set(cells)),
                "avg_elevation_m": round(avg_elevation, 1),
                "min_elevation_m": round(min_elevation, 1),
            }
            edges_list.append(edge_data)
            G_internal.add_edge(u_str, v_str, **edge_data)
            edge_counter += 1

        return nodes_dict, edges_list, G_internal

    # ---------------------------------------------------------------
    # Synthetic road network fallback (original, unchanged)
    # ---------------------------------------------------------------
    def _generate_road_network(self) -> Tuple[Dict, List, nx.DiGraph]:
        G = nx.DiGraph()
        nodes = {
            "N_DOWNTOWN": {"id": "N_DOWNTOWN", "name": "Downtown Central Station", "lat": 19.062, "lon": 72.870},
            "N_MILAN_NORTH": {"id": "N_MILAN_NORTH", "name": "Milan North Junction", "lat": 19.077, "lon": 72.874},
            "N_MILAN_SUBWAY": {"id": "N_MILAN_SUBWAY", "name": "Milan Subway Dip", "lat": 19.073, "lon": 72.874},
            "N_MILAN_SOUTH": {"id": "N_MILAN_SOUTH", "name": "Milan South Junction", "lat": 19.068, "lon": 72.873},
            "N_KINGS_CIRCLE": {"id": "N_KINGS_CIRCLE", "name": "King's Circle Junction", "lat": 19.067, "lon": 72.864},
            "N_AIRPORT": {"id": "N_AIRPORT", "name": "Metro Airport Terminal", "lat": 19.088, "lon": 72.868},
            "N_TECH_PARK": {"id": "N_TECH_PARK", "name": "East Tech City", "lat": 19.085, "lon": 72.898},
            "N_EAST_RIDGE": {"id": "N_EAST_RIDGE", "name": "Eastern Ridge Interchange", "lat": 19.070, "lon": 72.895},
            "N_WEST_COAST": {"id": "N_WEST_COAST", "name": "West Coast Harbor Gate", "lat": 19.065, "lon": 72.854},
            "N_NORTH_GATE": {"id": "N_NORTH_GATE", "name": "North City Gate", "lat": 19.092, "lon": 72.875},
            "N_SOUTH_GATE": {"id": "N_SOUTH_GATE", "name": "South Port Entrance", "lat": 19.058, "lon": 72.862},
            "N_CREEK_BRIDGE": {"id": "N_CREEK_BRIDGE", "name": "Kurla Creek Bridge", "lat": 19.082, "lon": 72.883},
            "N_MED_CENTER": {"id": "N_MED_CENTER", "name": "Central Emergency Hospital", "lat": 19.076, "lon": 72.888},
            "N_HIGHWAY_BYPASS_N": {"id": "N_HIGHWAY_BYPASS_N", "name": "Elevated Expressway North", "lat": 19.086, "lon": 72.890},
            "N_HIGHWAY_BYPASS_S": {"id": "N_HIGHWAY_BYPASS_S", "name": "Elevated Expressway South", "lat": 19.064, "lon": 72.888},
        }
        for nid, data in nodes.items():
            r, c = self.lat_lon_to_cell(data["lat"], data["lon"])
            data["elevation_m"] = float(self.dem[r, c])
            data["grid_r"] = r
            data["grid_c"] = c
            G.add_node(nid, **data)

        raw_edges = [
            ("N_DOWNTOWN", "N_MILAN_SOUTH", "Downtown Arterial South", 45, False),
            ("N_MILAN_SOUTH", "N_MILAN_SUBWAY", "Milan Subway Approach South", 40, False),
            ("N_MILAN_SUBWAY", "N_MILAN_NORTH", "Milan Subway Underpass", 40, False),
            ("N_MILAN_NORTH", "N_AIRPORT", "Airport Central Boulevard", 55, False),
            ("N_DOWNTOWN", "N_HIGHWAY_BYPASS_S", "Southern Link to Elevated Expressway", 50, False),
            ("N_HIGHWAY_BYPASS_S", "N_EAST_RIDGE", "Eastern Foothill Viaduct", 65, True),
            ("N_EAST_RIDGE", "N_MED_CENTER", "Emergency Hospital Flyover", 60, True),
            ("N_MED_CENTER", "N_HIGHWAY_BYPASS_N", "Elevated Expressway Central", 70, True),
            ("N_HIGHWAY_BYPASS_N", "N_TECH_PARK", "Tech Park Spur", 60, False),
            ("N_HIGHWAY_BYPASS_N", "N_AIRPORT", "Airport High-Level Connector", 65, True),
            ("N_DOWNTOWN", "N_KINGS_CIRCLE", "King's Avenue Link", 40, False),
            ("N_KINGS_CIRCLE", "N_MILAN_SOUTH", "King's Cross Connection", 40, False),
            ("N_KINGS_CIRCLE", "N_WEST_COAST", "Harbor Promenade", 50, False),
            ("N_WEST_COAST", "N_AIRPORT", "West Coastal Parkway", 60, False),
            ("N_SOUTH_GATE", "N_DOWNTOWN", "South Port Approach", 45, False),
            ("N_SOUTH_GATE", "N_KINGS_CIRCLE", "South King's Bypass", 40, False),
            ("N_MILAN_NORTH", "N_NORTH_GATE", "North Gateway Avenue", 50, False),
            ("N_NORTH_GATE", "N_AIRPORT", "Airport North Loop", 45, False),
            ("N_MILAN_NORTH", "N_CREEK_BRIDGE", "Creek Cross Link", 45, False),
            ("N_CREEK_BRIDGE", "N_MED_CENTER", "Medical Corridor East", 50, False),
            ("N_CREEK_BRIDGE", "N_HIGHWAY_BYPASS_N", "Expressway Creek Ramp", 55, False),
            ("N_MILAN_SUBWAY", "N_MED_CENTER", "Central East Traverse", 35, False),
        ]

        edges_list = []
        edge_counter = 1
        for u, v, name, speed_kmh, is_elevated in raw_edges:
            node_u = nodes[u]
            node_v = nodes[v]
            length_m = self._calc_dist_m(node_u["lat"], node_u["lon"], node_v["lat"], node_v["lon"])
            speed_ms = (speed_kmh * 1000.0) / 3600.0
            base_time_sec = length_m / speed_ms
            num_steps = max(3, int(length_m / 100.0))
            path_lats = np.linspace(node_u["lat"], node_v["lat"], num_steps)
            path_lons = np.linspace(node_u["lon"], node_v["lon"], num_steps)
            coords = [[float(lon), float(lat)] for lat, lon in zip(path_lats, path_lons)]
            cells = []
            elevations = []
            for lat, lon in zip(path_lats, path_lons):
                r, c = self.lat_lon_to_cell(lat, lon)
                cells.append((r, c))
                elevations.append(float(self.dem[r, c]))

            for direction, (nu, nv, cds) in enumerate([(node_u, node_v, coords), (node_v, node_u, list(reversed(coords)))]):
                suffix = "F" if direction == 0 else "R"
                e_id = f"R_{edge_counter:03d}_{suffix}"
                edge_data = {
                    "id": e_id,
                    "from_node": u if direction == 0 else v,
                    "to_node": v if direction == 0 else u,
                    "name": name if direction == 0 else f"{name} (Reverse)",
                    "length_m": round(length_m, 1),
                    "speed_kmh": speed_kmh,
                    "base_time_sec": round(base_time_sec, 1),
                    "is_elevated": is_elevated,
                    "coordinates": cds,
                    "cells": list(set(cells)),
                    "avg_elevation_m": round(float(np.mean(elevations)), 1),
                    "min_elevation_m": round(float(np.min(elevations)), 1),
                }
                edges_list.append(edge_data)
                fn = u if direction == 0 else v
                tn = v if direction == 0 else u
                G.add_edge(fn, tn, **edge_data)
            edge_counter += 1

        return nodes, edges_list, G

    # ---------------------------------------------------------------
    # Drainage network (unchanged)
    # ---------------------------------------------------------------
    def _generate_drainage_network(self) -> Tuple[Dict, List, nx.DiGraph]:
        G = nx.DiGraph()
        drain_nodes_spec = [
            ("D_IN_EAST_01", "inlet", 19.085, 72.898, "East Tech Park Catch Basin", 8.0),
            ("D_IN_EAST_02", "inlet", 19.076, 72.888, "Medical Center Catch Basin", 10.0),
            ("D_MH_EAST_TRUNK", "manhole", 19.078, 72.885, "East Foothills Collector Manhole", 35.0),
            ("D_IN_MILAN_N", "inlet", 19.077, 72.874, "Milan North Street Inlet", 12.0),
            ("D_IN_MILAN_DIP", "inlet", 19.073, 72.874, "Milan Subway Low Catch Basin", 15.0),
            ("D_MH_MILAN_SINK", "manhole", 19.073, 72.873, "Milan Subway Pumping Chamber", 45.0),
            ("D_IN_MILAN_S", "inlet", 19.068, 72.873, "Milan South Street Drain", 10.0),
            ("D_IN_KINGS_01", "inlet", 19.067, 72.864, "King's Circle Storm Inlet 1", 12.0),
            ("D_IN_KINGS_02", "inlet", 19.066, 72.865, "King's Circle Storm Inlet 2", 12.0),
            ("D_MH_KINGS", "manhole", 19.067, 72.862, "King's Circle Sump Chamber", 40.0),
            ("D_IN_DT_01", "inlet", 19.062, 72.870, "Downtown Central Station Inlet", 14.0),
            ("D_MH_DT_CENTRAL", "manhole", 19.063, 72.868, "Downtown Main Interceptor Manhole", 50.0),
            ("D_IN_AIRPORT", "inlet", 19.088, 72.868, "Airport Runoff Drain Inlet", 20.0),
            ("D_MH_NORTH_TRUNK", "manhole", 19.084, 72.867, "North Trunk Interceptor", 50.0),
            ("D_TRUNK_CENTRAL", "junction", 19.070, 72.860, "Central Storm Trunk Culvert", 120.0),
            ("D_TRUNK_NORTH", "junction", 19.080, 72.858, "North Relief Storm Canal", 100.0),
            ("D_OUTFALL_BAY", "outfall", 19.065, 72.851, "Western Bay Tidal Outfall", 500.0),
            ("D_OUTFALL_CREEK", "outfall", 19.078, 72.852, "Creek Storm Gate Outfall", 500.0),
        ]
        drain_nodes = {}
        for nid, ntype, lat, lon, street_loc, cap_m3 in drain_nodes_spec:
            r, c = self.lat_lon_to_cell(lat, lon)
            elev = float(self.dem[r, c])
            node_data = {
                "id": nid, "name": nid, "type": ntype, "lat": lat, "lon": lon,
                "elevation_m": round(elev, 2), "storage_capacity_m3": cap_m3,
                "current_water_m3": 0.0, "street_location": street_loc,
                "grid_r": r, "grid_c": c,
            }
            drain_nodes[nid] = node_data
            G.add_node(nid, **node_data)

        pipe_specs = [
            ("D_IN_EAST_01", "D_MH_EAST_TRUNK", 250, 0.6, 1.2),
            ("D_IN_EAST_02", "D_MH_EAST_TRUNK", 220, 0.6, 1.2),
            ("D_MH_EAST_TRUNK", "D_TRUNK_CENTRAL", 600, 1.2, 4.5),
            ("D_IN_MILAN_N", "D_MH_MILAN_SINK", 180, 0.7, 1.5),
            ("D_IN_MILAN_DIP", "D_MH_MILAN_SINK", 100, 0.8, 2.0),
            ("D_IN_MILAN_S", "D_MH_MILAN_SINK", 160, 0.7, 1.5),
            ("D_MH_MILAN_SINK", "D_TRUNK_CENTRAL", 450, 1.0, 3.2),
            ("D_IN_KINGS_01", "D_MH_KINGS", 120, 0.7, 1.6),
            ("D_IN_KINGS_02", "D_MH_KINGS", 130, 0.7, 1.6),
            ("D_MH_KINGS", "D_TRUNK_CENTRAL", 350, 1.1, 3.8),
            ("D_IN_DT_01", "D_MH_DT_CENTRAL", 140, 0.8, 1.8),
            ("D_MH_DT_CENTRAL", "D_TRUNK_CENTRAL", 320, 1.2, 4.0),
            ("D_IN_AIRPORT", "D_MH_NORTH_TRUNK", 250, 0.9, 2.5),
            ("D_MH_NORTH_TRUNK", "D_TRUNK_NORTH", 380, 1.4, 5.5),
            ("D_TRUNK_CENTRAL", "D_OUTFALL_BAY", 520, 2.0, 12.0),
            ("D_TRUNK_NORTH", "D_OUTFALL_CREEK", 480, 1.8, 10.0),
            ("D_TRUNK_NORTH", "D_TRUNK_CENTRAL", 400, 1.2, 4.0),
        ]
        drain_edges = []
        for i, (u, v, length, diam, cap) in enumerate(pipe_specs, 1):
            nu = drain_nodes[u]
            nv = drain_nodes[v]
            slope = max(0.001, (nu["elevation_m"] - nv["elevation_m"]) / length)
            edge_data = {
                "id": f"PIPE_{i:02d}", "from_node": u, "to_node": v,
                "length_m": length, "diameter_m": diam,
                "slope": round(float(slope), 4), "capacity_m3_s": cap,
                "current_flow_m3_s": 0.0,
                "coordinates": [[nu["lon"], nu["lat"]], [nv["lon"], nv["lat"]]],
            }
            drain_edges.append(edge_data)
            G.add_edge(u, v, **edge_data)

        return drain_nodes, drain_edges, G


# Singleton — re-created when city changes
_city_instance: Optional[CityData] = None
_city_key: str = "mumbai"


def get_city_data(city_config: Optional[Dict] = None) -> CityData:
    global _city_instance, _city_key
    from .city_configs import get_city_config, get_active_city_key
    cfg = city_config or get_city_config()
    key = cfg.get("name", get_active_city_key())
    if _city_instance is None or key != _city_key:
        _city_instance = CityData(cfg)
        _city_key = key
    return _city_instance


def reset_city_instance():
    global _city_instance, _city_key
    _city_instance = None
    _city_key = "mumbai"
