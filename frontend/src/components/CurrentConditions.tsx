import React from 'react';
import { 
  CloudRain, 
  AlertTriangle, 
  Waves, 
  GitFork, 
  ShieldAlert,
  ArrowUpRight,
  TrendingUp,
  MapPin
} from 'lucide-react';
import { TimestepSummary, FloodedRoadSegment } from '../types';

interface CurrentConditionsProps {
  currentMinute: number;
  timesteps: TimestepSummary[];
  floodedRoads: FloodedRoadSegment[];
}

export const CurrentConditions: React.FC<CurrentConditionsProps> = ({
  currentMinute,
  timesteps,
  floodedRoads,
}) => {
  const current = timesteps.find((t) => t.minutes === currentMinute) || {
    minutes: currentMinute,
    timestamp: '',
    rainfall_mm_hr: 0,
    flooded_roads_count: 0,
    critical_zones_count: 0,
    max_depth_cm: 0,
    mean_depth_cm: 0,
    overflow_nodes_count: 0,
    total_surface_volume_m3: 0,
    total_drainage_volume_m3: 0,
  };

  const criticalRoads = floodedRoads.filter((r) => r.water_depth_cm >= 30.0);

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl backdrop-blur-md flex flex-col gap-4">
      {/* Panel Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Current Flood Nowcast Conditions
          </h2>
        </div>
        <span className="text-[11px] font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
          T+{current.minutes} MIN
        </span>
      </div>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-2 gap-2.5">
        {/* Rainfall Intensity */}
        <div className="bg-slate-950/70 border border-slate-800 p-2.5 rounded-lg flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-[11px]">
            <span>Rainfall Rate</span>
            <CloudRain className="w-3.5 h-3.5 text-blue-400" />
          </div>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="text-xl font-bold font-mono text-white">
              {current.rainfall_mm_hr}
            </span>
            <span className="text-[10px] text-slate-400">mm/hr</span>
          </div>
          <div className="mt-1 w-full bg-slate-800 h-1 rounded-full overflow-hidden">
            <div
              className="bg-blue-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, (current.rainfall_mm_hr / 150) * 100)}%` }}
            />
          </div>
        </div>

        {/* Max Water Depth */}
        <div className="bg-slate-950/70 border border-slate-800 p-2.5 rounded-lg flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-[11px]">
            <span>Max Flood Depth</span>
            <Waves className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="mt-1 flex items-baseline gap-1">
            <span
              className={`text-xl font-bold font-mono ${
                current.max_depth_cm > 40
                  ? 'text-red-400'
                  : current.max_depth_cm > 20
                  ? 'text-amber-400'
                  : 'text-emerald-400'
              }`}
            >
              {current.max_depth_cm}
            </span>
            <span className="text-[10px] text-slate-400">cm</span>
          </div>
          <span className="text-[10px] text-slate-500">
            Avg: {current.mean_depth_cm} cm across basin
          </span>
        </div>

        {/* Flooded Roads */}
        <div className="bg-slate-950/70 border border-slate-800 p-2.5 rounded-lg flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-[11px]">
            <span>Flooded Roads</span>
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="text-xl font-bold font-mono text-amber-400">
              {current.flooded_roads_count}
            </span>
            <span className="text-[10px] text-slate-400">segments</span>
          </div>
          <span className="text-[10px] text-slate-500">
            {floodedRoads.filter((r) => r.is_blocked).length} impassable (&gt;40cm)
          </span>
        </div>

        {/* Drain Overflows */}
        <div className="bg-slate-950/70 border border-slate-800 p-2.5 rounded-lg flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-[11px]">
            <span>Drain Overflows</span>
            <GitFork className="w-3.5 h-3.5 text-red-400" />
          </div>
          <div className="mt-1 flex items-baseline gap-1">
            <span
              className={`text-xl font-bold font-mono ${
                current.overflow_nodes_count > 0 ? 'text-red-400' : 'text-slate-300'
              }`}
            >
              {current.overflow_nodes_count}
            </span>
            <span className="text-[10px] text-slate-400">manholes</span>
          </div>
          <span className="text-[10px] text-slate-500">Capacity exceeded</span>
        </div>
      </div>

      {/* Critical Chokepoint Alerts */}
      {criticalRoads.length > 0 && (
        <div className="bg-red-950/40 border border-red-800/60 rounded-lg p-2.5 flex flex-col gap-1.5">
          <div className="flex items-center gap-1.5 text-red-400 text-xs font-semibold">
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Severe Road Inundation Alerts:</span>
          </div>
          <div className="flex flex-col gap-1 max-h-24 overflow-y-auto pr-1">
            {criticalRoads.slice(0, 4).map((r) => (
              <div
                key={r.road_id}
                className="flex items-center justify-between text-[11px] bg-red-900/30 px-2 py-1 rounded text-red-200"
              >
                <span className="truncate max-w-[160px]">{r.name}</span>
                <span className="font-mono font-bold text-red-300">{r.water_depth_cm} cm</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Forecast Trend Sparkline */}
      <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-2.5 flex flex-col gap-2">
        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <span className="flex items-center gap-1">
            <TrendingUp className="w-3 h-3 text-blue-400" />
            3-Hour Road Inundation Forecast Trend
          </span>
        </div>
        <div className="grid grid-cols-6 gap-1 items-end h-16 pt-2 pb-1 border-b border-slate-800/60">
          {timesteps.map((ts) => {
            const isCurrent = ts.minutes === currentMinute;
            const maxVal = Math.max(1, ...timesteps.map((t) => t.flooded_roads_count));
            const heightPct = Math.max(15, (ts.flooded_roads_count / maxVal) * 100);

            return (
              <div key={ts.minutes} className="flex flex-col items-center gap-1 h-full justify-end">
                <span className="text-[9px] font-mono text-slate-400">
                  {ts.flooded_roads_count}
                </span>
                <div
                  className={`w-full rounded-t transition-all ${
                    isCurrent
                      ? 'bg-amber-400 shadow-md shadow-amber-400/50'
                      : ts.flooded_roads_count > 15
                      ? 'bg-red-500/80'
                      : 'bg-blue-600/70'
                  }`}
                  style={{ height: `${heightPct}%` }}
                />
                <span className="text-[9px] font-mono text-slate-500">
                  {ts.minutes}m
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
