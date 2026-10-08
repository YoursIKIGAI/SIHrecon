import React from 'react';
import { GitFork, AlertCircle, CheckCircle2, ArrowDownCircle, Layers } from 'lucide-react';
import { DrainNodeStatus } from '../types';

interface DrainagePanelProps {
  overflowNodes: DrainNodeStatus[];
  currentMinute: number;
}

export const DrainagePanel: React.FC<DrainagePanelProps> = ({
  overflowNodes,
  currentMinute,
}) => {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl backdrop-blur-md flex flex-col gap-3">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
        <div className="flex items-center gap-2">
          <GitFork className="w-4 h-4 text-cyan-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Subsurface Drainage Network Status
          </h2>
        </div>
        <span
          className={`text-[11px] font-mono px-2 py-0.5 rounded font-bold ${
            overflowNodes.length > 0
              ? 'bg-red-950/80 text-red-400 border border-red-800/60'
              : 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60'
          }`}
        >
          {overflowNodes.length > 0 ? `${overflowNodes.length} SURCHARGED` : 'HYDRAULICALLY NORMAL'}
        </span>
      </div>

      <p className="text-[11px] text-slate-400 leading-relaxed">
        NetworkX directed graph routes runoff from curb catch basins downhill to trunk culverts. 
        When incoming discharge exceeds pipe conveyance capacity, storage chambers fill up and excess 
        water surcharges back onto low-elevation road surfaces.
      </p>

      {/* Overflowing Node List */}
      <div className="flex flex-col gap-1.5 max-h-48 overflow-y-auto pr-1">
        {overflowNodes.length === 0 ? (
          <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg flex items-center gap-2 text-xs text-slate-400">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>All drainage pipes and collector sumps operating within hydraulic capacity.</span>
          </div>
        ) : (
          overflowNodes.map((node) => (
            <div
              key={node.node_id}
              className="p-2.5 bg-red-950/40 border border-red-800/50 rounded-lg flex flex-col gap-1 text-xs"
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-red-200">{node.street_location}</span>
                <span className="font-mono text-[10px] text-red-400 font-bold bg-red-950 px-1.5 py-0.5 rounded border border-red-800">
                  +{node.overflow_rate_m3_s} m³/s OVERFLOW
                </span>
              </div>
              <div className="flex items-center justify-between text-[10px] text-slate-400">
                <span>Chamber: {node.name} ({node.type})</span>
                <span>Elev: {node.elevation_m}m</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
