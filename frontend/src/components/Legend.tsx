import React, { useState } from 'react';
import { Layers, Eye, EyeOff, Download, FileSpreadsheet, MapPin, Radio, Activity } from 'lucide-react';
import { apiClient } from '../api/client';

interface LegendProps {
  showFloodLayer: boolean;
  onToggleFloodLayer: () => void;
  showDrainageLayer: boolean;
  onToggleDrainageLayer: () => void;
  showRoadsLayer: boolean;
  onToggleRoadsLayer: () => void;
  showRoutesLayer: boolean;
  onToggleRoutesLayer: () => void;
  showRadarOverlay?: boolean;
  onToggleRadarOverlay?: () => void;
  currentMinute?: number;
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
  showRadarOverlay = true,
  onToggleRadarOverlay,
  currentMinute = 60,
}) => {
  const [showExportMenu, setShowExportMenu] = useState<boolean>(false);

  const depthCategories = [
    { label: 'Safe (0–5 cm)', color: '#10b981', textColor: 'text-emerald-400' },
    { label: 'Minor (5–15 cm)', color: '#84cc16', textColor: 'text-lime-400' },
    { label: 'Moderate (15–30 cm)', color: '#f59e0b', textColor: 'text-amber-400' },
    { label: 'Severe (30–50 cm)', color: '#ef4444', textColor: 'text-red-400' },
    { label: 'Critical (>50 cm)', color: '#d946ef', textColor: 'text-fuchsia-400' },
  ];

  const handleExportGeoTIFF = () => {
    const url = apiClient.getExportGeoTIFFUrl(currentMinute);
    const a = document.createElement('a');
    a.href = url;
    a.download = `flood_depth_t${currentMinute}min.tif`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setShowExportMenu(false);
  };

  const handleExportGeoJSON = () => {
    const url = apiClient.getExportGeoJSONUrl(currentMinute);
    const a = document.createElement('a');
    a.href = url;
    a.download = `flood_map_t${currentMinute}min.geojson`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setShowExportMenu(false);
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Flood Depth Swatches */}
      <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3 flex flex-col gap-2">
        <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
          Flood Inundation Depth Scale
        </span>
        <div className="flex flex-col gap-1.5">
          {depthCategories.map((c) => (
            <div key={c.label} className="flex items-center justify-between text-[11px]">
              <div className="flex items-center gap-2">
                <div
                  className="w-3.5 h-3.5 rounded-sm border border-white/20 shrink-0"
                  style={{ backgroundColor: c.color }}
                />
                <span className={`${c.textColor} font-medium`}>{c.label}</span>
              </div>
              <span className="text-[9px] text-slate-500 font-mono">
                {c.color}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Layer Toggles & Weather Radar Toggle */}
      <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3 flex flex-col gap-2">
        <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
          Map Layer Visibility
        </span>

        {onToggleRadarOverlay && (
          <button
            onClick={onToggleRadarOverlay}
            className="flex items-center justify-between text-xs px-2 py-1.5 rounded-lg hover:bg-slate-800/80 text-slate-200 transition-colors"
          >
            <span className="flex items-center gap-2">
              <Radio className="w-3.5 h-3.5 text-red-400 animate-pulse" />
              <span>Doppler Rain Echo</span>
            </span>
            {showRadarOverlay ? (
              <Eye className="w-3.5 h-3.5 text-red-400" />
            ) : (
              <EyeOff className="w-3.5 h-3.5 text-slate-600" />
            )}
          </button>
        )}

        <button
          onClick={onToggleFloodLayer}
          className="flex items-center justify-between text-xs px-2 py-1.5 rounded-lg hover:bg-slate-800/80 text-slate-200 transition-colors"
        >
          <span className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
            <span>Flood Inundation Cells</span>
          </span>
          {showFloodLayer ? (
            <Eye className="w-3.5 h-3.5 text-blue-400" />
          ) : (
            <EyeOff className="w-3.5 h-3.5 text-slate-600" />
          )}
        </button>

        <button
          onClick={onToggleDrainageLayer}
          className="flex items-center justify-between text-xs px-2 py-1.5 rounded-lg hover:bg-slate-800/80 text-slate-200 transition-colors"
        >
          <span className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
            <span>Drainage Network Pipes</span>
          </span>
          {showDrainageLayer ? (
            <Eye className="w-3.5 h-3.5 text-cyan-400" />
          ) : (
            <EyeOff className="w-3.5 h-3.5 text-slate-600" />
          )}
        </button>

        <button
          onClick={onToggleRoadsLayer}
          className="flex items-center justify-between text-xs px-2 py-1.5 rounded-lg hover:bg-slate-800/80 text-slate-200 transition-colors"
        >
          <span className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-400" />
            <span>Roadway Risk Network</span>
          </span>
          {showRoadsLayer ? (
            <Eye className="w-3.5 h-3.5 text-indigo-400" />
          ) : (
            <EyeOff className="w-3.5 h-3.5 text-slate-600" />
          )}
        </button>

        <button
          onClick={onToggleRoutesLayer}
          className="flex items-center justify-between text-xs px-2 py-1.5 rounded-lg hover:bg-slate-800/80 text-slate-200 transition-colors"
        >
          <span className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
            <span>Routing Comparison</span>
          </span>
          {showRoutesLayer ? (
            <Eye className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <EyeOff className="w-3.5 h-3.5 text-slate-600" />
          )}
        </button>
      </div>

      {/* Map Symbols Guide */}
      <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3 flex flex-col gap-2">
        <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
          Symbol Guide
        </span>
        <div className="flex flex-col gap-1.5 text-[11px] text-slate-300">
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 border-t-2 border-dashed border-cyan-400 shrink-0" />
            <span className="text-cyan-300">Storm Cell Movement Track</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3.5 h-1 bg-cyan-400 rounded shrink-0" />
            <span>Subsurface Drainage Pipe</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full border-2 border-red-500 bg-red-950 shrink-0 animate-ping" />
            <span className="text-red-300">Surcharging Manhole Inlet</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3.5 h-1 bg-emerald-400 rounded shrink-0" />
            <span className="text-emerald-400 font-semibold">Flood-Safe Route</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3.5 h-1 border-t-2 border-dashed border-red-400 shrink-0" />
            <span className="text-red-400">Direct Route (Impassable)</span>
          </div>
        </div>
      </div>

      {/* GIS Export Section */}
      <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
            GIS Data Export
          </span>
          <span className="text-[10px] text-cyan-400 font-mono">T+{currentMinute}m</span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={handleExportGeoTIFF}
            className="flex items-center justify-center gap-1.5 px-2.5 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg text-xs font-semibold text-slate-200 transition-colors"
            title="Download GeoTIFF elevation/flood depth raster"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
            <span>GeoTIFF (.tif)</span>
          </button>

          <button
            onClick={handleExportGeoJSON}
            className="flex items-center justify-center gap-1.5 px-2.5 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg text-xs font-semibold text-slate-200 transition-colors"
            title="Download vector polygons & flooded roads as GeoJSON"
          >
            <MapPin className="w-3.5 h-3.5 text-blue-400" />
            <span>GeoJSON</span>
          </button>
        </div>
      </div>
    </div>
  );
};
