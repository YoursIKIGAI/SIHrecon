import React, { useState } from 'react';
import { 
  Navigation, 
  ShieldCheck, 
  AlertOctagon, 
  Clock, 
  MapPin, 
  RotateCw, 
  Check, 
  Truck, 
  Car,
  Ambulance,
  ArrowRight,
  GitBranch,
  ShieldAlert,
  Info
} from 'lucide-react';
import { RouteResponse, RouteOption } from '../types';

interface RoutingPanelProps {
  origin: [number, number];
  destination: [number, number];
  onOriginChange: (coords: [number, number]) => void;
  onDestinationChange: (coords: [number, number]) => void;
  routeResult: RouteResponse | null;
  isLoading: boolean;
  onRecalculateRoute: () => void;
  mode: string;
  onModeChange: (m: string) => void;
  activeCity?: string;
}

const CITY_PRESET_ROUTES: Record<string, { name: string; origin: [number, number]; destination: [number, number]; desc: string }[]> = {
  mumbai: [
    {
      name: 'Milan Subway → Airport T2',
      origin: [72.874, 19.073],
      destination: [72.868, 19.088],
      desc: 'Crosses documented Milan Subway underpass depression (40+ cm hazard)',
    },
    {
      name: 'Harbor Gate → Trauma Hospital',
      origin: [72.854, 19.065],
      destination: [72.888, 19.076],
      desc: 'Coastal bay to emergency trauma facility via central basin',
    },
    {
      name: 'South Port → Tech Park Ridge',
      origin: [72.862, 19.058],
      destination: [72.898, 19.085],
      desc: 'Full city diagonal corridor testing elevated flyovers',
    },
  ],
  delhi: [
    {
      name: 'Connaught Place → Kashmere Gate ISBT',
      origin: [77.218, 28.631],
      destination: [77.228, 28.667],
      desc: 'Traverses historic Yamuna flood-impacted Ring Road corridor',
    },
    {
      name: 'ITO Junction → Pragati Maidan Tunnel',
      origin: [77.241, 28.630],
      destination: [77.243, 28.618],
      desc: 'Tests drainage pump failure chokepoint at ITO Vikas Marg',
    },
    {
      name: 'AIIMS Trauma → Yamuna Bank Metro',
      origin: [77.207, 28.568],
      destination: [77.262, 28.623],
      desc: 'Emergency medical link across south-central floodplain',
    },
  ],
  chennai: [
    {
      name: 'Saidapet Bridge → Velachery Main Rd',
      origin: [80.222, 13.021],
      destination: [80.217, 12.981],
      desc: 'Crosses Adyar River flood breach corridor into Velachery basin',
    },
    {
      name: 'Chennai Airport GST → Anna Salai Gemini',
      origin: [80.164, 12.985],
      destination: [80.251, 13.052],
      desc: 'GST arterial link severely inundated in Dec 2015 deluge',
    },
    {
      name: 'T. Nagar Panagal Park → Chennai Central',
      origin: [80.231, 13.041],
      destination: [80.276, 13.082],
      desc: 'Commercial core through Buckingham Canal lowlands',
    },
  ],
};

