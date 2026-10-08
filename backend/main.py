from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from .api.routes import router

app = FastAPI(
    title="Urban Flood Nowcasting & Flood-Safe Routing System",
    description=(
        "Working end-to-end hackathon MVP coupling DEM surface runoff, "
        "subsurface drainage graph capacity, real-time flood depth prediction, "
        "and dynamic flood-safe routing."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for local development and frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")

@app.get("/")
def root():
    return {
        "message": "Urban Flood Prediction & Flood-Safe Routing API is operational",
        "documentation": "/docs",
        "health": "/api/status",
        "simulate_endpoint": "/api/simulate",
        "route_endpoint": "/api/route",
        "flood_map_endpoint": "/api/flood-map",
        "drainage_endpoint": "/api/drainage"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
