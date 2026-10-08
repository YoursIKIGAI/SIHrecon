import React from 'react';
import { Layers, Eye, EyeOff } from 'lucide-react';

interface LegendProps {
  showFloodLayer: boolean;
  onToggleFloodLayer: () => void;
  showDrainageLayer: boolean;
  onToggleDrainageLayer: () => void;
  showRoadsLayer: boolean;
  onToggleRoadsLayer: () => void;
  showRoutesLayer: boolean;
  onToggleRoutesLayer: () => void;
}

export const Legend: React.FC<LegendProps> = ({
  showFloodLayer,
  onToggleFloodLayer,
  showDrainageLayer,
  onToggleDrainageLayer,
  showRoadsLayer,
  onToggleRoadsLayer,
  showRoutesLayer,
  onToggleRoutesLayer,
}) => {
  const depthCategories = [
    { label: 'Safe (0–5 cm)', color: '#10b981', textColor: 'text-emerald-400' },
    { label: 'Minor (5–15 cm)', color: '#84cc16', textColor: 'text-lime-400' },
    { label: 'Moderate (15–30 cm)', color: '#f59e0b', textColor: 'text-amber-400' },
    { label: 'Severe (30–50 cm)', color: '#ef4444', textColor: 'text-red-400' },
    { label: 'Critical (>50 cm)', color: '#d946ef', textColor: 'text-fuchsia-400' },
  ];

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3 shadow-xl backdrop-blur-md flex flex-col gap-2.5 max-w-[220px]">
      <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-slate-300 border-b border-slate-800 pb-1.5">
        <span className="flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5 text-blue-400" />
          Map Legend & Layers
        </span>
      </div>

      {/* Flood Depth Swatches */}
      <div className="flex flex-col gap-1">
        <span className="text-[10px] uppercase font-bold text-slate-400">Flood Inundation Depth</span>
        {depthCategories.map((c) => (
          <div key={c.label} className="flex items-center gap-2 text-[11px]">
            <div
              className="w-3.5 h-3.5 rounded-sm border border-white/20 shrink-0"
              style={{ backgroundColor: c.color }}
            />
            <span className={`${c.textColor} font-medium`}>{c.label}</span>
          </div>
        ))}
      </div>

      {/* Drainage & Routes Symbols */}
      <div className="flex flex-col gap-1 pt-1.5 border-t border-slate-800/80">
        <span className="text-[10px] uppercase font-bold text-slate-400">Symbols</span>
        <div className="flex items-center gap-2 text-[11px] text-slate-300">
          <div className="w-3.5 h-1 bg-cyan-400 rounded shrink-0" />
          <span>Drainage Pipe Flow</span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-slate-300">
          <div className="w-3 h-3 rounded-full border-2 border-red-500 bg-red-950 shrink-0 animate-ping" />
          <span className="text-red-300">Overflowing Manhole</span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-slate-300">
          <div className="w-3.5 h-1 bg-emerald-400 rounded shrink-0" />
          <span className="text-emerald-400 font-semibold">Flood-Safe Route</span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-slate-300">
          <div className="w-3.5 h-1 border-t-2 border-dashed border-red-400 shrink-0" />
          <span className="text-red-400">Direct Route (Flooded)</span>
        </div>
      </div>

      {/* Layer Visibility Toggles */}
      <div className="flex flex-col gap-1 pt-1.5 border-t border-slate-800/80">
        <span className="text-[10px] uppercase font-bold text-slate-400">Layer Toggles</span>
        
        <button
          onClick={onToggleFloodLayer}
          className="flex items-center justify-between text-[11px] px-1.5 py-1 rounded hover:bg-slate-800 text-slate-300"
        >
          <span>Flood Zones</span>
          {showFloodLayer ? <Eye className="w-3 h-3 text-blue-400" /> : <EyeOff className="w-3 h-3 text-slate-500" />}
        </button>

        <button
          onClick={onToggleDrainageLayer}
          className="flex items-center justify-between text-[11px] px-1.5 py-1 rounded hover:bg-slate-800 text-slate-300"
        >
          <span>Drainage Network</span>
          {showDrainageLayer ? <Eye className="w-3 h-3 text-cyan-400" /> : <EyeOff className="w-3 h-3 text-slate-500" />}
        </button>

        <button
          onClick={onToggleRoadsLayer}
          className="flex items-center justify-between text-[11px] px-1.5 py-1 rounded hover:bg-slate-800 text-slate-300"
        >
          <span>Road Network</span>
          {showRoadsLayer ? <Eye className="w-3 h-3 text-blue-400" /> : <EyeOff className="w-3 h-3 text-slate-500" />}
        </button>

        <button
          onClick={onToggleRoutesLayer}
          className="flex items-center justify-between text-[11px] px-1.5 py-1 rounded hover:bg-slate-800 text-slate-300"
        >
          <span>Routing Comparison</span>
          {showRoutesLayer ? <Eye className="w-3 h-3 text-emerald-400" /> : <EyeOff className="w-3 h-3 text-slate-500" />}
        </button>
      </div>
    </div>
  );
};
