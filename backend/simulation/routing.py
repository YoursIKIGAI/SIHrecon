import networkx as nx
import numpy as np
from typing import Dict, List, Tuple, Any, Optional

from ..data.city_generator import CityData, get_city_data
from ..models.schemas import (
    RouteRequest,
    RouteResponse,
    RouteOption,
    RouteSegmentDetail,
    FloodedRoadSegment,
)

class RoutingEngine:
    """
    Flood-Aware Dynamic Multi-City Routing Engine.
    Calculates:
      1. Fastest route (standard free-flow Dijkstra without flood penalties)
      2. Flood-safe route (heavily penalizes flooded corridors; excludes/penalizes impassable roads > 40cm)
      3. Alternative route (balanced safety/distance compromise)

    Features segment-level risk aggregation, out-of-bounds coordinate validation,
    and city independence.
    """

    def __init__(self, city_data: Optional[CityData] = None):
        self.city = city_data if city_data is not None else get_city_data()
        self.base_graph = self.city.road_graph

    def validate_coordinates(self, lat: float, lon: float, point_label: str = "Point") -> Tuple[bool, str]:
        """Validates that a coordinate falls within the active city's geographic extent."""
        in_bounds = self.city.is_point_in_bounds(lat, lon)
        if not in_bounds:
            b = self.city.bounds
            return False, (
                f"{point_label} ({lat:.4f}, {lon:.4f}) is outside {self.city.city_name} bounds "
                f"[Lat: {b['min_lat']:.4f} to {b['max_lat']:.4f}, Lon: {b['min_lon']:.4f} to {b['max_lon']:.4f}]."
            )
        return True, "OK"

    def _find_nearest_node(self, lon: float, lat: float) -> str:
        """Finds the closest road intersection node to a given coordinate."""
        best_nid = None
        min_dist_sq = float("inf")

        for nid, data in self.base_graph.nodes(data=True):
            nlat = data["lat"]
            nlon = data["lon"]
            dist_sq = (nlat - lat)**2 + (nlon - lon)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                best_nid = nid

        return best_nid if best_nid is not None else list(self.base_graph.nodes())[0]

    def calculate_routes(
        self,
        origin_lon: float,
        origin_lat: float,
        dest_lon: float,
        dest_lat: float,
        road_depths: List[FloodedRoadSegment],
        timestep_minutes: int = 60
    ) -> RouteResponse:
        """
        Calculates:
          - Fastest (Normal) Route
          - Flood-Safe Route
          - Alternative Route (balanced trade-off)
        """
        # Validate coordinates against city boundary
        valid_origin, origin_err = self.validate_coordinates(origin_lat, origin_lon, "Origin")
        if not valid_origin:
            raise ValueError(origin_err)

        valid_dest, dest_err = self.validate_coordinates(dest_lat, dest_lon, "Destination")
        if not valid_dest:
            raise ValueError(dest_err)

        # Map depth lookups by road ID
        depth_by_id = {r.road_id: r for r in road_depths}

        start_node = self._find_nearest_node(origin_lon, origin_lat)
        end_node = self._find_nearest_node(dest_lon, dest_lat)

        if start_node == end_node:
            # Pick a fallback adjacent node if start equals end
            neighbors = list(self.base_graph.neighbors(start_node))
            if neighbors:
                end_node = neighbors[0]

        # 1. Build graphs for routing
        G_normal = self.base_graph.copy()
        G_safe = self.base_graph.copy()
        G_alt = self.base_graph.copy()

        for u, v, data in G_normal.edges(data=True):
            base_time = data["base_time_sec"]
            data["weight"] = base_time

        for u, v, data in G_safe.edges(data=True):
            eid = data["id"]
            base_time = data["base_time_sec"]
            road_info = depth_by_id.get(eid)
            depth_cm = road_info.water_depth_cm if road_info else 0.0

            # Dynamic Flood Penalty Function for Safe Route
            if depth_cm <= 5.0:
                penalty_factor = 1.0  # safe
            elif depth_cm <= 10.0:
                penalty_factor = 1.3  # minor puddle
            elif depth_cm <= 20.0:
                penalty_factor = 4.0  # moderate waterlogging
            elif depth_cm <= 40.0:
                penalty_factor = 20.0 # severe waterlogging, strong detour
            else:
                # > 40 cm: Road impassable / blocked!
                penalty_factor = 10000.0

            data["weight"] = base_time * penalty_factor
            data["depth_cm"] = depth_cm

        for u, v, data in G_alt.edges(data=True):
            eid = data["id"]
            base_time = data["base_time_sec"]
            road_info = depth_by_id.get(eid)
            depth_cm = road_info.water_depth_cm if road_info else 0.0

            # Moderate penalty for Alternative Route (allows shallow water to avoid giant detours)
            if depth_cm <= 10.0:
                alt_penalty = 1.1
            elif depth_cm <= 25.0:
                alt_penalty = 2.2
            elif depth_cm <= 40.0:
                alt_penalty = 6.0
            else:
                alt_penalty = 5000.0

            data["weight"] = base_time * alt_penalty
            data["depth_cm"] = depth_cm

        # 2. Compute Normal Route (Shortest time, unaware of flood hazard)
        try:
            normal_path_nodes = nx.shortest_path(G_normal, source=start_node, target=end_node, weight="weight")
            normal_route_option = self._reconstruct_route(
                normal_path_nodes, G_normal, depth_by_id, route_type="normal"
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            normal_route_option = self._empty_route("normal")

        # 3. Compute Flood-Safe Route (Avoids high water and blocked roads)
        try:
            safe_path_nodes = nx.shortest_path(G_safe, source=start_node, target=end_node, weight="weight")
            safe_route_option = self._reconstruct_route(
                safe_path_nodes, G_safe, depth_by_id, route_type="flood_safe"
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            safe_route_option = normal_route_option

        # 4. Compute Alternative Route (Intermediate balance)
        try:
            alt_path_nodes = nx.shortest_path(G_alt, source=start_node, target=end_node, weight="weight")
            alt_route_option = self._reconstruct_route(
                alt_path_nodes, G_alt, depth_by_id, route_type="alternative"
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            alt_route_option = safe_route_option

        # Calculate avoided flooded roads and segment stats
        normal_flooded_ids = {s.road_id for s in normal_route_option.segments if s.water_depth_cm >= 10.0}
        safe_flooded_ids = {s.road_id for s in safe_route_option.segments if s.water_depth_cm >= 10.0}
        avoided_count = max(0, len(normal_flooded_ids) - len(safe_flooded_ids))

        time_diff = round(safe_route_option.estimated_time_minutes - normal_route_option.estimated_time_minutes, 1)
        dist_diff = round(safe_route_option.distance_km - normal_route_option.distance_km, 2)
        is_rerouted = (
            (normal_route_option.coordinates != safe_route_option.coordinates)
            if normal_route_option.segments and safe_route_option.segments else False
        )

        if is_rerouted and normal_route_option.max_water_depth_cm >= 20.0:
            summary = (
                f"Flood hazard detected on direct route ({normal_route_option.max_water_depth_cm:.1f} cm water). "
                f"Safe route re-directed via higher ground/drainage corridor, avoiding {avoided_count} flooded segments "
                f"(+{abs(time_diff):.1f} min travel time delta). Alternative balanced route also available."
            )
        elif not is_rerouted and normal_route_option.max_water_depth_cm < 10.0:
            summary = f"Direct route across {self.city.city_name} is flood-safe and optimal. No detour required."
        else:
            summary = (
                f"Route computed for {self.city.city_name}. "
                f"Direct risk: {normal_route_option.flood_risk}, Safe route risk: {safe_route_option.flood_risk}."
            )

        return RouteResponse(
            normal_route=normal_route_option,
            safe_route=safe_route_option,
            alternative_route=alt_route_option,
            distance_difference_km=dist_diff,
            time_difference_minutes=time_diff,
            avoided_flooded_roads=avoided_count,
            timestep_minutes=timestep_minutes,
            is_rerouted=is_rerouted,
            summary=summary
        )

    def _reconstruct_route(
        self,
        path_nodes: List[str],
        graph: nx.DiGraph,
        depth_by_id: Dict[str, FloodedRoadSegment],
        route_type: str
    ) -> RouteOption:
        """Assembles GeoJSON coordinates, segment-level risks, and route summary metrics."""
        all_coords = []
        segments = []
        total_dist_m = 0.0
        total_time_sec = 0.0
        max_depth = 0.0
        flooded_count = 0

        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i + 1]
            edge_data = graph.get_edge_data(u, v)
            if not edge_data:
                continue

            eid = edge_data["id"]
            road_name = edge_data["name"]
            length = edge_data["length_m"]
            base_time = edge_data["base_time_sec"]
            coords = edge_data["coordinates"]

            road_info = depth_by_id.get(eid)
            depth_cm = road_info.water_depth_cm if road_info else 0.0
            risk = road_info.risk_level if road_info else "Safe"
            is_blocked = depth_cm > 40.0

            if depth_cm > max_depth:
                max_depth = depth_cm
            if depth_cm >= 10.0:
                flooded_count += 1

            total_dist_m += length
            total_time_sec += base_time

            segments.append(
                RouteSegmentDetail(
                    road_id=eid,
                    name=road_name,
                    length_m=round(length, 1),
                    water_depth_cm=round(depth_cm, 1),
                    risk_level=risk,
                    coordinates=coords,
                    is_blocked=is_blocked,
                    elevation_m=round(edge_data.get("elevation_m", 15.0), 1)
                )
            )

            if not all_coords:
                all_coords.extend(coords)
            else:
                all_coords.extend(coords[1:])

        # Calculate exposed percentage
        total_segs = max(1, len(segments))
        exposed_pct = round((flooded_count / total_segs) * 100.0, 1)

        # Determine overall flood risk of route
        if max_depth < 5.0:
            overall_risk = "Low"
        elif max_depth < 15.0:
            overall_risk = "Minor"
        elif max_depth < 30.0:
            overall_risk = "Moderate"
        else:
            overall_risk = "Severe"

        return RouteOption(
            route_type=route_type,
            coordinates=all_coords,
            distance_km=round(total_dist_m / 1000.0, 2),
            estimated_time_minutes=round(total_time_sec / 60.0, 1),
            flood_risk=overall_risk,
            max_water_depth_cm=round(max_depth, 1),
            flooded_segments_count=flooded_count,
            segments=segments,
            exposed_percentage=exposed_pct
        )

    def _empty_route(self, route_type: str) -> RouteOption:
        return RouteOption(
            route_type=route_type,
            coordinates=[],
            distance_km=0.0,
            estimated_time_minutes=0.0,
            flood_risk="Unknown",
            max_water_depth_cm=0.0,
            flooded_segments_count=0,
            segments=[],
            exposed_percentage=0.0
        )
