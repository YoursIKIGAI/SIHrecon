import numpy as np
import networkx as nx
import json
from typing import Dict, List, Tuple, Any
import os

SEED = 42

class CityData:
    def __init__(self):
        np.random.seed(SEED)
        # Geographic bounds (Metro Mumbai Basin demo area)
        self.min_lat = 19.055
        self.max_lat = 19.095
        self.min_lon = 72.850
        self.max_lon = 72.905

        self.rows = 40
        self.cols = 50
        self.cell_width_m = 115.0   # ~115m x ~111m per cell (~12,765 m2 per cell)
        self.cell_height_m = 111.0
        self.cell_area_m2 = self.cell_width_m * self.cell_height_m

        # Latitudes and Longitudes grid
        self.lats = np.linspace(self.min_lat, self.max_lat, self.rows)
        self.lons = np.linspace(self.min_lon, self.max_lon, self.cols)

        # Generate DEM
        self.dem = self._generate_dem()

        # Generate Road Network
        self.road_nodes, self.road_edges, self.road_graph = self._generate_road_network()

        # Generate Drainage Network
        self.drain_nodes, self.drain_edges, self.drain_graph = self._generate_drainage_network()

    def _generate_dem(self) -> np.ndarray:
        """
        Generates realistic urban topography:
        - Eastern hills / high ground (35m - 48m)
        - Slope sloping westward down to coastal water / creek (2.0m - 4.0m)
        - Depressions / underpasses at critical urban choke points:
          * Milan Subway Underpass (low bowl, 1.4m)
          * King's Circle Basin (low bowl, 1.7m)
          * Kurla Creek Basin (2.0m)
        """
        # East-West gradient: col 0 is west (low), col cols-1 is east (high)
        col_grid, row_grid = np.meshgrid(np.arange(self.cols), np.arange(self.rows))
        
        # Base west-to-east elevation slope: 2m at west, 38m at east
        base_slope = 2.0 + (col_grid / (self.cols - 1)) ** 1.4 * 36.0

        # Gentle North-South ridge wave
        ns_wave = 3.0 * np.sin(row_grid / 6.0) + 2.0 * np.cos(col_grid / 8.0)

        dem = base_slope + ns_wave

        # Carve out urban depressions (underpasses, low railway dips, natural flood sinks)
        # 1. Milan Subway Underpass: row 18, col 22 (approx 19.073 N, 72.874 E)
        r1, c1 = 18, 22
        dist1 = np.sqrt((row_grid - r1)**2 + (col_grid - c1)**2)
        sink1 = 7.5 * np.exp(-(dist1**2) / (2 * 2.8**2))

        # 2. King's Circle Low Basin: row 12, col 14 (approx 19.067 N, 72.865 E)
        r2, c2 = 12, 14
        dist2 = np.sqrt((row_grid - r2)**2 + (col_grid - c2)**2)
        sink2 = 6.0 * np.exp(-(dist2**2) / (2 * 3.5**2))

        # 3. Railway Underpass Dip: row 26, col 28
        r3, c3 = 26, 28
        dist3 = np.sqrt((row_grid - r3)**2 + (col_grid - c3)**2)
        sink3 = 8.0 * np.exp(-(dist3**2) / (2 * 2.5**2))

        # 4. Creek Lowland Channel: row 32, col 16
        r4, c4 = 32, 16
        dist4 = np.sqrt((row_grid - r4)**2 + (col_grid - c4)**2)
        sink4 = 5.0 * np.exp(-(dist4**2) / (2 * 4.0**2))

        dem = dem - sink1 - sink2 - sink3 - sink4

        # Ensure minimum elevation is above sea level (min 1.2 meters)
        dem = np.clip(dem, 1.2, 55.0)

        # Smooth slightly using simple convolution to create natural terrain contours
        from scipy.ndimage import gaussian_filter
        dem = gaussian_filter(dem, sigma=1.0)
        dem = np.round(dem, 2)
        return dem

    def lat_lon_to_cell(self, lat: float, lon: float) -> Tuple[int, int]:
        """Convert lat, lon to nearest grid row, col."""
        r = int(np.clip(np.round((lat - self.min_lat) / (self.max_lat - self.min_lat) * (self.rows - 1)), 0, self.rows - 1))
        c = int(np.clip(np.round((lon - self.min_lon) / (self.max_lon - self.min_lon) * (self.cols - 1)), 0, self.cols - 1))
        return r, c

    def cell_to_lat_lon(self, r: int, c: int) -> Tuple[float, float]:
        """Convert grid cell r, c to lat, lon."""
        lat = self.min_lat + (r / (self.rows - 1)) * (self.max_lat - self.min_lat)
        lon = self.min_lon + (c / (self.cols - 1)) * (self.max_lon - self.min_lon)
        return float(lat), float(lon)

    def _generate_road_network(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]], nx.DiGraph]:
        """
        Creates realistic road network graph with:
        - Arterial elevated highway (Western Ridge Expressway)
        - Central Business District corridor traversing Milan Subway underpass
        - Cross avenues and perimeter ring roads
        """
        G = nx.DiGraph()

        # Define key intersections (nodes)
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

        # Enrich nodes with elevation
        for nid, data in nodes.items():
            r, c = self.lat_lon_to_cell(data["lat"], data["lon"])
            data["elevation_m"] = float(self.dem[r, c])
            data["grid_r"] = r
            data["grid_c"] = c
            G.add_node(nid, **data)

        # Helper to compute haversine distance in meters
        def calc_dist_m(lat1, lon1, lat2, lon2):
            R = 6371000.0
            phi1, phi2 = np.radians(lat1), np.radians(lat2)
            dphi = np.radians(lat2 - lat1)
            dlambda = np.radians(lon2 - lon1)
            a = np.sin(dphi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2)**2
            return float(2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a)))

        # Define road connections (bidirectional)
        raw_edges = [
            # Direct Milan Subway Corridor (Low-lying depression route - prone to flooding!)
            ("N_DOWNTOWN", "N_MILAN_SOUTH", "Downtown Arterial South", 45, False),
            ("N_MILAN_SOUTH", "N_MILAN_SUBWAY", "Milan Subway Approach South", 40, False),
            ("N_MILAN_SUBWAY", "N_MILAN_NORTH", "Milan Subway Underpass", 40, False),
            ("N_MILAN_NORTH", "N_AIRPORT", "Airport Central Boulevard", 55, False),

            # Elevated Expressway Bypass (High-ground safe route!)
            ("N_DOWNTOWN", "N_HIGHWAY_BYPASS_S", "Southern Link to Elevated Expressway", 50, False),
            ("N_HIGHWAY_BYPASS_S", "N_EAST_RIDGE", "Eastern Foothill Viaduct", 65, True),
            ("N_EAST_RIDGE", "N_MED_CENTER", "Emergency Hospital Flyover", 60, True),
            ("N_MED_CENTER", "N_HIGHWAY_BYPASS_N", "Elevated Expressway Central", 70, True),
            ("N_HIGHWAY_BYPASS_N", "N_TECH_PARK", "Tech Park Spur", 60, False),
            ("N_HIGHWAY_BYPASS_N", "N_AIRPORT", "Airport High-Level Connector", 65, True),

            # Coastal & West routes (King's circle route - also low elevation)
            ("N_DOWNTOWN", "N_KINGS_CIRCLE", "King's Avenue Link", 40, False),
            ("N_KINGS_CIRCLE", "N_MILAN_SOUTH", "King's Cross Connection", 40, False),
            ("N_KINGS_CIRCLE", "N_WEST_COAST", "Harbor Promenade", 50, False),
            ("N_WEST_COAST", "N_AIRPORT", "West Coastal Parkway", 60, False),
            ("N_SOUTH_GATE", "N_DOWNTOWN", "South Port Approach", 45, False),
            ("N_SOUTH_GATE", "N_KINGS_CIRCLE", "South King's Bypass", 40, False),

            # Northern & Eastern Cross routes
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
            length_m = calc_dist_m(node_u["lat"], node_u["lon"], node_v["lat"], node_v["lon"])
            speed_ms = (speed_kmh * 1000.0) / 3600.0
            base_time_sec = length_m / speed_ms

            # Discretize path between u and v to find traversed grid cells
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

            avg_elevation = float(np.mean(elevations))
            min_elevation = float(np.min(elevations))

            # Forward edge
            e_id_fwd = f"R_{edge_counter:03d}_F"
            edge_fwd_data = {
                "id": e_id_fwd,
                "from_node": u,
                "to_node": v,
                "name": name,
                "length_m": round(length_m, 1),
                "speed_kmh": speed_kmh,
                "base_time_sec": round(base_time_sec, 1),
                "is_elevated": is_elevated,
                "coordinates": coords,
                "cells": list(set(cells)),
                "avg_elevation_m": round(avg_elevation, 1),
                "min_elevation_m": round(min_elevation, 1),
            }
            edges_list.append(edge_fwd_data)
            G.add_edge(u, v, **edge_fwd_data)

            # Reverse edge
            e_id_rev = f"R_{edge_counter:03d}_R"
            coords_rev = list(reversed(coords))
            edge_rev_data = {
                "id": e_id_rev,
                "from_node": v,
                "to_node": u,
                "name": f"{name} (Reverse)",
                "length_m": round(length_m, 1),
                "speed_kmh": speed_kmh,
                "base_time_sec": round(base_time_sec, 1),
                "is_elevated": is_elevated,
                "coordinates": coords_rev,
                "cells": list(set(cells)),
                "avg_elevation_m": round(avg_elevation, 1),
                "min_elevation_m": round(min_elevation, 1),
            }
            edges_list.append(edge_rev_data)
            G.add_edge(v, u, **edge_rev_data)

            edge_counter += 1

        return nodes, edges_list, G

    def _generate_drainage_network(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]], nx.DiGraph]:
        """
        Creates directed drainage graph with:
        Street Inlets -> Manholes -> Collector Pipes -> Main Trunk Canal -> Bay Outfalls.
        """
        G = nx.DiGraph()

        # Drainage nodes located along key streets and low points
        drain_nodes_spec = [
            # High-elevation collector nodes (East)
            ("D_IN_EAST_01", "inlet", 19.085, 72.898, "East Tech Park Catch Basin", 8.0),
            ("D_IN_EAST_02", "inlet", 19.076, 72.888, "Medical Center Catch Basin", 10.0),
            ("D_MH_EAST_TRUNK", "manhole", 19.078, 72.885, "East Foothills Collector Manhole", 35.0),
            
            # Milan Subway System (Critical bottleneck!)
            ("D_IN_MILAN_N", "inlet", 19.077, 72.874, "Milan North Street Inlet", 12.0),
            ("D_IN_MILAN_DIP", "inlet", 19.073, 72.874, "Milan Subway Low Catch Basin", 15.0),
            ("D_MH_MILAN_SINK", "manhole", 19.073, 72.873, "Milan Subway Pumping Chamber", 45.0),
            ("D_IN_MILAN_S", "inlet", 19.068, 72.873, "Milan South Street Drain", 10.0),

            # King's Circle Drainage
            ("D_IN_KINGS_01", "inlet", 19.067, 72.864, "King's Circle Storm Inlet 1", 12.0),
            ("D_IN_KINGS_02", "inlet", 19.066, 72.865, "King's Circle Storm Inlet 2", 12.0),
            ("D_MH_KINGS", "manhole", 19.067, 72.862, "King's Circle Sump Chamber", 40.0),

            # Downtown Central Area
            ("D_IN_DT_01", "inlet", 19.062, 72.870, "Downtown Central Station Inlet", 14.0),
            ("D_MH_DT_CENTRAL", "manhole", 19.063, 72.868, "Downtown Main Interceptor Manhole", 50.0),

            # Airport & North Drainage
            ("D_IN_AIRPORT", "inlet", 19.088, 72.868, "Airport Runoff Drain Inlet", 20.0),
            ("D_MH_NORTH_TRUNK", "manhole", 19.084, 72.867, "North Trunk Interceptor", 50.0),

            # Main Culverts & Trunk Junctions
            ("D_TRUNK_CENTRAL", "junction", 19.070, 72.860, "Central Storm Trunk Culvert", 120.0),
            ("D_TRUNK_NORTH", "junction", 19.080, 72.858, "North Relief Storm Canal", 100.0),

            # Coastal Outfalls (Discharges directly into coastal waters)
            ("D_OUTFALL_BAY", "outfall", 19.065, 72.851, "Western Bay Tidal Outfall", 500.0),
            ("D_OUTFALL_CREEK", "outfall", 19.078, 72.852, "Creek Storm Gate Outfall", 500.0),
        ]

        drain_nodes = {}
        for nid, ntype, lat, lon, street_loc, cap_m3 in drain_nodes_spec:
            r, c = self.lat_lon_to_cell(lat, lon)
            elev = float(self.dem[r, c])
            node_data = {
                "id": nid,
                "name": nid,
                "type": ntype,
                "lat": lat,
                "lon": lon,
                "elevation_m": round(elev, 2),
                "storage_capacity_m3": cap_m3,
                "current_water_m3": 0.0,
                "street_location": street_loc,
                "grid_r": r,
                "grid_c": c,
            }
            drain_nodes[nid] = node_data
            G.add_node(nid, **node_data)

        # Drainage edges (Pipes and culverts)
        # (u, v, length_m, diameter_m, capacity_m3_s)
        pipe_specs = [
            # High-elevation branch -> East trunk
            ("D_IN_EAST_01", "D_MH_EAST_TRUNK", 250, 0.6, 1.2),
            ("D_IN_EAST_02", "D_MH_EAST_TRUNK", 220, 0.6, 1.2),
            ("D_MH_EAST_TRUNK", "D_TRUNK_CENTRAL", 600, 1.2, 4.5),

            # Milan subway drainage
            ("D_IN_MILAN_N", "D_MH_MILAN_SINK", 180, 0.7, 1.5),
            ("D_IN_MILAN_DIP", "D_MH_MILAN_SINK", 100, 0.8, 2.0),
            ("D_IN_MILAN_S", "D_MH_MILAN_SINK", 160, 0.7, 1.5),
            ("D_MH_MILAN_SINK", "D_TRUNK_CENTRAL", 450, 1.0, 3.2),  # Bottleneck pipe! In extreme rain >3.2 m3/s causes surcharge

            # King's circle drainage
            ("D_IN_KINGS_01", "D_MH_KINGS", 120, 0.7, 1.6),
            ("D_IN_KINGS_02", "D_MH_KINGS", 130, 0.7, 1.6),
            ("D_MH_KINGS", "D_TRUNK_CENTRAL", 350, 1.1, 3.8),

            # Downtown branch
            ("D_IN_DT_01", "D_MH_DT_CENTRAL", 140, 0.8, 1.8),
            ("D_MH_DT_CENTRAL", "D_TRUNK_CENTRAL", 320, 1.2, 4.0),

            # Airport & North branch
            ("D_IN_AIRPORT", "D_MH_NORTH_TRUNK", 250, 0.9, 2.5),
            ("D_MH_NORTH_TRUNK", "D_TRUNK_NORTH", 380, 1.4, 5.5),

            # Main Culverts to Outfall
            ("D_TRUNK_CENTRAL", "D_OUTFALL_BAY", 520, 2.0, 12.0),
            ("D_TRUNK_NORTH", "D_OUTFALL_CREEK", 480, 1.8, 10.0),
            ("D_TRUNK_NORTH", "D_TRUNK_CENTRAL", 400, 1.2, 4.0), # Interconnecting relief
        ]

        drain_edges = []
        for i, (u, v, length, diam, cap) in enumerate(pipe_specs, 1):
            nu = drain_nodes[u]
            nv = drain_nodes[v]
            slope = max(0.001, (nu["elevation_m"] - nv["elevation_m"]) / length)
            edge_data = {
                "id": f"PIPE_{i:02d}",
                "from_node": u,
                "to_node": v,
                "length_m": length,
                "diameter_m": diam,
                "slope": round(float(slope), 4),
                "capacity_m3_s": cap,
                "current_flow_m3_s": 0.0,
                "coordinates": [
                    [nu["lon"], nu["lat"]],
                    [nv["lon"], nv["lat"]]
                ]
            }
            drain_edges.append(edge_data)
            G.add_edge(u, v, **edge_data)

        return drain_nodes, drain_edges, G

# Singleton instance
_city_instance = None

def get_city_data() -> CityData:
    global _city_instance
    if _city_instance is None:
        _city_instance = CityData()
    return _city_instance
