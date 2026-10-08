import networkx as nx
import numpy as np
from typing import Dict, List, Tuple, Any
from ..models.schemas import DrainNodeStatus

class DrainageModel:
    """
    Subsurface drainage network hydraulic simulation using NetworkX directed graph.
    Models inlet capture, pipe capacity limits, node storage buffering,
    hydraulic surcharging, and surface overflow.
    """

    def __init__(self, drain_graph: nx.DiGraph, drain_nodes: Dict[str, Any], drain_edges: List[Dict[str, Any]]):
        self.G = drain_graph
        self.drain_nodes = drain_nodes
        self.drain_edges = drain_edges
        self.reset_state()

    def reset_state(self):
        """Resets water stored in manholes and pipes."""
        for nid, data in self.G.nodes(data=True):
            data["current_water_m3"] = 0.0
            data["overflow_m3"] = 0.0
            data["is_overflowing"] = False
            data["overflow_rate_m3_s"] = 0.0

        for u, v, data in self.G.edges(data=True):
            data["current_flow_m3_s"] = 0.0
            data["is_surcharged"] = False

    def simulate_timestep(
        self,
        surface_water_grid_m3: np.ndarray,
        timestep_seconds: float = 1800.0,
        intake_efficiency: float = 0.65
    ) -> Tuple[np.ndarray, List[DrainNodeStatus], Dict[str, float]]:
        """
        Simulates hydraulic intake and pipe transport for one timestep:
        1. Inlets capture surface water from their corresponding grid cells.
        2. Flow propagates through the directed graph towards outfall nodes.
        3. Edges limit flow to capacity (capacity_m3_s).
        4. Node storage buffers surcharge; overflow returns to surface cell.
        
        Returns:
            overflow_grid_m3: 2D array of overflow volume returned to surface
            overflow_nodes_list: List of DrainNodeStatus for currently overflowing nodes
            stats: summary metrics (captured_vol, overflow_vol, outfall_discharged_vol)
        """
        overflow_grid_m3 = np.zeros_like(surface_water_grid_m3, dtype=np.float32)
        rows, cols = surface_water_grid_m3.shape
        overflow_nodes = []

        total_intake_m3 = 0.0
        total_overflow_m3 = 0.0
        total_discharged_m3 = 0.0

        # Step 1: Inflow calculation into each node
        node_inflows_m3 = {nid: 0.0 for nid in self.G.nodes()}

        for nid, data in self.G.nodes(data=True):
            if data["type"] == "inlet":
                r, c = data["grid_r"], data["grid_c"]
                if 0 <= r < rows and 0 <= c < cols:
                    available_water = surface_water_grid_m3[r, c]
                    # Inlet max intake rate (e.g. 1.5 m3/s * timestep seconds)
                    max_inlet_cap = 1.5 * timestep_seconds * intake_efficiency
                    captured = min(available_water * 0.75, max_inlet_cap)
                    
                    surface_water_grid_m3[r, c] -= captured
                    node_inflows_m3[nid] += captured
                    total_intake_m3 += captured

        # Step 2: Route through graph in topological order
        # Outfalls have no successors; inlets have no predecessors
        # We can sort nodes topologically or process generation by generation
        try:
            eval_order = list(nx.topological_sort(self.G))
        except nx.NetworkXUnfeasible:
            # If there's a loop, fallback to elevation descending order
            eval_order = sorted(
                self.G.nodes(),
                key=lambda n: self.G.nodes[n]["elevation_m"],
                reverse=True
            )

        for nid in eval_order:
            node_data = self.G.nodes[nid]
            storage_cap = node_data["storage_capacity_m3"]
            is_outfall = (node_data["type"] == "outfall")

            # Total water arriving at this node
            incoming_m3 = node_inflows_m3[nid] + node_data["current_water_m3"]
            
            if is_outfall:
                # Discharges directly into coastal waters / tidal creek
                # Max outfall flow capacity
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
                # No downstream edge and not outfall - dead end or retention
                discharge_cap_m3 = 0.0
            else:
                total_pipe_cap_m3_s = sum(edata["capacity_m3_s"] for _, _, edata in out_edges)
                discharge_cap_m3 = total_pipe_cap_m3_s * timestep_seconds

            if incoming_m3 <= discharge_cap_m3:
                # All water can flow through outgoing pipes
                routed_m3 = incoming_m3
                node_data["current_water_m3"] = 0.0
                node_data["is_overflowing"] = False
                node_data["overflow_rate_m3_s"] = 0.0
            else:
                # Water exceeds pipe discharge capacity!
                routed_m3 = discharge_cap_m3
                surplus_m3 = incoming_m3 - discharge_cap_m3

                # Buffer inside node chamber
                if surplus_m3 <= storage_cap:
                    node_data["current_water_m3"] = surplus_m3
                    node_data["is_overflowing"] = False
                    node_data["overflow_rate_m3_s"] = 0.0
                else:
                    # Chamber fills up -> Surcharge / Overflows onto surface street!
                    node_data["current_water_m3"] = storage_cap
                    overflow_vol = surplus_m3 - storage_cap
                    node_data["is_overflowing"] = True
                    overflow_rate = overflow_vol / timestep_seconds
                    node_data["overflow_rate_m3_s"] = round(float(overflow_rate), 2)
                    node_data["overflow_m3"] = round(float(overflow_vol), 1)

                    # Return overflow water directly to the surface cell
                    r, c = node_data["grid_r"], node_data["grid_c"]
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
                            street_location=node_data["street_location"]
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
                    "street_location": data.get("street_location", nid)
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
                    "length_m": data["length_m"],
                    "diameter_m": data["diameter_m"],
                    "capacity_m3_s": data["capacity_m3_s"],
                    "current_flow_m3_s": data.get("current_flow_m3_s", 0.0),
                    "is_surcharged": data.get("is_surcharged", False),
                    "slope": data["slope"]
                }
            }
            features.append(feat)

        return {
            "type": "FeatureCollection",
            "features": features
        }