export const RoutingPanel: React.FC<RoutingPanelProps> = ({
  origin,
  destination,
  onOriginChange,
  onDestinationChange,
  routeResult,
  isLoading,
  onRecalculateRoute,
  mode,
  onModeChange,
  activeCity = 'mumbai',
}) => {
  const [selectedRouteTab, setSelectedRouteTab] = useState<'safe' | 'normal' | 'alternative'>('safe');

  const cityKey = (activeCity || 'mumbai').toLowerCase();
  const presets = CITY_PRESET_ROUTES[cityKey] || CITY_PRESET_ROUTES.mumbai;

  const getRiskBadgeColor = (risk: string) => {
    switch (risk?.toLowerCase()) {
      case 'low':
      case 'safe':
        return 'text-emerald-400 bg-emerald-950/80 border-emerald-800';
      case 'minor':
        return 'text-yellow-400 bg-yellow-950/80 border-yellow-800';
      case 'moderate':
        return 'text-amber-400 bg-amber-950/80 border-amber-800';
      case 'severe':
      case 'critical':
        return 'text-red-400 bg-red-950/80 border-red-800';
      default:
        return 'text-slate-400 bg-slate-800 border-slate-700';
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-xl backdrop-blur-md flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2">
          <Navigation className="w-4 h-4 text-emerald-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Flood-Aware Navigation
          </h2>
        </div>
        <div className="flex items-center gap-1 bg-slate-950 p-0.5 rounded-lg border border-slate-800">
          <button
            onClick={() => onModeChange('car')}
            className={`p-1 rounded ${mode === 'car' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}
            title="Civilian Sedan / Hatchback (Limit 20cm)"
          >
            <Car className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onModeChange('ambulance')}
            className={`p-1 rounded ${mode === 'ambulance' ? 'bg-red-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}
            title="Emergency Medical Ambulance (Priority)"
          >
            <Ambulance className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onModeChange('truck')}
            className={`p-1 rounded ${mode === 'truck' ? 'bg-amber-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}
            title="Heavy Rescue Vehicle (High Clearance)"
          >
            <Truck className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Origin & Destination Display */}
      <div className="grid grid-cols-2 gap-2 text-[11px]">
        <div className="bg-slate-950/70 border border-slate-800/80 p-2 rounded-lg">
          <div className="flex items-center gap-1 text-blue-400 font-semibold mb-0.5">
            <span className="w-3 h-3 rounded-full bg-blue-600 text-white text-[9px] flex items-center justify-center font-bold">A</span>
            <span>Origin Point</span>
          </div>
          <span className="font-mono text-slate-300 text-[10px]">
            {origin[1].toFixed(4)}°N, {origin[0].toFixed(4)}°E
          </span>
        </div>

        <div className="bg-slate-950/70 border border-slate-800/80 p-2 rounded-lg">
          <div className="flex items-center gap-1 text-red-400 font-semibold mb-0.5">
            <span className="w-3 h-3 rounded-full bg-red-600 text-white text-[9px] flex items-center justify-center font-bold">B</span>
            <span>Destination Point</span>
          </div>
          <span className="font-mono text-slate-300 text-[10px]">
            {destination[1].toFixed(4)}°N, {destination[0].toFixed(4)}°E
          </span>
        </div>
      </div>

      {/* City-Specific Quick Presets */}
      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
          <span>{activeCity.toUpperCase()} Route Presets:</span>
          <span className="text-[9px] text-slate-500">Drag A/B markers on map</span>
        </span>
        <div className="flex flex-col gap-1">
          {presets.map((p, idx) => {
            const isSelected =
              Math.abs(origin[0] - p.origin[0]) < 0.005 &&
              Math.abs(destination[0] - p.destination[0]) < 0.005;

            return (
              <button
                key={idx}
                onClick={() => {
                  onOriginChange(p.origin);
                  onDestinationChange(p.destination);
                }}
                className={`text-left px-2.5 py-1.5 rounded-lg text-xs transition-all border ${
                  isSelected
                    ? 'bg-blue-950/70 border-blue-600/70 text-blue-200'
                    : 'bg-slate-950/50 border-slate-800 hover:border-slate-700 text-slate-300'
                }`}
              >
                <div className="flex items-center justify-between font-semibold">
                  <span className="truncate">{p.name}</span>
                  {isSelected && <Check className="w-3.5 h-3.5 text-blue-400 shrink-0 ml-1" />}
                </div>
                <div className="text-[10px] text-slate-400 truncate mt-0.5">{p.desc}</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Recalculate Button */}
      <button
        onClick={onRecalculateRoute}
        disabled={isLoading}
        className="w-full py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white text-xs font-bold flex items-center justify-center gap-1.5 transition-all shadow-md shadow-emerald-950/40"
      >
        <RotateCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
        <span>{isLoading ? 'Routing Network...' : 'Recalculate 3 Routes'}</span>
      </button>

      {/* 3-Route Comparison Cards */}
      {routeResult && (
        <div className="flex flex-col gap-2 mt-1 border-t border-slate-800 pt-2.5">
          {/* Route Option Tabs */}
          <div className="grid grid-cols-3 gap-1 bg-slate-950 p-0.5 rounded-lg border border-slate-800 text-[11px]">
            <button
              onClick={() => setSelectedRouteTab('safe')}
              className={`py-1 rounded-md font-bold transition-all ${
                selectedRouteTab === 'safe'
                  ? 'bg-emerald-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Safe Route
            </button>
            <button
              onClick={() => setSelectedRouteTab('normal')}
              className={`py-1 rounded-md font-bold transition-all ${
                selectedRouteTab === 'normal'
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Fastest
            </button>
            <button
              onClick={() => setSelectedRouteTab('alternative')}
              className={`py-1 rounded-md font-bold transition-all ${
                selectedRouteTab === 'alternative'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Alternative
            </button>
          </div>

          {/* Selected Route Details Card */}
          {(() => {
            const currentRoute: RouteOption | undefined =
              selectedRouteTab === 'safe'
                ? routeResult.safe_route
                : selectedRouteTab === 'normal'
                ? routeResult.normal_route
                : routeResult.alternative_route || routeResult.safe_route;

            if (!currentRoute) return null;

            return (
              <div className="bg-slate-950/80 border border-slate-800 p-2.5 rounded-xl flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-bold text-white capitalize">
                      {selectedRouteTab === 'safe' ? 'Flood-Safe Corridor' : selectedRouteTab === 'normal' ? 'Fastest Direct Path' : 'Balanced Alternative'}
                    </span>
                  </div>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase font-bold ${getRiskBadgeColor(currentRoute.flood_risk)}`}>
                    {currentRoute.flood_risk} Risk
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-slate-900/80 p-2 rounded-lg border border-slate-800">
                    <span className="text-[10px] text-slate-400 block">Distance & Time:</span>
                    <span className="font-bold font-mono text-white text-sm">
                      {currentRoute.distance_km} km
                    </span>
                    <span className="text-slate-400 font-mono text-[11px] ml-1.5">
                      ({currentRoute.estimated_time_minutes} min)
                    </span>
                  </div>

                  <div className="bg-slate-900/80 p-2 rounded-lg border border-slate-800">
                    <span className="text-[10px] text-slate-400 block">Max Flood Depth:</span>
                    <span className={`font-bold font-mono text-sm ${currentRoute.max_water_depth_cm > 20 ? 'text-red-400' : 'text-emerald-400'}`}>
                      {currentRoute.max_water_depth_cm} cm
                    </span>
                    <span className="text-slate-400 text-[10px] block mt-0.5">
                      {currentRoute.flooded_segments_count} flooded segments ({currentRoute.exposed_percentage || 0}%)
                    </span>
                  </div>
                </div>

                {/* Route Reasoning / Summary */}
                <div className="text-[11px] text-slate-300 bg-slate-900/50 p-2 rounded-lg border border-slate-800/80">
                  <span className="text-amber-400 font-semibold mr-1">Navigation Assessment:</span>
                  {routeResult.summary}
                </div>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
};
