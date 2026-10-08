import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { RouteResponse, FloodedRoadSegment, DrainNodeStatus, BasemapType, LocationSearchResult } from '../types';
import { apiClient } from '../api/client';
import { Search, Map, Globe, Mountain, Navigation, Compass, Radio, AlertOctagon } from 'lucide-react';

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
  const radarLayerRef = useRef<L.LayerGroup | null>(null);

  // Search state
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<LocationSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [showSearchResults, setShowSearchResults] = useState<boolean>(false);

  // Basemap Tile Provider API URLs
  const BASEMAP_TILES: Record<BasemapType, { url: string; attribution: string; maxZoom: number }> = {
    dark: {
      url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      attribution: '&copy; CARTO &copy; OpenStreetMap',
      maxZoom: 19,
    },
    satellite: {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      attribution: '&copy; Esri World Imagery &copy; Maxar, Earthstar Geographics',
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

    const map = L.map(mapContainerRef.current, {
      center: [19.075, 72.875],
      zoom: 13,
      zoomControl: false,
    });

    // Initial Tile Layer
    const currentTileConfig = BASEMAP_TILES[basemap] || BASEMAP_TILES.dark;
    tileLayerRef.current = L.tileLayer(currentTileConfig.url, {
      attribution: currentTileConfig.attribution,
      maxZoom: currentTileConfig.maxZoom,
    }).addTo(map);

    L.control.zoom({ position: 'topright' }).addTo(map);

    floodLayerRef.current = L.layerGroup().addTo(map);
    radarLayerRef.current = L.layerGroup().addTo(map);
    roadsLayerRef.current = L.layerGroup().addTo(map);
    drainageLayerRef.current = L.layerGroup().addTo(map);
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

  // 3. Search Handler with API Integration
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
    }, 250);

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

  // 5. Render Doppler Radar Storm Overlay
  useEffect(() => {
    if (!radarLayerRef.current) return;
    radarLayerRef.current.clearLayers();

    if (!showRadarOverlay) return;

    // Convective storm core radar circle
    const radarCore = L.circle([19.073, 72.874], {
      radius: 1400,
      color: '#ef4444',
      weight: 1.5,
      dashArray: '4, 4',
      fillColor: '#dc2626',
      fillOpacity: 0.22,
    });
    radarCore.bindPopup(`<strong>DOPPLER RADAR ECHO: ${radarReflectivityDbz} dBZ</strong><br/>Intense convective storm precipitation core`);
    radarLayerRef.current.addLayer(radarCore);

    const radarOuter = L.circle([19.073, 72.874], {
      radius: 2800,
      color: '#f59e0b',
      weight: 1,
      dashArray: '6, 6',
      fillColor: '#f59e0b',
      fillOpacity: 0.12,
    });
    radarLayerRef.current.addLayer(radarOuter);
  }, [showRadarOverlay, radarReflectivityDbz]);

  // 6. Render Road Network
  useEffect(() => {
    if (!roadsLayerRef.current) return;
    roadsLayerRef.current.clearLayers();

    if (!showRoadsLayer || !floodedRoads) return;

    floodedRoads.forEach((road) => {
      const latlngs: L.LatLngExpression[] = road.coordinates.map(([lon, lat]) => [lat, lon]);
      const isFlooded = road.water_depth_cm >= 5.0;
      const isBlocked = road.is_blocked;

      const polyline = L.polyline(latlngs, {
        color: isBlocked ? '#ef4444' : isFlooded ? getFloodColor(road.water_depth_cm) : '#64748b',
        weight: isBlocked ? 6 : isFlooded ? 4.5 : 2.5,
        opacity: isFlooded ? 0.95 : 0.45,
        dashArray: isBlocked ? '8, 6' : undefined,
      });

      polyline.bindPopup(`
        <div style="font-family: inherit; font-size: 12px; line-height: 1.5;">
          <div style="font-weight: 800; color: #f8fafc; margin-bottom: 2px;">${road.name}</div>
          <div>Condition: <strong style="color: ${road.is_blocked ? '#ef4444' : '#10b981'}">${road.is_blocked ? 'IMPASSABLE / BLOCKED (>40cm)' : 'PASSABLE'}</strong></div>
          <div>Inundation Depth: <strong style="color: ${getFloodColor(road.water_depth_cm)}; font-size: 13px;">${road.water_depth_cm} cm</strong> (${road.risk_level})</div>
          <div>Segment Length: <strong>${road.length_m} m</strong></div>
        </div>
      `);

      roadsLayerRef.current?.addLayer(polyline);
    });
  }, [floodedRoads, showRoadsLayer]);

  // 7. Render Subsurface Drainage (Pipes & Surcharged Manholes)
  useEffect(() => {
    if (!drainageLayerRef.current) return;
    drainageLayerRef.current.clearLayers();

    if (!showDrainageLayer || !drainageGeoJson) return;

    // Pipes
    const pipesLayer = L.geoJSON(drainageGeoJson, {
      filter: (feature) => feature.properties.element === 'edge',
      style: (feature) => {
        const isSurcharged = feature?.properties.is_surcharged;
        return {
          color: isSurcharged ? '#f87171' : '#06b6d4',
          weight: feature?.properties.capacity_m3_s > 5 ? 4.5 : 2.5,
          opacity: 0.85,
          dashArray: isSurcharged ? '5, 5' : undefined,
        };
      },
      onEachFeature: (feature, layer) => {
        const p = feature.properties;
        layer.bindPopup(`
          <div style="font-size: 12px;">
            <div style="font-weight: bold; color: #06b6d4;">DRAINAGE CULVERT ${p.id}</div>
            <div>Flow: <strong>${p.current_flow_m3_s} / ${p.capacity_m3_s} m³/s</strong></div>
            <div>Diameter: <strong>${p.diameter_m} m</strong></div>
            <div>Hydraulic Status: <strong>${p.is_surcharged ? 'SURCHARGED / HIGH PRESSURE' : 'NORMAL CONVEYANCE'}</strong></div>
          </div>
        `);
      },
    });
    drainageLayerRef.current.addLayer(pipesLayer);

    // Nodes (manholes, outfalls)
    if (drainageGeoJson.features) {
      drainageGeoJson.features
        .filter((f: any) => f.properties.element === 'node')
        .forEach((feat: any) => {
          const [lon, lat] = feat.geometry.coordinates;
          const p = feat.properties;
          const isOverflowing = overflowNodes.some((o) => o.node_id === p.id);

          if (isOverflowing) {
            const overflowHtml = `
              <div style="position: relative; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;">
                <div class="overflow-marker-ring"></div>
                <div style="width: 14px; height: 14px; border-radius: 50%; background: #ef4444; border: 2.5px solid #ffffff; box-shadow: 0 0 14px #ef4444;"></div>
              </div>
            `;
            const icon = L.divIcon({
              html: overflowHtml,
              className: 'overflow-icon',
              iconSize: [32, 32],
              iconAnchor: [16, 16],
            });
            const marker = L.marker([lat, lon], { icon });
            marker.bindPopup(`
              <div style="font-size: 12px;">
                <div style="font-weight: 800; color: #ef4444; margin-bottom: 2px;">SURCHARGED DRAINAGE INLET</div>
                <div>Location: <strong>${p.street_location}</strong></div>
                <div>Backflow State: <strong style="color: #ef4444;">EXCEEDED HYDRAULIC CAPACITY</strong></div>
              </div>
            `);
            drainageLayerRef.current?.addLayer(marker);
          } else {
            const circle = L.circleMarker([lat, lon], {
              radius: p.type === 'outfall' ? 8 : 4.5,
              fillColor: p.type === 'outfall' ? '#3b82f6' : '#0891b2',
              color: '#ffffff',
              weight: 1.5,
              fillOpacity: 0.9,
            });
            circle.bindPopup(`
              <div style="font-size: 12px;">
                <div style="font-weight: 700; color: #38bdf8;">${p.street_location}</div>
                <div>Type: <strong>${p.type.toUpperCase()}</strong></div>
                <div>Storage Buffer: <strong>${p.storage_capacity_m3} m³</strong></div>
                <div>Elevation: <strong>${p.elevation_m} m</strong></div>
              </div>
            `);
            drainageLayerRef.current?.addLayer(circle);
          }
        });
    }
  }, [drainageGeoJson, overflowNodes, showDrainageLayer]);

  // 8. Render Routing Comparison (Glowing lines)
  useEffect(() => {
    if (!routesLayerRef.current) return;
    routesLayerRef.current.clearLayers();

    if (!showRoutesLayer || !routeResult) return;

    // Normal Route (Red/Orange dashed when passing flooded areas)
    if (routeResult.normal_route && routeResult.normal_route.coordinates.length > 0) {
      const normalLatlngs: L.LatLngExpression[] = routeResult.normal_route.coordinates.map(
        ([lon, lat]) => [lat, lon]
      );
      const isDangerous = routeResult.normal_route.max_water_depth_cm > 20.0;

      const normalPolyline = L.polyline(normalLatlngs, {
        color: isDangerous ? '#ef4444' : '#94a3b8',
        weight: 5,
        opacity: 0.9,
        dashArray: isDangerous ? '8, 8' : '4, 4',
      });

      normalPolyline.bindPopup(`
        <div style="font-size: 12px;">
          <div style="font-weight: 800; color: #ef4444;">STANDARD DIRECT ROUTE</div>
          <div>Estimated Travel Time: <strong>${routeResult.normal_route.estimated_time_minutes} min</strong></div>
          <div>Distance: <strong>${routeResult.normal_route.distance_km} km</strong></div>
          <div>Max Inundation Encountered: <strong style="color: #ef4444; font-size: 14px;">${routeResult.normal_route.max_water_depth_cm} cm</strong></div>
          <div>Hazard Risk: <strong>${routeResult.normal_route.flood_risk}</strong></div>
        </div>
      `);
      routesLayerRef.current.addLayer(normalPolyline);
    }

    // Flood-Safe Route (Glowing bold Emerald line)
    if (routeResult.safe_route && routeResult.safe_route.coordinates.length > 0) {
      const safeLatlngs: L.LatLngExpression[] = routeResult.safe_route.coordinates.map(
        ([lon, lat]) => [lat, lon]
      );

      // Outer glow
      const glowPolyline = L.polyline(safeLatlngs, {
        color: '#10b981',
        weight: 11,
        opacity: 0.4,
      });
      routesLayerRef.current.addLayer(glowPolyline);

      // Core line
      const safePolyline = L.polyline(safeLatlngs, {
        color: '#34d399',
        weight: 5.5,
        opacity: 1.0,
      });

      safePolyline.bindPopup(`
        <div style="font-size: 12px;">
          <div style="font-weight: 800; color: #10b981;">RECOMMENDED FLOOD-SAFE ROUTE</div>
          <div>Estimated Travel Time: <strong>${routeResult.safe_route.estimated_time_minutes} min</strong></div>
          <div>Distance: <strong>${routeResult.safe_route.distance_km} km</strong></div>
          <div>Avoided Submerged Segments: <strong style="color: #10b981; font-size: 13px;">${routeResult.avoided_flooded_roads} segments</strong></div>
          <div>Max Water Depth: <strong>${routeResult.safe_route.max_water_depth_cm} cm</strong> (Passable)</div>
        </div>
      `);
      routesLayerRef.current.addLayer(safePolyline);
    }
  }, [routeResult, showRoutesLayer]);

  // 9. Render Origin (A) and Destination (B) Markers
  useEffect(() => {
    if (!markersLayerRef.current) return;
    markersLayerRef.current.clearLayers();

    const originIcon = L.divIcon({
      html: `
        <div style="width: 32px; height: 32px; border-radius: 50%; background: #10b981; border: 3px solid #ffffff; box-shadow: 0 4px 14px rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; font-weight: 900; color: #ffffff; font-size: 14px;">
          A
        </div>
      `,
      className: 'origin-marker',
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    });

    const origMarker = L.marker([origin[1], origin[0]], { icon: originIcon });
    origMarker.bindPopup('<strong>ORIGIN (Point A)</strong>');
    markersLayerRef.current.addLayer(origMarker);

    const destIcon = L.divIcon({
      html: `
        <div style="width: 32px; height: 32px; border-radius: 50%; background: #ef4444; border: 3px solid #ffffff; box-shadow: 0 4px 14px rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; font-weight: 900; color: #ffffff; font-size: 14px;">
          B
        </div>
      `,
      className: 'dest-marker',
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    });

    const destMarker = L.marker([destination[1], destination[0]], { icon: destIcon });
    destMarker.bindPopup('<strong>DESTINATION (Point B)</strong>');
    markersLayerRef.current.addLayer(destMarker);
  }, [origin, destination]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainerRef} className="w-full h-full z-0" />

      {/* Top Floating Map Controls: Location Search API & Basemap Provider Switcher */}
      <div className="absolute top-4 left-96 z-20 flex items-center gap-2 pointer-events-auto">
        {/* Search Bar with Autocomplete API */}
        <div className="relative">
          <div className="flex items-center bg-slate-900/90 border border-slate-700/80 rounded-xl px-3 py-1.5 shadow-xl backdrop-blur-md w-72">
            <Search className="w-4 h-4 text-slate-400 mr-2 shrink-0" />
            <input
              type="text"
              placeholder="Search landmarks or choke points..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setShowSearchResults(true)}
              className="bg-transparent text-xs text-white placeholder-slate-400 focus:outline-none w-full"
            />
          </div>

          {/* Autocomplete Dropdown */}
          {showSearchResults && searchResults.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl overflow-hidden z-30 max-h-56 overflow-y-auto">
              {searchResults.map((loc) => (
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
              ))}
            </div>
          )}
        </div>

        {/* Basemap API Switcher */}
        <div className="bg-slate-900/90 border border-slate-700/80 p-1 rounded-xl shadow-xl backdrop-blur-md flex items-center gap-1">
          <button
            onClick={() => onBasemapChange('dark')}
            className={`px-2.5 py-1 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all ${
              basemap === 'dark' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
            title="CartoDB Dark Matter Basemap"
          >
            <Map className="w-3.5 h-3.5" />
            <span>Dark</span>
          </button>
          <button
            onClick={() => onBasemapChange('satellite')}
            className={`px-2.5 py-1 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all ${
              basemap === 'satellite' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
            title="Esri World Satellite Imagery"
          >
            <Globe className="w-3.5 h-3.5" />
            <span>Satellite</span>
          </button>
          <button
            onClick={() => onBasemapChange('topo')}
            className={`px-2.5 py-1 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all ${
              basemap === 'topo' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
            title="OpenTopoMap Elevation Contour Map"
          >
            <Mountain className="w-3.5 h-3.5" />
            <span>Topo</span>
          </button>
        </div>
      </div>
    </div>
  );
};
