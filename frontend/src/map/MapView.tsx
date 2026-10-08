import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { RouteResponse, FloodedRoadSegment, DrainNodeStatus, BasemapType, LocationSearchResult } from '../types';
import { apiClient } from '../api/client';
import { Search, Map, Globe, Mountain, Navigation, Compass, Layers, X } from 'lucide-react';

interface MapViewProps {
  floodGeoJson: any;
  drainageGeoJson: any;
  floodedRoads: FloodedRoadSegment[];
  overflowNodes: DrainNodeStatus[];
  routeResult: RouteResponse | null;
  origin: [number, number];
  destination: [number, number];
  onMapClick: (coords: [number, number]) => void;
  showFloodLayer: boolean;
  showDrainageLayer: boolean;
  showRoadsLayer: boolean;
  showRoutesLayer: boolean;
  currentMinute: number;
  basemap: BasemapType;
  onBasemapChange: (bm: BasemapType) => void;
  showRadarOverlay: boolean;
  radarReflectivityDbz?: number;
  stormTrack?: { minute: number; center_lat: number; center_lon: number; intensity_mm_hr: number }[];
  cityCenter?: [number, number];
}

export const MapView: React.FC<MapViewProps> = ({
  floodGeoJson,
  drainageGeoJson,
  floodedRoads,
  overflowNodes,
  routeResult,
  origin,
  destination,
  onMapClick,
  showFloodLayer,
  showDrainageLayer,
  showRoadsLayer,
  showRoutesLayer,
  currentMinute,
  basemap,
  onBasemapChange,
  showRadarOverlay,
  radarReflectivityDbz = 52.0,
  stormTrack = [],
  cityCenter,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  // Layer groups
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const floodLayerRef = useRef<L.LayerGroup | null>(null);
  const drainageLayerRef = useRef<L.LayerGroup | null>(null);
  const roadsLayerRef = useRef<L.LayerGroup | null>(null);
  const routesLayerRef = useRef<L.LayerGroup | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const stormTrackLayerRef = useRef<L.LayerGroup | null>(null);

  // Search state
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<LocationSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [showSearchResults, setShowSearchResults] = useState<boolean>(false);
  const [showBasemapMenu, setShowBasemapMenu] = useState<boolean>(false);

  // Reliable Basemap Tile Providers (Zero watermark on Dark Canvas!)
  const BASEMAP_TILES: Record<BasemapType, { url: string; attribution: string; maxZoom: number }> = {
    dark: {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
      attribution: '&copy; Esri &copy; OpenStreetMap contributors',
      maxZoom: 16,
    },
    satellite: {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      attribution: '&copy; Esri World Imagery &copy; Maxar',
      maxZoom: 19,
    },
    streets: {
      url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19,
    },
    topo: {
      url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
      attribution: '&copy; OpenTopoMap contributors',
      maxZoom: 17,
    },
  };

  const getFloodColor = (depthCm: number): string => {
    if (depthCm < 5.0) return '#10b981';
    if (depthCm < 15.0) return '#84cc16';
    if (depthCm < 30.0) return '#f59e0b';
    if (depthCm < 50.0) return '#ef4444';
    return '#d946ef';
  };

  const getFloodOpacity = (depthCm: number): number => {
    if (depthCm < 5.0) return 0.30;
    if (depthCm < 15.0) return 0.50;
    if (depthCm < 30.0) return 0.70;
    if (depthCm < 50.0) return 0.85;
    return 0.95;
  };

  // 1. Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const initialCenter: [number, number] = cityCenter ? [cityCenter[1], cityCenter[0]] : [19.075, 72.875];
    const map = L.map(mapContainerRef.current, {
      center: initialCenter,
      zoom: 13,
      zoomControl: false,
    });

    // Initial Tile Layer
    const currentTileConfig = BASEMAP_TILES[basemap] || BASEMAP_TILES.dark;
    tileLayerRef.current = L.tileLayer(currentTileConfig.url, {
      attribution: currentTileConfig.attribution,
      maxZoom: currentTileConfig.maxZoom,
    }).addTo(map);

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    floodLayerRef.current = L.layerGroup().addTo(map);
    roadsLayerRef.current = L.layerGroup().addTo(map);
    drainageLayerRef.current = L.layerGroup().addTo(map);
    stormTrackLayerRef.current = L.layerGroup().addTo(map);
    routesLayerRef.current = L.layerGroup().addTo(map);
    markersLayerRef.current = L.layerGroup().addTo(map);

    map.on('click', (e: L.LeafletMouseEvent) => {
      onMapClick([Number(e.latlng.lng.toFixed(4)), Number(e.latlng.lat.toFixed(4))]);
    });

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update map view when active city changes
  useEffect(() => {
    if (!mapInstanceRef.current || !cityCenter) return;
    mapInstanceRef.current.flyTo([cityCenter[1], cityCenter[0]], 13, { duration: 1.5 });
  }, [cityCenter]);

  // 2. Basemap Switcher API Update
  useEffect(() => {
    if (!mapInstanceRef.current || !tileLayerRef.current) return;
    mapInstanceRef.current.removeLayer(tileLayerRef.current);

    const cfg = BASEMAP_TILES[basemap] || BASEMAP_TILES.dark;
    tileLayerRef.current = L.tileLayer(cfg.url, {
      attribution: cfg.attribution,
      maxZoom: cfg.maxZoom,
    }).addTo(mapInstanceRef.current);
    tileLayerRef.current.bringToBack();
  }, [basemap]);

  // 3. Search Handler with 300ms Debounce API Integration (Fix 5)
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const results = await apiClient.searchLocations(searchQuery);
        setSearchResults(results);
        setShowSearchResults(true);
      } catch (err) {
        console.error('Search error:', err);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleSelectSearchResult = (loc: LocationSearchResult) => {
    if (!mapInstanceRef.current) return;
    mapInstanceRef.current.flyTo([loc.lat, loc.lon], 15, { duration: 1.2 });
    setShowSearchResults(false);
    setSearchQuery(loc.name);
  };

  // 4. Render Flood Polygons
  useEffect(() => {
    if (!floodLayerRef.current) return;
    floodLayerRef.current.clearLayers();

    if (!showFloodLayer || !floodGeoJson || !floodGeoJson.features) return;

    const floodGeoLayer = L.geoJSON(floodGeoJson, {
      filter: (feature) => feature.properties.type === 'grid_cell',
      style: (feature) => {
        const depth = feature?.properties.water_depth_cm || 0;
        return {
          fillColor: getFloodColor(depth),
          fillOpacity: getFloodOpacity(depth),
          color: getFloodColor(depth),
          weight: 0.6,
          opacity: 0.5,
        };
      },
      onEachFeature: (feature, layer) => {
        const p = feature.properties;
        layer.bindPopup(`
          <div style="font-family: inherit; font-size: 12px; line-height: 1.5;">
            <div style="font-weight: 800; color: #38bdf8; margin-bottom: 4px; display: flex; align-items: center; justify-content: space-between;">
              <span>DEM CELL [${p.row}, ${p.col}]</span>
              <span style="font-size: 10px; background: #0c4a6e; padding: 2px 6px; border-radius: 4px;">NOWCAST</span>
            </div>
            <div>Water Depth: <strong style="color: ${getFloodColor(p.water_depth_cm)}; font-size: 14px;">${p.water_depth_cm} cm</strong></div>
            <div>Risk Category: <strong>${p.risk_level}</strong></div>
            <div>Elevation: <strong>${p.elevation_m} m AMSL</strong></div>
          </div>
        `);
      },
    });

    floodLayerRef.current.addLayer(floodGeoLayer);
  }, [floodGeoJson, showFloodLayer]);

  // 5. Render Storm Cell Movement Track (Fix 7)
  useEffect(() => {
    if (!stormTrackLayerRef.current) return;
    stormTrackLayerRef.current.clearLayers();

    if (!stormTrack || stormTrack.length < 2) return;

    const latLngs: [number, number][] = stormTrack.map((pt) => [pt.center_lat, pt.center_lon]);

    const trackLine = L.polyline(latLngs, {
      color: '#06b6d4',
      weight: 3,
      opacity: 0.85,
      dashArray: '6, 8',
      lineCap: 'round',
    });
    trackLine.bindPopup('<strong>Convective Storm Cell Trajectory</strong><br/>Predicted trajectory across 0–3h nowcast window.');
    stormTrackLayerRef.current.addLayer(trackLine);

    stormTrack.forEach((pt) => {
      const isCurrent = Math.abs(pt.minute - currentMinute) <= 15;
      const markerHtml = `
        <div style="
          width: ${isCurrent ? '26px' : '16px'};
          height: ${isCurrent ? '26px' : '16px'};
          border-radius: 50%;
          background: ${isCurrent ? 'rgba(6, 182, 212, 0.4)' : 'rgba(14, 165, 233, 0.25)'};
          border: 2px solid #06b6d4;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 0 12px ${isCurrent ? '#06b6d4' : 'transparent'};
          transform: translate(-50%, -50%);
        ">
          <div style="width: 6px; height: 6px; border-radius: 50%; background: #ffffff;"></div>
        </div>
      `;

      const stormIcon = L.divIcon({
        html: markerHtml,
        className: 'storm-track-icon',
        iconSize: [0, 0],
      });

      const m = L.marker([pt.center_lat, pt.center_lon], { icon: stormIcon });
      m.bindPopup(`
        <div style="font-size: 11px; font-family: inherit;">
          <strong style="color: #06b6d4;">Storm Core at T+${pt.minute}m</strong><br/>
          Intensity: <strong>${pt.intensity_mm_hr} mm/hr</strong><br/>
          Location: ${pt.center_lat.toFixed(3)}°N, ${pt.center_lon.toFixed(3)}°E
        </div>
      `);
      stormTrackLayerRef.current?.addLayer(m);
    });
  }, [stormTrack, currentMinute]);

  // 6. Render Drainage Network & Overflows
  useEffect(() => {
    if (!drainageLayerRef.current) return;
    drainageLayerRef.current.clearLayers();

    if (!showDrainageLayer || !drainageGeoJson) return;

    const drainGeo = L.geoJSON(drainageGeoJson, {
      filter: (f) => f.geometry.type === 'LineString',
      style: {
        color: '#38bdf8',
        weight: 2.2,
        opacity: 0.8,
        dashArray: '3, 4',
      },
    });
    drainageLayerRef.current.addLayer(drainGeo);

    // Overflowing Manholes
    overflowNodes.forEach((node) => {
      const pulseIcon = L.divIcon({
        html: `
          <div class="relative flex items-center justify-center">
            <div style="width: 24px; height: 24px; border-radius: 50%; background: #ef4444; opacity: 0.4; animation: ping 1s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>
            <div style="position: absolute; width: 14px; height: 14px; border-radius: 50%; background: #dc2626; border: 2px solid #ffffff; box-shadow: 0 0 10px #ef4444;"></div>
          </div>
        `,
        className: 'overflow-node-marker',
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });

      const m = L.marker([node.lat, node.lon], { icon: pulseIcon });
      m.bindPopup(`
        <div style="font-size: 12px; font-family: inherit;">
          <strong style="color: #ef4444;">OVERFLOWING INLET / MANHOLE</strong><br/>
          <strong>${node.name}</strong> (${node.type})<br/>
          Location: ${node.street_location}<br/>
          Overflow Rate: <strong style="color: #f87171;">${node.overflow_rate_m3_s} m³/s</strong><br/>
          Storage Capacity: ${node.storage_capacity_m3} m³ (SURCHARGED)
        </div>
      `);
      drainageLayerRef.current?.addLayer(m);
    });
  }, [drainageGeoJson, overflowNodes, showDrainageLayer]);

  // 7. Render Road Network
  useEffect(() => {
    if (!roadsLayerRef.current) return;
    roadsLayerRef.current.clearLayers();

    if (!showRoadsLayer || !floodedRoads) return;

    floodedRoads.forEach((r) => {
      if (r.coordinates && r.coordinates.length >= 2) {
        const latLngs = r.coordinates.map((c) => [c[1], c[0]] as [number, number]);
        const color = getFloodColor(r.water_depth_cm);

        const line = L.polyline(latLngs, {
          color: r.is_blocked ? '#ef4444' : color,
          weight: r.water_depth_cm > 15.0 ? 5 : 3,
          opacity: 0.9,
          dashArray: r.is_blocked ? '6, 6' : undefined,
        });

        line.bindPopup(`
          <div style="font-size: 12px; font-family: inherit;">
            <strong>${r.name}</strong><br/>
            Water Depth: <strong style="color: ${color}">${r.water_depth_cm} cm</strong><br/>
            Risk Status: <strong>${r.risk_level}</strong><br/>
            ${r.is_blocked ? '<span style="color: #ef4444; font-weight: bold;">⛔ ROADWAY IMPASSABLE (&gt;40cm)</span>' : '<span style="color: #10b981;">PASSABLE</span>'}
          </div>
        `);

        roadsLayerRef.current?.addLayer(line);
      }
    });
  }, [floodedRoads, showRoadsLayer]);

  // 8. Render Routing Comparison
  useEffect(() => {
    if (!routesLayerRef.current) return;
    routesLayerRef.current.clearLayers();

    if (!showRoutesLayer || !routeResult) return;

    if (routeResult.normal_route && routeResult.normal_route.coordinates.length > 0) {
      const normCoords = routeResult.normal_route.coordinates.map((c) => [c[1], c[0]] as [number, number]);
      const normLine = L.polyline(normCoords, {
        color: routeResult.normal_route.flooded_segments_count > 0 ? '#ef4444' : '#64748b',
        weight: 3.5,
        opacity: 0.75,
        dashArray: '5, 8',
      });
      normLine.bindPopup(`
        <div style="font-size: 12px;">
          <strong>Direct / Normal Route</strong><br/>
          Flooded Segments: <strong>${routeResult.normal_route.flooded_segments_count}</strong><br/>
          Max Water Depth: <strong>${routeResult.normal_route.max_water_depth_cm} cm</strong><br/>
          Distance: ${routeResult.normal_route.distance_km} km
        </div>
      `);
      routesLayerRef.current.addLayer(normLine);
    }

    if (routeResult.safe_route && routeResult.safe_route.coordinates.length > 0) {
      const safeCoords = routeResult.safe_route.coordinates.map((c) => [c[1], c[0]] as [number, number]);
      const safeLine = L.polyline(safeCoords, {
        color: '#10b981',
        weight: 5,
        opacity: 0.95,
      });
      safeLine.bindPopup(`
        <div style="font-size: 12px;">
          <strong style="color: #10b981;">Flood-Safe Elevation Route</strong><br/>
          Flooded Segments: <strong>${routeResult.safe_route.flooded_segments_count}</strong><br/>
          Max Water Depth: <strong>${routeResult.safe_route.max_water_depth_cm} cm</strong><br/>
          Est. Travel Time: <strong>${routeResult.safe_route.estimated_time_minutes} min</strong>
        </div>
      `);
      routesLayerRef.current.addLayer(safeLine);
    }
  }, [routeResult, showRoutesLayer]);

  // 9. Origin & Destination Markers
  useEffect(() => {
    if (!markersLayerRef.current) return;
    markersLayerRef.current.clearLayers();

    const originIcon = L.divIcon({
      html: `
        <div style="width: 28px; height: 28px; border-radius: 50%; background: #3b82f6; border: 2.5px solid #ffffff; box-shadow: 0 4px 14px rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; font-weight: 900; color: #ffffff; font-size: 13px;">
          A
        </div>
      `,
      className: 'origin-marker',
      iconSize: [28, 28],
      iconAnchor: [14, 14],
    });

    const origMarker = L.marker([origin[1], origin[0]], { icon: originIcon });
    origMarker.bindPopup('<strong>ORIGIN (Point A)</strong>');
    markersLayerRef.current.addLayer(origMarker);

    const destIcon = L.divIcon({
      html: `
        <div style="width: 28px; height: 28px; border-radius: 50%; background: #ef4444; border: 2.5px solid #ffffff; box-shadow: 0 4px 14px rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; font-weight: 900; color: #ffffff; font-size: 13px;">
          B
        </div>
      `,
      className: 'dest-marker',
      iconSize: [28, 28],
      iconAnchor: [14, 14],
    });

    const destMarker = L.marker([destination[1], destination[0]], { icon: destIcon });
    destMarker.bindPopup('<strong>DESTINATION (Point B)</strong>');
    markersLayerRef.current.addLayer(destMarker);
  }, [origin, destination]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainerRef} className="w-full h-full z-0" />

      {/* Top Floating Map Controls: Centered horizontally with zero sidebar collisions */}
      <div className="absolute top-3 sm:top-3.5 left-1/2 -translate-x-1/2 z-20 flex items-center gap-1.5 sm:gap-2 pointer-events-auto">
        {/* Search Bar with Autocomplete */}
        <div className="relative">
          <div className="flex items-center bg-slate-900/95 border border-slate-700/80 rounded-xl px-2 sm:px-3 py-1 sm:py-1.5 shadow-2xl backdrop-blur-md w-28 xs:w-36 sm:w-60 md:w-72 focus-within:w-44 xs:focus-within:w-48 sm:focus-within:w-80 transition-all">
            <Search className="w-3 sm:w-3.5 h-3 sm:h-3.5 text-slate-400 mr-1.5 sm:mr-2 shrink-0" />
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setShowSearchResults(true)}
              className="bg-transparent text-xs text-white placeholder-slate-400 focus:outline-none w-full"
            />
            {searchQuery && (
              <button
                onClick={() => {
                  setSearchQuery('');
                  setSearchResults([]);
                }}
                className="text-slate-500 hover:text-white p-0.5"
              >
                <X className="w-3 h-3" />
              </button>
            )}
            {isSearching && (
              <div className="w-3.5 h-3.5 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin shrink-0 ml-1.5" />
            )}
          </div>

          {/* Autocomplete Dropdown */}
          {showSearchResults && searchQuery.trim().length >= 2 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl overflow-hidden z-30 max-h-56 overflow-y-auto">
              {searchResults.length > 0 ? (
                searchResults.map((loc) => (
                  <button
                    key={loc.id}
                    onClick={() => handleSelectSearchResult(loc)}
                    className="w-full text-left px-3 py-2 text-xs hover:bg-slate-800 flex items-center justify-between border-b border-slate-800 last:border-b-0 transition-colors"
                  >
                    <div>
                      <div className="font-semibold text-slate-200">{loc.name}</div>
                      <div className="text-[10px] text-slate-400 capitalize">{loc.category} • {loc.elevation_m}m elev</div>
                    </div>
                    <Navigation className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                  </button>
                ))
              ) : (
                !isSearching && (
                  <div className="px-4 py-3 text-xs text-slate-400 text-center italic">
                    No matching locations found for "{searchQuery}"
                  </div>
                )
              )}
            </div>
          )}
        </div>

        {/* Basemap Switcher — Desktop/Tablet (sm+) */}
        <div className="hidden sm:flex bg-slate-900/95 border border-slate-700/80 p-1 rounded-xl shadow-2xl backdrop-blur-md items-center gap-1">
          <button
            onClick={() => onBasemapChange('dark')}
            className={`px-2.5 py-1 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all ${
              basemap === 'dark' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
            title="Esri Dark Gray Canvas (Watermark-Free)"
          >
            <Map className="w-3 h-3" />
            <span>Dark</span>
          </button>
          <button
            onClick={() => onBasemapChange('satellite')}
            className={`px-2.5 py-1 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all ${
              basemap === 'satellite' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
            title="Esri World Imagery"
          >
            <Globe className="w-3 h-3" />
            <span>Satellite</span>
          </button>
          <button
            onClick={() => onBasemapChange('streets')}
            className={`px-2.5 py-1 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all ${
              basemap === 'streets' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
            title="OpenStreetMap Streets"
          >
            <Layers className="w-3 h-3" />
            <span>Streets</span>
          </button>
          <button
            onClick={() => onBasemapChange('topo')}
            className={`px-2.5 py-1 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all ${
              basemap === 'topo' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
            title="OpenTopoMap Topography"
          >
            <Mountain className="w-3 h-3" />
            <span>Topo</span>
          </button>
        </div>

        {/* Basemap Switcher — Mobile (< sm) */}
        <div className="sm:hidden relative">
          <button
            onClick={() => setShowBasemapMenu(!showBasemapMenu)}
            className="bg-slate-900/95 border border-slate-700/80 px-2.5 py-1.5 rounded-xl shadow-2xl backdrop-blur-md flex items-center gap-1.5 text-xs text-slate-200"
            title="Switch Basemap Tile Layer"
          >
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span className="capitalize text-[11px] font-semibold">{basemap}</span>
          </button>

          {showBasemapMenu && (
            <div className="absolute right-0 top-full mt-1 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-1 z-30 min-w-[120px] flex flex-col gap-0.5 animate-in fade-in">
              {(['dark', 'satellite', 'streets', 'topo'] as BasemapType[]).map((bm) => (
                <button
                  key={bm}
                  onClick={() => {
                    onBasemapChange(bm);
                    setShowBasemapMenu(false);
                  }}
                  className={`text-left px-2.5 py-1.5 rounded-lg text-xs capitalize transition-colors ${
                    basemap === bm ? 'bg-blue-600 text-white font-bold' : 'text-slate-300 hover:bg-slate-800'
                  }`}
                >
                  {bm}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
