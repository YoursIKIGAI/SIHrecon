import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { RouteResponse, FloodedRoadSegment, DrainNodeStatus, BasemapType, LocationSearchResult } from '../types';
import { apiClient } from '../api/client';
import { Search, Map, Globe, Mountain, Navigation, Compass, Layers, X, Info } from 'lucide-react';

interface MapViewProps {
  floodGeoJson: any;
  drainageGeoJson: any;
  floodedRoads: FloodedRoadSegment[];
  overflowNodes: DrainNodeStatus[];
  routeResult: RouteResponse | null;
  origin: [number, number];
  destination: [number, number];
  onMapClick: (coords: [number, number]) => void;
  onOriginChange?: (coords: [number, number]) => void;
  onDestinationChange?: (coords: [number, number]) => void;
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
  historicalObservations?: any;
  showHistoricalLayer?: boolean;
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
  onOriginChange,
  onDestinationChange,
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
  historicalObservations,
  showHistoricalLayer = true,
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
  const historicalLayerRef = useRef<L.LayerGroup | null>(null);

  // Search state
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<LocationSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [showSearchResults, setShowSearchResults] = useState<boolean>(false);
  const [showBasemapMenu, setShowBasemapMenu] = useState<boolean>(false);

  // Reliable Basemap Tile Providers
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
    historicalLayerRef.current = L.layerGroup().addTo(map);

    map.on('click', (e: L.LeafletMouseEvent) => {
      onMapClick([Number(e.latlng.lng.toFixed(4)), Number(e.latlng.lat.toFixed(4))]);
    });

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // 2. Pan when City Center changes
  useEffect(() => {
    if (mapInstanceRef.current && cityCenter) {
      mapInstanceRef.current.flyTo([cityCenter[1], cityCenter[0]], 13, { duration: 1.2 });
    }
  }, [cityCenter]);

  // 3. Basemap switcher
  useEffect(() => {
    if (!mapInstanceRef.current || !tileLayerRef.current) return;
    const tileConfig = BASEMAP_TILES[basemap] || BASEMAP_TILES.dark;
    mapInstanceRef.current.removeLayer(tileLayerRef.current);
    tileLayerRef.current = L.tileLayer(tileConfig.url, {
      attribution: tileConfig.attribution,
      maxZoom: tileConfig.maxZoom,
    }).addTo(mapInstanceRef.current);
    tileLayerRef.current.bringToBack();
  }, [basemap]);

  // 4. Flood Grid Polygons
  useEffect(() => {
    if (!floodLayerRef.current) return;
    floodLayerRef.current.clearLayers();
    if (!showFloodLayer || !floodGeoJson) return;

    L.geoJSON(floodGeoJson, {
      filter: (feature) => feature.geometry.type === 'Polygon',
      style: (feature) => {
        const depth = feature?.properties?.water_depth_cm || 0;
        return {
          fillColor: getFloodColor(depth),
          fillOpacity: getFloodOpacity(depth),
          color: getFloodColor(depth),
          weight: 0.8,
          opacity: 0.6,
        };
      },
      onEachFeature: (feature, layer) => {
        const p = feature.properties;
        layer.bindTooltip(`
          <div style="font-family: monospace; font-size: 11px;">
            <strong>Water Depth:</strong> ${p.water_depth_cm} cm<br/>
            <strong>Risk Level:</strong> ${p.risk_level}<br/>
            <strong>Elevation:</strong> ${p.elevation_m} m
          </div>
        `, { sticky: true });
      },
    }).addTo(floodLayerRef.current);
  }, [floodGeoJson, showFloodLayer]);

