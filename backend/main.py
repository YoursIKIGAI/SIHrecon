"""
Fix 6 — WebSocket live feed + auto-update loop.
Fix 8 — Multi-city switch endpoint.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os
import asyncio
import json
from typing import Set

from .api.routes import router

# Load env config
OPENWEATHERMAP_API_KEY = os.environ.get("OPENWEATHERMAP_API_KEY", "")

app = FastAPI(
    title="Urban Flood Nowcasting & Flood-Safe Routing System",
    description=(
        "End-to-end hackathon MVP coupling DEM surface runoff, "
        "subsurface drainage graph capacity, real-time flood depth prediction, "
        "and dynamic flood-safe routing. Supports WebSocket live updates."
    ),
    version="2.0.0-sih-enhanced",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

# ---------------------------------------------------------------
# Fix 6: WebSocket live connection manager
# ---------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)

    async def broadcast(self, message: str):
        dead = set()
        for ws in self.active:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        self.active -= dead


manager = ConnectionManager()

# Auto-update state
_auto_update_enabled = False
_auto_update_interval = 60  # seconds
_auto_update_scenario = "extreme"


@app.websocket("/ws/live-feed")
async def websocket_live_feed(ws: WebSocket):
    """
    Fix 6: WebSocket endpoint for real-time flood update streaming.
    Sends current simulation state immediately on connect, then
    streams updates as they are triggered by the auto-update loop.
    """
    await manager.connect(ws)
    try:
        # Send current state immediately
        from .simulation.flood_engine import get_flood_engine
        engine = get_flood_engine()
        if engine.last_result:
            payload = {
                "type": "simulation_update",
                "data": engine.last_result.model_dump() if hasattr(engine.last_result, "model_dump") else {},
                "auto_update": _auto_update_enabled,
            }
            await ws.send_text(json.dumps(payload))

        # Keep connection alive — handle ping/pong
        while True:
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                if msg == "ping":
                    await ws.send_text("pong")
            except asyncio.TimeoutError:
                await ws.send_text(json.dumps({"type": "heartbeat"}))
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(ws)


async def _auto_update_loop():
    """Background task that runs simulations and broadcasts to all WS clients."""
    global _auto_update_enabled, _auto_update_interval, _auto_update_scenario
    while True:
        if _auto_update_enabled and manager.active:
            try:
                from .simulation.flood_engine import get_flood_engine
                engine = get_flood_engine()
                result = engine.run_simulation(
                    scenario=_auto_update_scenario,
                    engine_mode="physics",
                    duration_minutes=180
                )
                payload = json.dumps({
                    "type": "simulation_update",
                    "data": result.model_dump() if hasattr(result, "model_dump") else {},
                    "auto_update": True,
                })
                await manager.broadcast(payload)
            except Exception as e:
                print(f"[AutoUpdate] Error: {e}")
        await asyncio.sleep(_auto_update_interval)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(_auto_update_loop())


@app.get("/")
def root():
    return {
        "message": "Urban Flood Prediction & Flood-Safe Routing API v2.0 — SIH Enhanced",
        "documentation": "/docs",
        "health": "/api/status",
        "websocket": "ws://localhost:8000/ws/live-feed",
        "simulate_endpoint": "/api/simulate",
        "route_endpoint": "/api/route",
        "flood_map_endpoint": "/api/flood-map",
        "drainage_endpoint": "/api/drainage",
        "radar_feed_endpoint": "/api/radar-feed",
        "cities_endpoint": "/api/cities",
        "export_geotiff": "/api/export/geotiff",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
