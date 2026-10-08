import React from 'react';
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
  ArrowRight
} from 'lucide-react';
import { RouteResponse } from '../types';

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
}

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
}) => {
  // Preset landmark routes
  const PRESET_ROUTES = [
    {
      name: 'Downtown → Airport (Milan Chokepoint)',
      origin: [72.870, 19.062] as [number, number],
      destination: [72.868, 19.088] as [number, number],
      desc: 'Crosses lowest underpass depression',
    },
    {
      name: 'Harbor Gate → Medical Center',
      origin: [72.854, 19.065] as [number, number],
      destination: [72.888, 19.076] as [number, number],
      desc: 'Coastal bay to emergency trauma facility',
    },
    {
      name: 'South Port → Tech Park Ridge',
      origin: [72.862, 19.058] as [number, number],
      destination: [72.898, 19.085] as [number, number],
      desc: 'Full city diagonal transit',
    },
  ];

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl backdrop-blur-md flex flex-col gap-3.5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
        <div className="flex items-center gap-2">
          <Navigation className="w-4 h-4 text-emerald-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Flood-Safe Emergency Routing
          </h2>
        </div>
        <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-md border border-slate-800">
          <button
            onClick={() => onModeChange('car')}
            className={`p-1 rounded ${mode === 'car' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'}`}
            title="Civilian Car (Limit 20cm)"
          >
            <Car className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onModeChange('ambulance')}
            className={`p-1 rounded ${mode === 'ambulance' ? 'bg-red-600 text-white' : 'text-slate-400 hover:text-white'}`}
            title="Emergency Ambulance (Priority)"
          >
            <Ambulance className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onModeChange('truck')}
            className={`p-1 rounded ${mode === 'truck' ? 'bg-amber-600 text-white' : 'text-slate-400 hover:text-white'}`}
            title="Heavy Rescue Vehicle (High Clearance)"
          >
            <Truck className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Quick Presets for Demo */}
      <div className="flex flex-col gap-1.5">
        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
          Demo Quick Presets:
        </span>
        <div className="flex flex-col gap-1">
          {PRESET_ROUTES.map((p, idx) => {
            const isSelected =
              Math.abs(origin[0] - p.origin[0]) < 0.001 &&
              Math.abs(destination[0] - p.destination[0]) < 0.001;

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
                <div className="font-medium text-[11px] flex items-center justify-between">
                  <span>{p.name}</span>
                  {isSelected && <Check className="w-3 h-3 text-blue-400" />}
                </div>
                <div className="text-[10px] text-slate-500">{p.desc}</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Origin & Destination Coords Display */}
      <div className="grid grid-cols-2 gap-2 text-[11px]">
        <div className="bg-slate-950/70 border border-slate-800 p-2 rounded-lg flex flex-col gap-0.5">
          <span className="text-[10px] text-emerald-400 font-semibold flex items-center gap-1">
            <MapPin className="w-3 h-3" /> Origin
          </span>
          <span className="font-mono text-slate-300">
            {origin[1].toFixed(3)}°N, {origin[0].toFixed(3)}°E
          </span>
        </div>
        <div className="bg-slate-950/70 border border-slate-800 p-2 rounded-lg flex flex-col gap-0.5">
          <span className="text-[10px] text-red-400 font-semibold flex items-center gap-1">
            <MapPin className="w-3 h-3" /> Destination
          </span>
          <span className="font-mono text-slate-300">
            {destination[1].toFixed(3)}°N, {destination[0].toFixed(3)}°E
          </span>
        </div>
      </div>

      {/* Recalculate Button */}
      <button
        onClick={onRecalculateRoute}
        disabled={isLoading}
        className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-colors border border-slate-700"
      >
        <RotateCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
        <span>RECALCULATE ROUTE</span>
      </button>

      {/* Route Comparison Output */}
      {routeResult && (
        <div className="flex flex-col gap-2.5 pt-1">
          {/* Executive Summary Banner */}
          <div
            className={`p-2.5 rounded-lg text-xs border leading-relaxed ${
              routeResult.is_rerouted
                ? 'bg-emerald-950/50 border-emerald-800 text-emerald-200'
                : 'bg-blue-950/50 border-blue-800 text-blue-200'
            }`}
          >
            <div className="font-semibold flex items-center gap-1.5 mb-1">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>{routeResult.is_rerouted ? 'FLOOD-SAFE REROUTE ACTIVE' : 'DIRECT PATH SAFE'}</span>
            </div>
            <p className="text-[11px] opacity-90">{routeResult.summary}</p>
          </div>

          {/* Dual Comparison Cards */}
          <div className="grid grid-cols-2 gap-2">
            {/* Standard Normal Route */}
            <div
              className={`p-2.5 rounded-lg border flex flex-col justify-between ${
                routeResult.normal_route.max_water_depth_cm > 20
                  ? 'bg-red-950/30 border-red-800/80'
                  : 'bg-slate-950 border-slate-800'
              }`}
            >
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Standard Route
                </span>
                <div className="flex items-baseline gap-1">
                  <span className="text-base font-bold font-mono text-white">
                    {routeResult.normal_route.estimated_time_minutes}
                  </span>
                  <span className="text-[10px] text-slate-400">min</span>
                  <span className="text-[10px] text-slate-500 font-mono ml-auto">
                    {routeResult.normal_route.distance_km} km
                  </span>
                </div>
              </div>

              <div className="mt-2 pt-2 border-t border-slate-800/80 flex flex-col gap-1 text-[11px]">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Peak Water:</span>
                  <span
                    className={`font-mono font-bold ${
                      routeResult.normal_route.max_water_depth_cm > 30
                        ? 'text-red-400'
                        : 'text-amber-400'
                    }`}
                  >
                    {routeResult.normal_route.max_water_depth_cm} cm
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Risk:</span>
                  <span className="text-xs font-semibold text-red-400">
                    {routeResult.normal_route.flood_risk}
                  </span>
                </div>
              </div>
            </div>

            {/* Flood-Safe Alternative Route */}
            <div className="bg-emerald-950/30 border border-emerald-700/80 p-2.5 rounded-lg flex flex-col justify-between">
              <div>
                <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider block mb-1">
                  Flood-Safe Route
                </span>
                <div className="flex items-baseline gap-1">
                  <span className="text-base font-bold font-mono text-emerald-300">
                    {routeResult.safe_route.estimated_time_minutes}
                  </span>
                  <span className="text-[10px] text-emerald-400/80">min</span>
                  <span className="text-[10px] text-slate-400 font-mono ml-auto">
                    {routeResult.safe_route.distance_km} km
                  </span>
                </div>
              </div>

              <div className="mt-2 pt-2 border-t border-emerald-800/40 flex flex-col gap-1 text-[11px]">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Avoided Roads:</span>
                  <span className="font-mono font-bold text-emerald-400">
                    {routeResult.avoided_flooded_roads} flooded
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Risk:</span>
                  <span className="text-xs font-semibold text-emerald-400">
                    {routeResult.safe_route.flood_risk}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Delta Time Badge */}
          {routeResult.is_rerouted && (
            <div className="bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400">Detour Time Trade-off:</span>
              <span className="text-amber-400 font-bold">
                +{Math.abs(routeResult.time_difference_minutes)} min (+{Math.abs(routeResult.distance_difference_km)} km)
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