  // 5. Road Network Overlay
  useEffect(() => {
    if (!roadsLayerRef.current) return;
    roadsLayerRef.current.clearLayers();
    if (!showRoadsLayer || !floodedRoads) return;

    floodedRoads.forEach((road) => {
      const latlngs = road.coordinates.map((c) => [c[1], c[0]] as [number, number]);
      const isFlooded = road.water_depth_cm >= 5.0;
      const isBlocked = road.is_blocked;

      const poly = L.polyline(latlngs, {
        color: isBlocked ? '#ef4444' : isFlooded ? '#f59e0b' : '#334155',
        weight: isBlocked ? 4.5 : isFlooded ? 3.5 : 1.5,
        opacity: isBlocked ? 0.95 : isFlooded ? 0.85 : 0.4,
        dashArray: isBlocked ? '6, 6' : undefined,
      });

      poly.bindTooltip(`
        <div style="font-family: sans-serif; font-size: 11px;">
          <strong>${road.name}</strong><br/>
          Depth: <strong>${road.water_depth_cm} cm</strong><br/>
          Status: <span style="color: ${isBlocked ? '#ef4444' : '#10b981'}; font-weight: bold;">
            ${isBlocked ? 'IMPASSABLE / BLOCKED' : road.risk_level}
          </span>
        </div>
      `, { sticky: true });

      roadsLayerRef.current?.addLayer(poly);
    });
  }, [floodedRoads, showRoadsLayer]);

  // 6. Drainage Network (Verified vs Inferred + Surcharge)
  useEffect(() => {
    if (!drainageLayerRef.current) return;
    drainageLayerRef.current.clearLayers();
    if (!showDrainageLayer) return;

    if (drainageGeoJson) {
      L.geoJSON(drainageGeoJson, {
        filter: (feature) => feature.geometry.type === 'LineString',
        style: (feature) => {
          const isVerified = feature?.properties?.verification_status === 'verified';
          return {
            color: '#06b6d4',
            weight: 2.2,
            opacity: isVerified ? 0.8 : 0.45,
            dashArray: isVerified ? undefined : '4, 4',
          };
        },
        onEachFeature: (feature, layer) => {
          const p = feature.properties;
          layer.bindTooltip(`
            <div style="font-size: 11px;">
              <strong>Drain Channel:</strong> ${p.name || 'Storm Trunk'}<br/>
              Type: ${p.verification_status || 'verified'}<br/>
              Slope: ${p.slope_percent || 0.2}%
            </div>
          `, { sticky: true });
        },
      }).addTo(drainageLayerRef.current);
    }

    if (overflowNodes) {
      overflowNodes.forEach((node) => {
        const isSurcharging = node.is_overflowing;
        const marker = L.circleMarker([node.lat, node.lon], {
          radius: isSurcharging ? 6 : 4,
          fillColor: isSurcharging ? '#dc2626' : '#0284c7',
          fillOpacity: 0.9,
          color: '#ffffff',
          weight: 1.5,
        });

        marker.bindTooltip(`
          <div style="font-size: 11px;">
            <strong>${node.name}</strong> (${node.type})<br/>
            Location: ${node.street_location}<br/>
            Status: <span style="color: ${isSurcharging ? '#ef4444' : '#38bdf8'}; font-weight: bold;">
              ${isSurcharging ? `OVERFLOWING (${node.overflow_rate_m3_s} m³/s)` : 'Normal'}
            </span><br/>
            Classification: ${node.verification_status || 'verified'}
          </div>
        `, { sticky: true });

        drainageLayerRef.current?.addLayer(marker);
      });
    }
  }, [drainageGeoJson, overflowNodes, showDrainageLayer]);

  // 7. Historical Observation Ground-Truth Layer
  useEffect(() => {
    if (!historicalLayerRef.current) return;
    historicalLayerRef.current.clearLayers();
    if (!showHistoricalLayer || !historicalObservations?.features) return;

    historicalObservations.features.forEach((feat: any) => {
      const coords = feat.geometry.coordinates;
      const p = feat.properties;
      const marker = L.circleMarker([coords[1], coords[0]], {
        radius: 7,
        fillColor: '#f59e0b',
        fillOpacity: 0.85,
        color: '#ffffff',
        weight: 2,
      });

      marker.bindPopup(`
        <div style="font-size: 12px; font-family: sans-serif;">
          <strong style="color: #f59e0b;">Verified Historical Flood Point</strong><br/>
          <strong>Location:</strong> ${p.name}<br/>
          <strong>Observed Depth:</strong> <span style="font-weight: bold; color: #ef4444;">${p.observed_depth_cm} cm</span><br/>
          <strong>Source:</strong> ${p.source}
        </div>
      `);

      historicalLayerRef.current?.addLayer(marker);
    });
  }, [historicalObservations, showHistoricalLayer]);

