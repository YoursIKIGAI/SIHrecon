import networkx as nx
import numpy as np
from typing import Dict, List, Tuple, Any, Optional

from ..models.schemas import DrainNodeStatus

class DrainageModel:
    """
    Subsurface Hydraulic Pipe Network and Manhole Surcharge Model.
    Tracks water intake at curb inlets, downstream pipe flow routing,
    chamber storage capacity, hydraulic bottlenecks, and surface surcharge overflow eruptions.
    """

    def __init__(
        self,
        drain_graph: nx.DiGraph,
        drain_nodes: Dict[str, Dict[str, Any]],
        drain_edges: List[Dict[str, Any]]
    ):
        self.G = drain_graph
        self.nodes = drain_nodes
        self.edges = drain_edges
        self.reset_state()

    def reset_state(self):
        """Reset current water levels in all nodes and pipes to zero dry state."""
        for nid, data in self.G.nodes(data=True):
            data["current_water_m3"] = 0.0
            data["is_overflowing"] = False
            data["overflow_rate_m3_s"] = 0.0

        for u, v, data in self.G.edges(data=True):
            data["current_flow_m3_s"] = 0.0
            data["is_surcharged"] = False

    def simulate_timestep(
        self,
        surface_water_grid_m3: np.ndarray,
        timestep_seconds: float,
        intake_efficiency: float = 0.85
    ) -> Tuple[np.ndarray, List[DrainNodeStatus], Dict[str, float]]:
        """
        Simulate drainage intake, internal pipe routing, and manhole surcharge.
        """
        overflow_grid_m3 = np.zeros_like(surface_water_grid_m3)
        rows, cols = surface_water_grid_m3.shape
        overflow_nodes = []

        total_intake_m3 = 0.0
        total_overflow_m3 = 0.0
        total_discharged_m3 = 0.0

        # Step 1: Inflow calculation into each node from surface runoff catchment
        node_inflows_m3 = {nid: 0.0 for nid in self.G.nodes()}

        for nid, data in self.G.nodes(data=True):
            r, c = data["grid_r"], data["grid_c"]
            if 0 <= r < rows and 0 <= c < cols:
                # Catchment neighborhood window around the drainage node
                r_min, r_max = max(0, r - 1), min(rows, r + 2)
                c_min, c_max = max(0, c - 1), min(cols, c + 2)
                neighborhood_water = float(np.sum(surface_water_grid_m3[r_min:r_max, c_min:c_max]))

                if data["type"] == "inlet":
                    # Inlets capture surface water up to design intake capacity
                    max_inlet_cap = 2.5 * timestep_seconds * intake_efficiency
                    captured = min(neighborhood_water * 0.65, max_inlet_cap)
                    if neighborhood_water > 0.0:
                        surface_water_grid_m3[r_min:r_max, c_min:c_max] *= max(0.0, 1.0 - (captured / neighborhood_water))
                    node_inflows_m3[nid] += captured
                    total_intake_m3 += captured

                elif data["type"] in ["manhole", "junction"]:
                    # Direct depression inflow into low-lying manholes when ponding exceeds 15 cm
                    cell_water = float(surface_water_grid_m3[r, c])
                    if cell_water > 100.0:
                        direct_catch = min(cell_water * 0.30, 1.8 * timestep_seconds)
                        surface_water_grid_m3[r, c] -= direct_catch
                        node_inflows_m3[nid] += direct_catch
                        total_intake_m3 += direct_catch

        # Step 2: Route through graph in topological order
        try:
            eval_order = list(nx.topological_sort(self.G))
        except nx.NetworkXUnfeasible:
            eval_order = sorted(
                self.G.nodes(),
                key=lambda n: self.G.nodes[n]["elevation_m"],
                reverse=True
            )

        for nid in eval_order:
            node_data = self.G.nodes[nid]
            storage_cap = float(node_data["storage_capacity_m3"])
            is_outfall = (node_data["type"] == "outfall")
            is_bottleneck = bool(node_data.get("is_bottleneck", False))

            incoming_m3 = node_inflows_m3[nid] + float(node_data.get("current_water_m3", 0.0))

            if is_outfall:
                outfall_cap_m3 = 18.0 * timestep_seconds
                discharged = min(incoming_m3, outfall_cap_m3)
                node_data["current_water_m3"] = 0.0
                total_discharged_m3 += discharged
                node_data["is_overflowing"] = False
                node_data["overflow_rate_m3_s"] = 0.0
                continue

            # Check outgoing edges from this node
            out_edges = list(self.G.out_edges(nid, data=True))
            if not out_edges:
                discharge_cap_m3 = 0.0
            else:
                total_pipe_cap_m3_s = sum(edata["capacity_m3_s"] for _, _, edata in out_edges)
                # Bottlenecks suffer hydraulic constriction
                if is_bottleneck:
                    total_pipe_cap_m3_s *= 0.50
                discharge_cap_m3 = total_pipe_cap_m3_s * timestep_seconds

            r, c = node_data["grid_r"], node_data["grid_c"]
            local_surface_ponding_m3 = float(surface_water_grid_m3[r, c]) if (0 <= r < rows and 0 <= c < cols) else 0.0

            if incoming_m3 <= discharge_cap_m3 and local_surface_ponding_m3 < 500.0:
                routed_m3 = incoming_m3
                node_data["current_water_m3"] = 0.0
                node_data["is_overflowing"] = False
                node_data["overflow_rate_m3_s"] = 0.0
            else:
                routed_m3 = min(incoming_m3, discharge_cap_m3)
                surplus_m3 = max(0.0, incoming_m3 - discharge_cap_m3)

                if surplus_m3 <= storage_cap and local_surface_ponding_m3 < 500.0:
                    node_data["current_water_m3"] = surplus_m3
                    node_data["is_overflowing"] = False
                    node_data["overflow_rate_m3_s"] = 0.0
                else:
                    node_data["current_water_m3"] = storage_cap
                    overflow_vol = max(surplus_m3 - storage_cap, surplus_m3 * 0.8)
                    if overflow_vol <= 0.0 and (is_bottleneck or local_surface_ponding_m3 >= 500.0):
                        overflow_vol = 150.0

                    node_data["is_overflowing"] = True
                    overflow_rate = max(0.1, overflow_vol / timestep_seconds)
                    node_data["overflow_rate_m3_s"] = round(float(overflow_rate), 2)
                    node_data["overflow_m3"] = round(float(overflow_vol), 1)

                    if 0 <= r < rows and 0 <= c < cols:
                        overflow_grid_m3[r, c] += overflow_vol
                        surface_water_grid_m3[r, c] += overflow_vol
                    total_overflow_m3 += overflow_vol

                    overflow_nodes.append(
                        DrainNodeStatus(
                            node_id=nid,
                            name=node_data["name"],
                            type=node_data["type"],
                            lat=node_data["lat"],
                            lon=node_data["lon"],
                            elevation_m=node_data["elevation_m"],
                            storage_capacity_m3=storage_cap,
                            current_water_m3=round(float(storage_cap), 1),
                            is_overflowing=True,
                            overflow_rate_m3_s=round(float(overflow_rate), 2),
                            street_location=node_data["street_location"],
                            verification_status=node_data.get("verification_status", "verified"),
                            is_bottleneck=is_bottleneck
                        )
                    )

            # Distribute routed water to downstream pipes and nodes
            if out_edges and routed_m3 > 0.0:
                total_cap = sum(edata["capacity_m3_s"] for _, _, edata in out_edges)
                for _, v, edata in out_edges:
                    fraction = edata["capacity_m3_s"] / total_cap if total_cap > 0 else (1.0 / len(out_edges))
                    edge_routed_m3 = routed_m3 * fraction
                    edata["current_flow_m3_s"] = round(float(edge_routed_m3 / timestep_seconds), 2)
                    edata["is_surcharged"] = (edata["current_flow_m3_s"] >= edata["capacity_m3_s"] * 0.95)
                    node_inflows_m3[v] += edge_routed_m3

        stats = {
            "total_intake_m3": round(total_intake_m3, 1),
            "total_overflow_m3": round(total_overflow_m3, 1),
            "total_discharged_m3": round(total_discharged_m3, 1),
            "overflowing_nodes_count": len(overflow_nodes)
        }

        return overflow_grid_m3, overflow_nodes, stats

    def to_geojson(self) -> Dict[str, Any]:
        """Convert drainage nodes and edges into GeoJSON FeatureCollection."""
        features = []

        # Nodes
        for nid, data in self.G.nodes(data=True):
            feat = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [data["lon"], data["lat"]]
                },
                "properties": {
                    "id": nid,
                    "element": "node",
                    "type": data["type"],
                    "elevation_m": data["elevation_m"],
                    "storage_capacity_m3": data["storage_capacity_m3"],
                    "current_water_m3": data.get("current_water_m3", 0.0),
                    "is_overflowing": data.get("is_overflowing", False),
                    "overflow_rate_m3_s": data.get("overflow_rate_m3_s", 0.0),
                    "street_location": data["street_location"],
                    "verification_status": data.get("verification_status", "verified"),
                    "is_bottleneck": data.get("is_bottleneck", False)
                }
            }
            features.append(feat)

        # Edges
        for u, v, data in self.G.edges(data=True):
            feat = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": data["coordinates"]
                },
                "properties": {
                    "id": data["id"],
                    "element": "edge",
                    "from_node": u,
                    "to_node": v,
                    "diameter_m": data["diameter_m"],
                    "length_m": data["length_m"],
                    "capacity_m3_s": data["capacity_m3_s"],
                    "current_flow_m3_s": data.get("current_flow_m3_s", 0.0),
                    "is_surcharged": data.get("is_surcharged", False),
                    "verification_status": data.get("verification_status", "inferred")
                }
            }
            features.append(feat)

        return {
            "type": "FeatureCollection",
            "features": features
        }
