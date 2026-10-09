"""
City Configuration & Multi-City Registry for Metro Flood Nowcast.
Supports:
  - Mumbai Metropolitan Region (Maharashtra)
  - Delhi National Capital Territory (Yamuna Floodplain)
  - Chennai Metro Basin (Adyar River & Coastal Plain)

Maintains city bounding boxes, elevation specifications, documented historical
events, route presets, and fallback points of interest.
"""
import os
from typing import Dict, Any, List, Optional

BASE_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

CITY_REGISTRY: Dict[str, Dict[str, Any]] = {
    "mumbai": {
        "key": "mumbai",
        "name": "Mumbai Metropolitan Region",
        "state": "Maharashtra",
        "min_lat": 19.055,
        "max_lat": 19.095,
        "min_lon": 72.850,
        "max_lon": 72.905,
        "rows": 40,
        "cols": 50,
        "dem_file": os.path.join(BASE_DATA_DIR, "dem", "mumbai_srtm.tif"),
        "description": "Financial capital — prone to June–Sept monsoon cloudbursts, tidal locking, and Mithi River backflow (Ref: 26 July 2005 event, 944 mm/24h).",
        "center_lat": 19.075,
        "center_lon": 72.877,
        "timezone": "Asia/Kolkata",
        "elev_min": 1.5,
        "elev_max": 55.0,
        "elev_mean": 14.8,
        "elev_description": "Coastal alluvial plain with western Arabian Sea shoreline and eastern elevated ridges (Trombay/Kurla).",
        "historical_events": [
            {
                "id": "mumbai_2005_cloudburst",
                "title": "Mumbai 26 July 2005 Catastrophic Cloudburst",
                "event_date": "2005-07-26",
                "duration_hours": 24,
                "total_rainfall_mm": 944.0,
                "peak_intensity_mm_hr": 210.0,
                "description": "Historic 944 mm deluge in 24 hours (Santacruz Observatory), worst in recorded history. Mithi river breach submerged Milan Subway, King's Circle, and Kurla.",
                "sources": [
                    "India Meteorological Department (IMD) Santacruz & Colaba Observatories",
                    "Municipal Corporation of Greater Mumbai (MCGM) Disaster Management Cell",
                    "Fact Finding Committee on Mumbai Floods (Chitale Committee Report 2006)"
                ],
                "affected_localities": [
                    "Milan Subway Underpass",
                    "King's Circle / Gandhi Market",
                    "Kurla Creek / LBS Marg",
                    "Hindmata Junction",
                    "Kalina Air India Colony",
                    "Mahim Causeway Link"
                ],
                "observation_points_count": 13,
                "json_file": os.path.join(BASE_DATA_DIR, "rainfall", "mumbai_2005_event.json"),
            }
        ],
        "route_presets": [
            {
                "id": "mum_p1",
                "name": "Downtown Station → Metro Airport (Milan Chokepoint)",
                "origin": [72.870, 19.062],
                "destination": [72.868, 19.088],
                "desc": "Direct route crosses deep Milan Subway underpass; safe route uses elevated flyover corridor.",
            },
            {
                "id": "mum_p2",
                "name": "Harbor Gate → Emergency Trauma Hospital",
                "origin": [72.854, 19.065],
                "destination": [72.888, 19.076],
                "desc": "Coastal dock to critical medical care center via King's Circle basin.",
            },
            {
                "id": "mum_p3",
                "name": "South Port Entrance → East Tech City Ridge",
                "origin": [72.862, 19.058],
                "destination": [72.898, 19.085],
                "desc": "Full urban diagonal corridor connecting maritime hub to technology ridge.",
            },
        ],
        "fallback_pois": [
            {"id": "MUM_POI_1", "name": "Downtown Central Station", "lat": 19.062, "lon": 72.870, "category": "transit"},
            {"id": "MUM_POI_2", "name": "Milan Subway Underpass", "lat": 19.073, "lon": 72.874, "category": "chokepoint"},
            {"id": "MUM_POI_3", "name": "Metro Airport Terminal 2", "lat": 19.088, "lon": 72.868, "category": "airport"},
            {"id": "MUM_POI_4", "name": "King's Circle Junction", "lat": 19.067, "lon": 72.864, "category": "basin"},
            {"id": "MUM_POI_5", "name": "Central Trauma Hospital", "lat": 19.076, "lon": 72.888, "category": "hospital"},
            {"id": "MUM_POI_6", "name": "East Tech City Cyberpark", "lat": 19.085, "lon": 72.898, "category": "commercial"},
            {"id": "MUM_POI_7", "name": "West Coast Harbor Gate", "lat": 19.065, "lon": 72.854, "category": "maritime"},
            {"id": "MUM_POI_8", "name": "Elevated Expressway Interchange", "lat": 19.086, "lon": 72.890, "category": "highway"},
            {"id": "MUM_POI_9", "name": "Kurla Creek Bridge Link", "lat": 19.082, "lon": 72.883, "category": "bridge"},
            {"id": "MUM_POI_10", "name": "South Port Entrance Gate", "lat": 19.058, "lon": 72.862, "category": "port"},
        ]
    },
    "delhi": {
        "key": "delhi",
        "name": "Delhi NCR — Yamuna Floodplain",
        "state": "National Capital Territory of Delhi",
        "min_lat": 28.580,
        "max_lat": 28.720,
        "min_lon": 77.100,
        "max_lon": 77.280,
        "rows": 40,
        "cols": 50,
        "dem_file": os.path.join(BASE_DATA_DIR, "dem", "delhi_srtm.tif"),
        "description": "Yamuna river basin — prone to monsoon flash waterlogging and upper-catchment river overflow (Ref: July 2023 flood, 208.66 m peak gauge).",
        "center_lat": 28.650,
        "center_lon": 77.190,
        "timezone": "Asia/Kolkata",
        "elev_min": 198.0,
        "elev_max": 226.0,
        "elev_mean": 211.5,
        "elev_description": "Gentle east-sloping terrain terminating at the Yamuna river floodway (~198-202 m MSL), flanked by Delhi Ridge (~225 m MSL) in the west.",
        "historical_events": [
            {
                "id": "delhi_2023_yamuna",
                "title": "Delhi July 2023 Yamuna Extreme Inundation",
                "event_date": "2023-07-09",
                "duration_hours": 24,
                "total_rainfall_mm": 153.0,
                "peak_intensity_mm_hr": 135.0,
                "description": "Record single-day July rain (153 mm) and 3.59 lakh cusecs Hathnikund discharge breached 45-year Yamuna record at 208.66 m. Flooded ITO, Ring Road, Pragati Maidan tunnel, and Kashmere Gate.",
                "sources": [
                    "India Meteorological Department (IMD) Safdarjung & Lodhi Road Stations",
                    "Central Water Commission (CWC) Old Railway Bridge Gauge Station",
                    "Delhi Disaster Management Authority (DDMA) Flood Control Division"
                ],
                "affected_localities": [
                    "ITO Ring Road Underpass",
                    "Kashmere Gate ISBT Low Basin",
                    "Pragati Maidan Tunnel Incline",
                    "Monastery Market Ring Road",
                    "Yamuna Bazar Nigambodh Ghat",
                    "Civil Lines Bela Road",
                    "Red Fort Outer Ring Road"
                ],
                "observation_points_count": 14,
                "json_file": os.path.join(BASE_DATA_DIR, "rainfall", "delhi_2023_event.json"),
            }
        ],
        "route_presets": [
            {
                "id": "del_p1",
                "name": "Connaught Place → Kashmere Gate ISBT",
                "origin": [77.218, 28.631],
                "destination": [77.228, 28.668],
                "desc": "Direct route along Ring Road is submerged by Yamuna backflow; safe route detours via elevated Delhi Ridge / Rani Jhansi corridor.",
            },
            {
                "id": "del_p2",
                "name": "New Delhi Railway Station → ITO Emergency HQ",
                "origin": [77.221, 28.642],
                "destination": [77.242, 28.629],
                "desc": "Key transit to municipal disaster management center, evaluating drainage barrier at Vikas Marg.",
            },
            {
                "id": "del_p3",
                "name": "Civil Lines Administrative Hub → Pragati Maidan Trade Center",
                "origin": [77.222, 28.682],
                "destination": [77.245, 28.618],
                "desc": "North-South transit skirting the flooded riverbank with alternative ridge bypass.",
            },
        ],
        "fallback_pois": [
            {"id": "DEL_POI_1", "name": "Connaught Place Central Hub", "lat": 28.631, "lon": 77.218, "category": "commercial"},
            {"id": "DEL_POI_2", "name": "Kashmere Gate ISBT", "lat": 28.667, "lon": 77.228, "category": "transit"},
            {"id": "DEL_POI_3", "name": "ITO Junction & Vikas Marg", "lat": 28.629, "lon": 77.242, "category": "chokepoint"},
            {"id": "DEL_POI_4", "name": "Pragati Maidan Tunnel Complex", "lat": 28.618, "lon": 77.245, "category": "underpass"},
            {"id": "DEL_POI_5", "name": "New Delhi Railway Station", "lat": 28.642, "lon": 77.221, "category": "railway"},
            {"id": "DEL_POI_6", "name": "Red Fort Outer Ring Road", "lat": 28.654, "lon": 77.236, "category": "arterial"},
            {"id": "DEL_POI_7", "name": "Yamuna Bazar Ghat", "lat": 28.658, "lon": 77.238, "category": "riverbank"},
            {"id": "DEL_POI_8", "name": "Civil Lines Bela Road", "lat": 28.682, "lon": 77.222, "category": "government"},
            {"id": "DEL_POI_9", "name": "Rajghat Outer Perimeter", "lat": 28.643, "lon": 77.249, "category": "monument"},
            {"id": "DEL_POI_10", "name": "Delhi Ridge Botanical Point", "lat": 28.650, "lon": 77.195, "category": "ridge"},
        ]
    },
    "chennai": {
        "key": "chennai",
        "name": "Chennai Metro Basin — Adyar River",
        "state": "Tamil Nadu",
        "min_lat": 12.970,
        "max_lat": 13.100,
        "min_lon": 80.160,
        "max_lon": 80.290,
        "rows": 40,
        "cols": 50,
        "dem_file": os.path.join(BASE_DATA_DIR, "dem", "chennai_srtm.tif"),
        "description": "Flat coastal delta — vulnerable to severe northeast monsoon depressions, Adyar river overtopping, and Buckingham canal silting (Ref: Dec 2015 deluge, 494 mm/24h).",
        "center_lat": 13.060,
        "center_lon": 80.270,
        "timezone": "Asia/Kolkata",
        "elev_min": 2.0,
        "elev_max": 24.0,
        "elev_mean": 9.2,
        "elev_description": "Low-gradient coastal plain with Bay of Bengal coastline (~2 m MSL), Velachery depression bowl (~3 m MSL), and isolated elevations around Guindy / St. Thomas Mount.",
        "historical_events": [
            {
                "id": "chennai_2015_deluge",
                "title": "Chennai 1 December 2015 Historic Deluge",
                "event_date": "2015-12-01",
                "duration_hours": 24,
                "total_rainfall_mm": 494.0,
                "peak_intensity_mm_hr": 195.0,
                "description": "Extreme 494 mm single-day rainfall combined with sudden 29,000 cusecs surplus release from Chembarambakkam Reservoir into Adyar river. Immersed Saidapet Bridge, Velachery, Airport runway, and Kotturpuram under 1.5–3 m water.",
                "sources": [
                    "India Meteorological Department (IMD) Meenambakkam & Nungambakkam Observatories",
                    "Public Works Department (PWD) Water Resources Organization Chembarambakkam Station",
                    "Tamil Nadu State Disaster Management Authority (TNSDMA) 2015 Deluge Report"
                ],
                "affected_localities": [
                    "Saidapet Bridge South Approach",
                    "Velachery 100ft Bypass Low Basin",
                    "Chennai Airport Runway / GST Road",
                    "Kotturpuram Adyar Riverbank",
                    "Jafferkhanpet Kasi Point",
                    "Tambaram Mudichur Low Basin",
                    "T Nagar Usman Road Subway"
                ],
                "observation_points_count": 13,
                "json_file": os.path.join(BASE_DATA_DIR, "rainfall", "chennai_2015_event.json"),
            }
        ],
        "route_presets": [
            {
                "id": "che_p1",
                "name": "Chennai Central Station → Chennai International Airport",
                "origin": [80.276, 13.083],
                "destination": [80.174, 12.988],
                "desc": "Primary lifeline route along Mount Road & GST Road severed by Adyar river inundation at Saidapet; safe route navigates elevated bypass.",
            },
            {
                "id": "che_p2",
                "name": "Guindy Industrial Hub → Velachery Residential Basin",
                "origin": [80.210, 13.010],
                "destination": [80.222, 12.980],
                "desc": "Transit into the lowest natural depression in southern Chennai, testing retention basin thresholds.",
            },
            {
                "id": "che_p3",
                "name": "T Nagar Commercial Center → Saidapet Hospital Point",
                "origin": [80.233, 13.038],
                "destination": [80.225, 13.018],
                "desc": "Medical emergency route assessing Usman Road subway and Saidapet bridge water depths.",
            },
        ],
        "fallback_pois": [
            {"id": "CHE_POI_1", "name": "Chennai Central Station", "lat": 13.083, "lon": 80.276, "category": "transit"},
            {"id": "CHE_POI_2", "name": "Saidapet Bridge Link", "lat": 13.018, "lon": 80.225, "category": "bridge"},
            {"id": "CHE_POI_3", "name": "Velachery 100ft Bypass", "lat": 12.980, "lon": 80.222, "category": "basin"},
            {"id": "CHE_POI_4", "name": "Chennai Airport GST Road", "lat": 12.988, "lon": 80.174, "category": "airport"},
            {"id": "CHE_POI_5", "name": "Guindy Industrial Hub", "lat": 13.010, "lon": 80.210, "category": "industrial"},
            {"id": "CHE_POI_6", "name": "T Nagar Commercial Centre", "lat": 13.038, "lon": 80.233, "category": "commercial"},
            {"id": "CHE_POI_7", "name": "Marina Beach Coastal Gate", "lat": 13.050, "lon": 80.280, "category": "coastal"},
            {"id": "CHE_POI_8", "name": "Kotturpuram Riverbank Point", "lat": 13.024, "lon": 80.245, "category": "riverbank"},
            {"id": "CHE_POI_9", "name": "St. Thomas Mount Ridge", "lat": 13.005, "lon": 80.198, "category": "ridge"},
            {"id": "CHE_POI_10", "name": "Anna Nagar 2nd Avenue Hub", "lat": 13.085, "lon": 80.210, "category": "residential"},
        ]
    },
}

_active_city_key = "mumbai"


def get_active_city_key() -> str:
    """Returns the current active city key ('mumbai', 'delhi', or 'chennai')."""
    return _active_city_key


def set_active_city_key(key: str) -> bool:
    """Sets active city key if registered. Returns True on success."""
    global _active_city_key
    normalized = str(key).lower().strip()
    if normalized in CITY_REGISTRY:
        _active_city_key = normalized
        return True
    return False


def get_city_config(key: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves full config dictionary for specified or active city."""
    k = (key or _active_city_key).lower().strip()
    return CITY_REGISTRY.get(k, CITY_REGISTRY["mumbai"])


def get_city_presets(key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns route presets for specified or active city."""
    cfg = get_city_config(key)
    return cfg.get("route_presets", [])


def get_city_pois(key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns fallback POIs for specified or active city."""
    cfg = get_city_config(key)
    return cfg.get("fallback_pois", [])


def get_historical_events(city_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns historical event descriptions for city or all cities."""
    if city_key:
        cfg = get_city_config(city_key)
        return cfg.get("historical_events", [])
    events = []
    for cfg in CITY_REGISTRY.values():
        events.extend(cfg.get("historical_events", []))
    return events
