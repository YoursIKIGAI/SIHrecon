# 🌊 Metro Flood Nowcast — Urban Flood Intelligence & Emergency Routing Command Center

> **Smart India Hackathon (SIH) Project** — An end-to-end AI-powered urban emergency management platform that predicts **where** flooding will occur, **how deep** the water will be, **which drains** will surcharge, and **how** emergency vehicles or commuters can safely navigate around submerged roads in real time.

---

## 📌 Table of Contents

1. [What Does This Application Do?](#-what-does-this-application-do)
2. [System Architecture](#-system-architecture)
3. [How the AI / ML Model Works](#-how-the-ai--ml-model-works)
4. [UI Icons & Controls Explained](#-ui-icons--controls-explained)
5. [Key Features](#-key-features)
6. [Project Structure](#-project-structure)
7. [Quick Start Guide](#-quick-start-guide)
8. [API Reference](#-api-reference)
9. [Possible Improvements](#-possible-improvements)
10. [Tech Stack](#-tech-stack)

---

## 🔍 What Does This Application Do?

**Metro Flood Nowcast** is an urban flood intelligence platform built for city emergency managers, first responders, and commuters. Given a short-term rainfall forecast (or a custom storm scenario), it:

1. **Predicts where water will accumulate** — using a 2,000-cell Digital Elevation Model (DEM) grid of the Mumbai Metro Basin.
2. **Calculates flood depths per road segment** — classifying risk as `Safe → Minor → Moderate → Severe → Critical`.
3. **Simulates underground drainage behavior** — identifying which manholes and pipes are surcharging and sending overflow back onto streets.
4. **Routes vehicles around flooded roads** — comparing a naive shortest-path route vs. a flood-safe alternative route that penalizes or avoids submerged roads.
5. **Gives a 0–3 hour animated timeline** — so you can scrub through the future and watch the flood evolve over time.

The platform supports two interchangeable simulation engines:
- **Coupled Hydrodynamic Physics Engine** — a step-by-step water balance simulation (slower, high-fidelity).
- **Trained AI/ML Surrogate Model** — a physics-informed regression model that produces results ~100× faster (<2 ms).

---

## 🏗️ System Architecture

```
Rainfall Forecast Input
(Light / Heavy / Extreme / Custom)
          │
          ▼
┌─────────────────────────┐
│   Runoff Generator      │  ← Rational Method + Infiltration (soil absorption)
│   (runoff.py)           │
└────────────┬────────────┘
             │
     ┌───────┴──────────┐
     ▼                  ▼
┌──────────────┐   ┌────────────────────┐
│ DEM Surface  │   │ Subsurface Drain   │
│ Flow Model   │◄──│ Network (NetworkX) │
│(surface_flow)│   │  (drainage.py)     │
└──────┬───────┘   └────────┬───────────┘
       │  overland runoff    │ surcharged backflow
       └─────────┬───────────┘
                 ▼
     ┌───────────────────────┐
     │  Coupled Hydrodynamic │  ← 0-3 hour time-series water balance
     │  Engine (flood_engine)│
     └────────────┬──────────┘
                  │
         ┌────────┴──────────┐
         ▼                   ▼
┌───────────────┐   ┌────────────────────────┐
│ AI/ML         │   │  Flood Inundation Map  │
│ Surrogate     │   │  (Risk: Safe→Critical) │
│ (model.py)    │   └──────────┬─────────────┘
└───────────────┘              │
                               ▼
                  ┌────────────────────────┐
                  │  Flood-Safe Dijkstra   │
                  │  Routing Engine        │
                  │  (routing.py)          │
                  └────────────┬───────────┘
                               ▼
                  ┌────────────────────────┐
                  │  React GIS Dashboard   │
                  │  (Leaflet Map, Panels) │
                  └────────────────────────┘
```

---

## 🤖 How the AI / ML Model Works

The AI model is a **Physics-Informed ML Surrogate Regressor** — it is trained to mimic the coupled hydrodynamic physics engine but runs approximately **100× faster**.

### Step 1 — Training Data Generation (`dataset.py`)

The `FloodDatasetGenerator` class runs the **full physics engine** across 12 different randomized storm intensities (20–190 mm/hr) at 4 timesteps each (30, 60, 90, 120 minutes). This generates a labeled dataset:

- **Input features (X)** — 8 physics-grounded spatial features per grid cell:

| Feature | Description |
|---|---|
| `rainfall_intensity_mm_hr` | Current storm rainfall rate |
| `cumulative_rainfall_mm` | Total rainfall since storm start |
| `dem_elevation_m` | Cell elevation from Digital Elevation Model |
| `slope` | Terrain steepness (D8 steepest descent) |
| `is_sink` | Is this cell a natural depression / basin? |
| `dist_to_drain_m` | Distance to nearest drainage inlet |
| `drain_capacity_m3_s` | Hydraulic capacity of nearest drain |
| `upstream_inflow_proxy` | Relative upstream accumulation (lower = collects more water) |

- **Target label (y)** — Water depth in cm for each cell, computed from the physics simulation.

### Step 2 — Model Training (`model.py`)

The `FloodSurrogateMLModel` uses **regularized gradient descent** with these key design choices:

```
Normalization → Feature Augmentation → Gradient Descent → ReLU Output
```

1. **Normalization**: Each feature is standardized to zero mean and unit variance.
2. **Feature Augmentation**: Two physics-inspired nonlinear interaction features are added:
   - `rain × (1 - elevation_norm)` — captures that low-lying areas flood more under the same rain.
   - `rain × is_sink` — captures catastrophic pooling in natural depressions.
3. **Gradient Descent with L2 Regularization**: 150 epochs (configurable), learning rate 0.04, L2 penalty 0.005.
4. **ReLU activation**: `max(0, prediction)` — ensures water depth cannot be negative.
5. **Metrics tracked**: R² score, RMSE (cm), MAE (cm), feature importances.

**Typical performance**: R² > 94%, RMSE ≈ 1.8 cm, inference time < 2 ms.

### Step 3 — Inference (`predict_grid`)

At prediction time, the model takes the current storm intensity and cumulative rain, stacks the pre-computed static terrain features, applies normalization + augmentation, and performs a single matrix multiply over all 2,000 grid cells simultaneously. **The whole grid is predicted in < 2 ms**.

### How the Two Engines Compare

| Property | Physics Engine | AI/ML Surrogate |
|---|---|---|
| Approach | Step-by-step water balance simulation | Trained regression approximation |
| Speed | ~250 ms | < 2 ms |
| Accuracy | Ground truth (reference) | R² > 94%, ~1.8 cm RMSE |
| Drainage detail | Full surcharge propagation | Heuristic overflow estimation |
| Use case | Detailed forensic analysis | Real-time dashboards, rapid alerts |

---

## 🖱️ UI Icons & Controls Explained

### 🔝 Top Command Bar (Header)

| Icon/Control | What It Does |
|---|---|
| ☁️ **CloudRain (pulsing, top-left)** | App logo — indicates the system is live and monitoring. The green blinking dot means the system is active/connected. |
| ⚡ **Zap icon + Rainfall buttons** | **Scenario selector** — choose from preset storm intensities: `LIGHT` (~10 mm/hr), `HEAVY` (~45 mm/hr), `EXTREME` (~120 mm/hr), `CUSTOM`. Clicking one immediately re-runs the simulation. |
| 📡 **Activity icon → "Hydro Physics"** | Switches the simulation engine to the **full coupled hydrodynamic physics** model. Button glows blue when active. |
| 🧠 **BrainCircuit icon → "AI / ML Surrogate"** | Switches to the **trained AI model** for ultra-fast inference. Button glows teal when active. |
| 📻 **Radio icon + dBZ value** | **Doppler Radar readout** — shows radar reflectivity in dBZ, calculated from rainfall rate using the Marshall-Palmer formula (Z = 200 × R^1.6). Red = severe storm (≥50 dBZ). |
| ▶ **"RUN PREDICTION"** | Triggers a fresh simulation with the currently selected scenario and engine mode. Shows a spinner while running. Displays execution time in ms on completion. |
| ✅ **Green ms badge** | Shows how long the last simulation took in milliseconds. |
| 🖥️ **Cpu icon → "Train Model"** | Opens the **AI/ML Surrogate Studio** modal where you can configure training epochs and launch model training live. |
| 📊 **BarChart3 → "Validation"** | Opens a **scientific accuracy report** comparing the physics and ML engines — shows Precision, Recall, F1, RMSE. |
| 🔊 / 🔇 **Volume2 / VolumeX** | **Emergency audio alert toggle** — when enabled, a synthetic siren beep plays whenever a `Critical` flood zone is detected. Red glow = alarms active. |

---

### 🗺️ Map View

| Control | What It Does |
|---|---|
| **Multi-basemap selector** (top-right of map) | Switch between: `Dark` (CartoDB Dark Matter), `Satellite` (Esri World Imagery), `Topo` (OpenTopoMap with elevation contours), `OSM` (standard OpenStreetMap). |
| **Flood depth polygons** | Colored grid cells overlaid on the map — color = flood risk level (see Legend). Only cells with >3 cm of water are shown. |
| **Road segments** | Colored road lines — color matches their current flood depth status. |
| **Cyan drainage network** | Subsurface pipe network. Pulsing red circles = overflowing/surcharged manholes. |
| **Green solid line (route)** | Flood-safe route — dynamically rerouted to avoid submerged roads. |
| **Red dashed line (route)** | Standard shortest-time route — may pass through flooded areas. |
| **Map click** | Click to set origin (first click) then destination (second click) for routing. |
| **Location search bar** | Type a landmark to fly the map to that location. |

---

### 📋 Left Side Panel

#### Conditions Tab (Activity icon)

Shows real-time flood stats for the **currently selected timestep**:
- Rainfall rate (mm/hr) with a sparkline trend across 0–3 hours.
- Number of flooded roads and critical zones.
- Max and mean water depths.
- List of most severely flooded road segments with risk badges.

#### Drainage Tab (GitFork icon)

Lists **all surcharged/overflowing manhole nodes** at the current timestep:
- Node name, type (catch basin / manhole / trunk collector), and location.
- Current overflow rate (m³/s) and storage fill level.

---

### ⏱️ Bottom Center — Time Slider

| Control | What It Does |
|---|---|
| **Horizontal slider** | Scrub through the 0–180 minute (0–3 hour) forecast. Map and all panels update live. |
| **Prev/Next buttons** | Jump between simulation timesteps (0, 30, 60, 90, 120, 180 min). |
| **Play / Pause button** | Automatically plays through the timeline, animating the flood spread over 3 hours. |
| **Timestep markers** | Ticks below the slider show rainfall intensity at each timestep. |

---

### 🧭 Right Side Panel — Routing Engine

| Control | What It Does |
|---|---|
| **Origin / Destination inputs** | Manually type or click on the map to set start and end points for navigation. |
| **Vehicle mode selector** | `Car`, `Emergency`, `Pedestrian` — affects speed assumptions for route time estimates. |
| **Demo Quick Presets** | One-click routing examples (e.g., "Downtown → Airport") to demonstrate flood avoidance. |
| **Route comparison card** | Shows: distance (km), estimated time (min), max water depth, flooded segment count — normal vs. safe side by side. |
| **Recalculate Route button** | Re-runs Dijkstra with the latest flood depths at the current timestep. |

---

### 📍 Bottom Left — Legend & Layer Toggles

| Control | What It Does |
|---|---|
| **Flood depth color scale** | `Safe` (transparent) → `Minor` (yellow) → `Moderate` (orange) → `Severe` (red) → `Critical` (deep red). |
| **Layer toggle checkboxes** | Toggle visibility of: Flood polygons, Drainage network, Road segments, Routes. |
| **Doppler Rain Echo toggle** | Shows/hides the animated radar reflectivity overlay on the map. |

---

### 🧪 AI/ML Surrogate Studio Modal

| Control | What It Does |
|---|---|
| **Epochs slider** | Number of gradient descent training iterations (10–500). |
| **Storm scenarios slider** | Number of storm hydrographs used to generate training data (4–12). |
| **TRAIN SURROGATE MODEL NOW** | Sends a `POST /api/train` request and shows live R², RMSE, and feature importance rankings. |
| **Feature importance bar chart** | Shows which of the 8 input features most influenced the model's flood depth predictions. |

---

## 🚀 Key Features

1. **Dual Engine Simulation** — Toggle seamlessly between physics simulation (accurate) and AI surrogate (instant).
2. **Drainage Network Graph** — Real subsurface hydraulic routing with surcharge propagation using NetworkX directed graphs.
3. **Flood-Safe Dynamic Routing** — Depth-penalized Dijkstra routing that re-routes as flood conditions evolve over time.
4. **Trainable AI in the Browser** — Train the ML model live from the dashboard; watch R² converge in real time.
5. **0–3 Hour Animated Timeline** — Scrub or play through the simulation to see how flooding develops.
6. **Multi-Basemap GIS** — Switch between Dark Matter, Satellite, Topo, and OSM tile layers.
7. **Audio Emergency Alerts** — Synthetic siren beep via Web Audio API when Critical zones are detected.
8. **Doppler Radar readout** — Rainfall converted to radar reflectivity (dBZ) using the Marshall-Palmer relation.
9. **Scientific Validation Report** — Precision, Recall, F1 Score, and RMSE against a synthetic ground truth.

---

## 📦 Project Structure

```
SIHrecon-main/
│
├── backend/
│   ├── main.py                     # FastAPI application entry point & CORS
│   ├── api/
│   │   └── routes.py               # REST endpoints (/simulate, /train, /route, /search-locations)
│   ├── models/
│   │   └── schemas.py              # Pydantic request/response schemas
│   ├── ml/
│   │   ├── dataset.py              # Hydrodynamic feature extraction & training data generator
│   │   ├── model.py                # Physics-informed surrogate ML regressor
│   │   ├── train_model.py          # Standalone CLI training script
│   │   └── flood_surrogate_model.json  # Serialized model weights & metrics
│   ├── simulation/
│   │   ├── rainfall.py             # Rainfall time-series & scenario generator
│   │   ├── runoff.py               # Infiltration & Rational Method runoff
│   │   ├── surface_flow.py         # DEM hydrodynamic D8 routing & depression detection
│   │   ├── drainage.py             # NetworkX directed drainage graph & surcharge
│   │   ├── flood_engine.py         # Coupled 0-3h time-series simulation engine
│   │   └── routing.py              # Flood-aware Dijkstra router with depth penalties
│   ├── data/
│   │   ├── city_generator.py       # Seeded synthetic Mumbai city terrain, roads & pipes
│   │   └── validation.py           # Precision, Recall, F1 & RMSE evaluator
│   └── tests/
│       └── test_simulation.py      # Unit tests & ML surrogate validation
│
├── frontend/
│   └── src/
│       ├── App.tsx                 # Master UI state controller
│       ├── api/client.ts           # REST API client
│       ├── components/
│       │   ├── Header.tsx          # Command bar with engine toggle & radar readout
│       │   ├── TimeSlider.tsx      # 0-3h forecast slider with play/pause
│       │   ├── CurrentConditions.tsx   # Live conditions & sparkline trend
│       │   ├── RoutingPanel.tsx    # Dual-route comparison & quick presets
│       │   ├── DrainagePanel.tsx   # Drainage surcharge node inspector
│       │   ├── ModelTrainingModal.tsx  # AI/ML Surrogate training studio
│       │   ├── ValidationModal.tsx # Scientific validation report
│       │   └── Legend.tsx          # Flood depth color scale & layer toggles
│       ├── map/MapView.tsx         # Leaflet map with multi-basemap & location search
│       └── types/index.ts          # TypeScript type definitions
│
├── data/                           # Seed datasets (DEM, roads, rainfall, drainage GeoJSON)
├── docker-compose.yml              # One-command Docker orchestration
├── requirements.txt                # Python dependencies
└── README.md
```

---

## 🛠️ Quick Start Guide

### Prerequisites

- **Python 3.9+**
- **Node.js 18+**
- **Docker** (optional, for containerized deployment)

---

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd SIHrecon-main

# Start everything in one command
docker-compose up --build
```

- **Frontend Dashboard**: http://localhost:3000
- **FastAPI Swagger Docs**: http://localhost:8000/docs

---

### Option 2: Manual Local Setup

#### Backend (Python FastAPI)

```bash
cd backend
python -m venv venv

# Activate virtual environment
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Start the backend server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### Train the ML Model (Optional — auto-trains on first run)

```bash
python -m backend.ml.train_model
```

#### Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

---

### Option 3: Windows One-Click Launchers

- Double-click `start_all.bat` to start both backend and frontend simultaneously.
- Or run `start_backend.bat` and `start_frontend.bat` separately.

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/simulate` | Run flood simulation (`engine_mode: "physics" or "ml_surrogate"`) |
| `POST` | `/api/train` | Train the ML surrogate model with custom epochs & storm scenarios |
| `GET` | `/api/ml-status` | Get trained model accuracy metrics, training history, and permutation importances |
| `POST` | `/api/route` | Compute normal vs. flood-safe Dijkstra routes |
| `GET` | `/api/flood-map?timestep=60` | Get GeoJSON flood polygon layer for a specific timestep |
| `GET` | `/api/drainage` | Get directed drainage network as GeoJSON |
| `GET` | `/api/search-locations?q=query` | Nominatim OpenStreetMap geocoding with 300ms debounce and POI fallback |
| `POST` | `/api/validate?mode=...` | Assess accuracy across benchmark_physics, historical_event, or self_noise |
| `GET` | `/api/scenarios` | List all available rainfall scenarios with descriptions |
| `GET` | `/api/radar-feed` | Ingest OpenWeatherMap live forecast or bundled Mumbai 2005 IMD cloudburst |
| `GET` | `/api/cities` | List supported city metro profiles (Mumbai, Delhi, Chennai) |
| `POST` | `/api/switch-city` | Switch active simulation city terrain and drainage model |
| `POST` | `/api/trigger-auto-update` | Toggle background auto-simulation broadcast loop |
| `GET` | `/api/export/geotiff` | Download flood depth grid as GIS GeoTIFF raster (.tif) |
| `GET` | `/api/export/geojson` | Download full vector polygons and flooded roads (.geojson) |
| `WS` | `/ws/live-feed` | WebSocket real-time simulation updates and live stream |

---

## 🚀 Enhancements Implemented (SIH Problem Statement Full-Stack Upgrade)

All 10 critical gaps identified in the problem statement have been resolved:

1. **🔴 Fix 1 — Real SRTM DEM Terrain Ingestion (`backend/data/city_generator.py`)**:
   - GeoTIFF raster ingestion via `rasterio` resampled to grid resolution.
   - Script `backend/data/download_dem.py` for automated SRTM 30m DEM retrieval.
   - Graceful fallback to synthetic micro-topography when offline.

2. **🔴 Fix 2 — Real Rainfall & Doppler Radar Ingestion (`backend/simulation/radar_fetcher.py`)**:
   - Live OpenWeatherMap API 2.5 / 3.0 integration for real-time nowcasts.
   - Bundled IMD historical cloudburst dataset (Mumbai 26 July 2005, 944 mm).
   - Real-time dropdown selector with API key modal in the frontend header.

3. **🔴 Fix 3 — Real Ground-Truth Validation Modes (`backend/data/validation.py`)**:
   - Replaced circular self-noise benchmarking with **3 distinct validation modes**:
     - `benchmark_physics`: Independent physics run with dry soil infiltration parameters.
     - `historical_event`: 20 field observation points from `mumbai_flood_observed.csv`.
     - `self_noise`: Clearly flagged as demonstration only with warning banners.
   - Interactive validation mode selector in the frontend modal.

4. **🔴 Fix 4 — Real OpenStreetMap Road Graph via OSMnx (`backend/data/city_generator.py`)**:
   - Integration with OSMnx for real drivable road networks with elevation lookup.
   - GeoPackage caching (`mumbai_osm_roads.gpkg`) to prevent redundant downloads.

5. **🟡 Fix 5 — Nominatim OpenStreetMap Geocoder (`backend/api/routes.py`)**:
   - Free Nominatim search API with city bounding box constraints.
   - 300ms debounce in `MapView.tsx` to prevent request flooding.
   - In-memory 300s TTL cache and graceful fallback to local POIs.

6. **🟡 Fix 6 — WebSocket Real-Time Live Updates (`backend/main.py`)**:
   - Native `/ws/live-feed` WebSocket endpoint with active client connection manager.
   - Background asyncio loop that pushes updates to connected clients.
   - Pulsing green "LIVE" badge and auto-update toggle in the header.

7. **🟡 Fix 7 — Spatially Non-Uniform Storm Cells & Trajectory (`backend/simulation/rainfall.py`)**:
   - Convective storm core modeling with spatial Gaussian attenuation and movement vector.
   - Time-series storm track output (`storm_track`) with lat/lon coordinates.
   - Animated dashed cyan polyline visualization in `MapView.tsx`.

8. **🟢 Fix 8 — Multi-City Support (`backend/data/city_configs.py`)**:
   - Built-in multi-city registry: **Mumbai MMR**, **Delhi NCR (Yamuna)**, and **Chennai Basin (Adyar)**.
   - Dynamic `/api/switch-city` endpoint reinitializing terrain, bounds, and drainage.
   - Interactive city selector dropdown in the frontend header.

9. **🟢 Fix 9 — GIS Export to GeoTIFF & GeoJSON (`backend/api/routes.py`)**:
   - Direct binary raster export to EPSG:4326 GeoTIFF via `rasterio`.
   - Downloadable vector GeoJSON feature collection.
   - One-click export menu located directly in the map legend panel.

10. **🟢 Fix 10 — Pure NumPy 2-Hidden-Layer MLP Neural Network (`backend/ml/model.py`)**:
    - Replaced linear regressor with an MLP neural network (8 → 32 → 16 → 1 ReLU).
    - Features Xavier initialization, mini-batch SGD, dropout (p=0.1), and early stopping.
    - Zero external ML dependencies (runs in pure NumPy).
    - Permutation feature importance analysis.
    - Pure SVG loss convergence curve (Train vs. Val loss) in the AI Studio modal.

---

## 💡 Possible Improvements

### 🔬 ML / AI Model

| Improvement | Details |
|---|---|
| **Replace linear regressor with a neural network** | Even a small MLP (2-3 hidden layers) would capture nonlinear interactions better and improve RMSE from ~1.8 cm to <0.5 cm |
| **Add temporal modeling (LSTM / GRU)** | The current model treats each timestep independently. A recurrent model would exploit the time evolution of flood depth for more accurate nowcasts |
| **Ensemble model** | Average predictions from multiple trained models with different random seeds to reduce variance |
| **Real DEM data integration** | Replace the synthetic city generator with real SRTM or LiDAR elevation data for an actual city |
| **Transfer learning from real flood events** | Fine-tune on historical flood records (e.g., Mumbai 2005, 2017 floods) to improve real-world accuracy |
| **Uncertainty quantification** | Add prediction intervals so operators know confidence levels (e.g., "35 ± 8 cm") |

### 🌐 Simulation

| Improvement | Details |
|---|---|
| **2D shallow water equations (SWE)** | Replace the D8 descent approximation with a full Saint-Venant SWE solver for more accurate overland flow |
| **Real-time radar data ingestion** | Connect to IMD (India Meteorological Department) API or NOAA radar feeds for live nowcasting |
| **Higher grid resolution** | Scale from 2,000 to 20,000+ grid cells for neighborhood-level precision |
| **Soil moisture state** | Track antecedent soil saturation between storms (currently reset each run) |
| **Building footprint obstruction** | Import OSM building polygons to properly block overland flow paths |

### 🗺️ Frontend / UX

| Improvement | Details |
|---|---|
| **Real geocoder API** | Replace the dummy location search with Mapbox Geocoding API or Nominatim for real address search |
| **Push notifications** | WebSocket-based real-time alerts pushed to field responders on mobile devices |
| **3D map visualization** | Use Deck.gl or Mapbox GL for 3D extruded flood depth visualization |
| **Multi-city support** | Add city profiles (Delhi, Chennai, Bangalore) with their own DEMs and drain networks |
| **Offline PWA mode** | Service worker caching so field responders can use the app without internet in disaster zones |
| **Export to PDF / GeoTIFF** | Let emergency managers export flood maps and route reports as printable PDFs |

### ⚙️ Backend / Infrastructure

| Improvement | Details |
|---|---|
| **WebSocket streaming** | Stream simulation progress updates in real time instead of waiting for the full response |
| **Redis caching** | Cache simulation results by scenario hash to avoid redundant computation |
| **PostgreSQL + PostGIS** | Persist simulation history and road/drain network in a spatial database |
| **Celery task queue** | Run heavy physics simulations as async background workers |
| **Kubernetes deployment** | Scale horizontally to handle multiple simultaneous simulation requests |
| **Authentication / role-based access** | Separate views for field responders, planners, and public |

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** — High-performance async REST API framework
- **NumPy** — Vectorized hydrodynamic simulation (D8 flow, depth grids)
- **NetworkX** — Directed graph for subsurface drainage routing and road network Dijkstra
- **Pydantic** — Strict request/response validation schemas
- **Uvicorn** — ASGI server for FastAPI

### Frontend
- **React 18 + TypeScript** — Component-driven UI
- **Vite** — Fast dev server and build tool
- **Leaflet.js** — GIS map rendering with multi-basemap tile layers
- **Tailwind CSS** — Utility-first styling
- **Lucide React** — Icon library (CloudRain, BrainCircuit, Radio, etc.)
- **Web Audio API** — Synthetic emergency siren alerts

### Deployment
- **Docker + Docker Compose** — Containerized multi-service orchestration
- **Nginx** — Frontend static file serving in production

---

## 🏆 Performance Benchmarks

| Task | Time |
|---|---|
| Full physics simulation (0-3 hrs, 2000 cells) | < 260 ms |
| AI/ML surrogate inference (2000 cells) | < 2 ms |
| ML model training (150 epochs, 8 storm scenarios) | < 1.5 seconds |
| Flood-safe Dijkstra routing | < 5 ms |

---

## 👥 Team

Built for **Smart India Hackathon (SIH)** — Urban Flood Nowcasting & Emergency Response Track.

---

## 📄 License

This project is open-source under the MIT License.