  // 8. 3-Route Generation Overlay (Fastest, Flood-Safe, Alternative)
  useEffect(() => {
    if (!routesLayerRef.current) return;
    routesLayerRef.current.clearLayers();
    if (!showRoutesLayer || !routeResult) return;

    // Normal / Fastest Route (Red if flooded, Gray if clear)
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
          <strong>Direct / Fastest Route</strong><br/>
          Flooded Segments: <strong>${routeResult.normal_route.flooded_segments_count}</strong><br/>
          Max Water Depth: <strong>${routeResult.normal_route.max_water_depth_cm} cm</strong><br/>
          Distance: ${routeResult.normal_route.distance_km} km (${routeResult.normal_route.estimated_time_minutes} min)
        </div>
      `);
      routesLayerRef.current.addLayer(normLine);
    }

    // Flood-Safe Route (Emerald Solid)
    if (routeResult.safe_route && routeResult.safe_route.coordinates.length > 0) {
      const safeCoords = routeResult.safe_route.coordinates.map((c) => [c[1], c[0]] as [number, number]);
      const safeLine = L.polyline(safeCoords, {
        color: '#10b981',
        weight: 5,
        opacity: 0.95,
      });
      safeLine.bindPopup(`
        <div style="font-size: 12px;">
          <strong style="color: #10b981;">Flood-Safe Route (Elevated Corridor)</strong><br/>
          Flooded Segments: <strong>${routeResult.safe_route.flooded_segments_count}</strong><br/>
          Max Water Depth: <strong>${routeResult.safe_route.max_water_depth_cm} cm</strong><br/>
          Travel Time: <strong>${routeResult.safe_route.estimated_time_minutes} min</strong> (${routeResult.safe_route.distance_km} km)
        </div>
      `);
      routesLayerRef.current.addLayer(safeLine);
    }

    // Alternative Route (Indigo Dashed)
    if (routeResult.alternative_route && routeResult.alternative_route.coordinates.length > 0) {
      const altCoords = routeResult.alternative_route.coordinates.map((c) => [c[1], c[0]] as [number, number]);
      const altLine = L.polyline(altCoords, {
        color: '#6366f1',
        weight: 4,
        opacity: 0.85,
        dashArray: '8, 6',
      });
      altLine.bindPopup(`
        <div style="font-size: 12px;">
          <strong style="color: #6366f1;">Alternative Route (Balanced Trade-Off)</strong><br/>
          Flooded Segments: <strong>${routeResult.alternative_route.flooded_segments_count}</strong><br/>
          Max Water Depth: <strong>${routeResult.alternative_route.max_water_depth_cm} cm</strong><br/>
          Travel Time: <strong>${routeResult.alternative_route.estimated_time_minutes} min</strong>
        </div>
      `);
      routesLayerRef.current.addLayer(altLine);
    }
  }, [routeResult, showRoutesLayer]);

  // 9. Draggable Origin & Destination Markers
  useEffect(() => {
    if (!markersLayerRef.current) return;
    markersLayerRef.current.clearLayers();

    const originIcon = L.divIcon({
      html: `
        <div style="width: 28px; height: 28px; border-radius: 50%; background: #3b82f6; border: 2.5px solid #ffffff; box-shadow: 0 4px 14px rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; font-weight: 900; color: #ffffff; font-size: 13px; cursor: grab;">
          A
        </div>
      `,
      className: 'origin-marker',
      iconSize: [28, 28],
      iconAnchor: [14, 14],
    });

    const origMarker = L.marker([origin[1], origin[0]], { 
      icon: originIcon,
      draggable: true,
      title: "Drag to change Origin (Point A)"
    });
    origMarker.bindPopup('<strong>ORIGIN (Point A)</strong><br/><span style="font-size: 10px; color: #64748b;">Drag me to recalculate route!</span>');
    origMarker.on('dragend', (e: any) => {
      const ll = e.target.getLatLng();
      const newCoords: [number, number] = [Number(ll.lng.toFixed(4)), Number(ll.lat.toFixed(4))];
      onOriginChange?.(newCoords);
    });
    markersLayerRef.current.addLayer(origMarker);

    const destIcon = L.divIcon({
      html: `
        <div style="width: 28px; height: 28px; border-radius: 50%; background: #ef4444; border: 2.5px solid #ffffff; box-shadow: 0 4px 14px rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; font-weight: 900; color: #ffffff; font-size: 13px; cursor: grab;">
          B
        </div>
      `,
      className: 'dest-marker',
      iconSize: [28, 28],
      iconAnchor: [14, 14],
    });

    const destMarker = L.marker([destination[1], destination[0]], { 
      icon: destIcon,
      draggable: true,
      title: "Drag to change Destination (Point B)"
    });
    destMarker.bindPopup('<strong>DESTINATION (Point B)</strong><br/><span style="font-size: 10px; color: #64748b;">Drag me to recalculate route!</span>');
    destMarker.on('dragend', (e: any) => {
      const ll = e.target.getLatLng();
      const newCoords: [number, number] = [Number(ll.lng.toFixed(4)), Number(ll.lat.toFixed(4))];
      onDestinationChange?.(newCoords);
    });
    markersLayerRef.current.addLayer(destMarker);
  }, [origin, destination, onOriginChange, onDestinationChange]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainerRef} className="w-full h-full z-0" />

      {/* Top Floating Map Controls */}
      <div className="absolute top-3 sm:top-3.5 left-1/2 -translate-x-1/2 z-20 flex items-center gap-1.5 sm:gap-2 pointer-events-auto">
        {/* Search Bar with Autocomplete */}
        <div className="relative">
          <div className="flex items-center bg-slate-900/95 border border-slate-700/80 rounded-xl px-2 sm:px-3 py-1 sm:py-1.5 shadow-2xl backdrop-blur-md w-28 xs:w-36 sm:w-60 md:w-72 focus-within:w-44 xs:focus-within:w-48 sm:focus-within:w-80 transition-all">
            <Search className="w-3 sm:w-3.5 h-3 sm:h-3.5 text-slate-400 mr-1.5 sm:mr-2 shrink-0" />
            <input
              type="text"
              placeholder="Search locality..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setShowSearchResults(true)}
              className="bg-transparent text-xs text-white placeholder-slate-400 focus:outline-none w-full"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="text-slate-400 hover:text-white ml-1"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>

        {/* Basemap Switcher Menu */}
        <div className="relative">
          <button
            onClick={() => setShowBasemapMenu(!showBasemapMenu)}
            className="p-1.5 sm:p-2 bg-slate-900/95 border border-slate-700/80 rounded-xl shadow-2xl text-slate-300 hover:text-white transition-colors"
            title="Switch Basemap Style"
          >
            <Layers className="w-4 h-4 text-cyan-400" />
          </button>

          {showBasemapMenu && (
            <div className="absolute right-0 top-full mt-2 w-36 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-1 z-30 animate-in fade-in">
              {(['dark', 'satellite', 'streets', 'topo'] as BasemapType[]).map((bm) => (
                <button
                  key={bm}
                  onClick={() => {
                    onBasemapChange(bm);
                    setShowBasemapMenu(false);
                  }}
                  className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs capitalize transition-colors ${
                    basemap === bm
                      ? 'bg-blue-600 text-white font-bold'
                      : 'text-slate-300 hover:bg-slate-800'
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
