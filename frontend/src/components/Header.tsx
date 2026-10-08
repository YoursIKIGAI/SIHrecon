import React from 'react';
import { 
  CloudRain, 
  Activity, 
  ShieldAlert, 
  Play, 
  CheckCircle2, 
  Zap, 
  BarChart3,
  BrainCircuit,
  Radio,
  Volume2,
  VolumeX,
  Layers,
  Cpu
} from 'lucide-react';
import { ScenarioInfo, EngineMode } from '../types';

interface HeaderProps {
  scenarios: Record<string, ScenarioInfo>;
  currentScenario: string;
  onSelectScenario: (key: string) => void;
  onRunSimulation: () => void;
  isLoading: boolean;
  executionTimeMs?: number;
  onOpenValidation: () => void;
  engineMode: EngineMode;
  onToggleEngineMode: (mode: EngineMode) => void;
  onOpenTrainModel: () => void;
  radarReflectivityDbz?: number;
  soundEnabled: boolean;
  onToggleSound: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  scenarios,
  currentScenario,
  onSelectScenario,
  onRunSimulation,
  isLoading,
  executionTimeMs,
  onOpenValidation,
  engineMode,
  onToggleEngineMode,
  onOpenTrainModel,
  radarReflectivityDbz = 52.0,
  soundEnabled,
  onToggleSound,
}) => {
  return (
    <header className="h-16 bg-slate-950/90 border-b border-cyan-500/20 px-4 flex items-center justify-between z-30 backdrop-blur-xl shrink-0 shadow-lg shadow-black/50">
      {/* Brand & Mission Title */}
      <div className="flex items-center gap-3">
        <div className="relative">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center text-white shadow-lg shadow-cyan-500/30">
            <CloudRain className="w-6 h-6 animate-pulse" />
          </div>
          <div className="absolute -bottom-1 -right-1 w-3.5 h-3.5 rounded-full bg-emerald-500 border-2 border-slate-950 flex items-center justify-center">
            <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping" />
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-extrabold text-sm tracking-wider text-white flex items-center gap-2 font-mono">
              METRO FLOOD NOWCAST
              <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                COMMAND CENTER
              </span>
            </h1>
          </div>
          <p className="text-[11px] text-slate-400 flex items-center gap-2">
            <span className="text-cyan-400 font-medium">DEM Surface Hydraulics + Drainage NetworkX</span>
            <span className="text-slate-600">•</span>
            <span className="text-amber-400 font-mono text-[10px] bg-amber-950/70 px-1.5 py-0.2 rounded border border-amber-800/40">
              MUMBAI METRO BASIN
            </span>
          </p>
        </div>
      </div>

      {/* Center Controls: Engine Mode Toggle & Doppler Radar */}
      <div className="hidden lg:flex items-center gap-3">
        {/* Engine Mode Toggle (Physics vs ML Surrogate) */}
        <div className="bg-slate-900/90 p-1 rounded-xl border border-slate-800 flex items-center gap-1 shadow-inner">
          <button
            onClick={() => onToggleEngineMode('physics')}
            className={`px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
              engineMode === 'physics'
                ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-600/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Hydro Physics</span>
          </button>

          <button
            onClick={() => onToggleEngineMode('ml_surrogate')}
            className={`px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
              engineMode === 'ml_surrogate'
                ? 'bg-gradient-to-r from-cyan-600 to-teal-600 text-white shadow-md shadow-cyan-600/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <BrainCircuit className="w-3.5 h-3.5 text-cyan-300" />
            <span>AI / ML Surrogate</span>
          </button>
        </div>

        {/* Doppler Radar dBZ Gauge */}
        <div className="bg-slate-900/90 border border-slate-800 px-3 py-1 rounded-xl flex items-center gap-2 text-xs font-mono">
          <Radio className="w-3.5 h-3.5 text-red-400 animate-pulse" />
          <span className="text-slate-400 text-[11px]">Doppler Radar:</span>
          <span className={`font-bold ${radarReflectivityDbz >= 50 ? 'text-red-400' : 'text-amber-400'}`}>
            {radarReflectivityDbz} dBZ
          </span>
        </div>
      </div>

      {/* Scenario Selectors, AI Train Button, & Run Simulation */}
      <div className="flex items-center gap-2.5">
        {/* Scenario Buttons */}
        <div className="bg-slate-900 p-1 rounded-xl border border-slate-800 flex items-center gap-1">
          <span className="text-xs font-medium text-slate-400 px-2 flex items-center gap-1">
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            Rainfall:
          </span>
          {Object.entries(scenarios).map(([key, sc]) => {
            const isSelected = currentScenario === key;
            return (
              <button
                key={key}
                onClick={() => onSelectScenario(key)}
                className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-all ${
                  isSelected
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-600/40'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                }`}
                title={sc.description}
              >
                {key.toUpperCase()}
              </button>
            );
          })}
        </div>

        {/* Run Prediction Button */}
        <button
          onClick={onRunSimulation}
          disabled={isLoading}
          className={`px-4 py-2 text-xs font-bold rounded-xl flex items-center gap-2 transition-all shadow-lg ${
            isLoading
              ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
              : 'bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white shadow-emerald-600/30 hover:scale-[1.02]'
          }`}
        >
          {isLoading ? (
            <>
              <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Running...</span>
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>RUN PREDICTION</span>
            </>
          )}
        </button>

        {/* Speed Pill */}
        {executionTimeMs !== undefined && (
          <div className="bg-slate-900/80 border border-slate-800 px-2.5 py-1.5 rounded-lg flex items-center gap-1.5 text-xs font-mono text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>{executionTimeMs.toFixed(0)}ms</span>
          </div>
        )}

        {/* Train AI Model Button */}
        <button
          onClick={onOpenTrainModel}
          className="bg-cyan-950/80 hover:bg-cyan-900 border border-cyan-700/60 text-cyan-200 px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all shadow-md shadow-cyan-950/40"
          title="Open AI / Machine Learning Surrogate Model Studio"
        >
          <Cpu className="w-3.5 h-3.5 text-cyan-400" />
          <span>Train Model</span>
        </button>

        {/* Validation Report Trigger */}
        <button
          onClick={onOpenValidation}
          className="bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 px-2.5 py-1.5 rounded-xl text-xs font-medium flex items-center gap-1.5 transition-colors"
          title="Open Hydrodynamic Accuracy & Benchmark Validation Report"
        >
          <BarChart3 className="w-3.5 h-3.5 text-blue-400" />
          <span>Validation</span>
        </button>

        {/* Audio Alert Toggle */}
        <button
          onClick={onToggleSound}
          className={`p-2 rounded-xl border transition-colors ${
            soundEnabled
              ? 'bg-red-950/80 border-red-700 text-red-300'
              : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-slate-300'
          }`}
          title={soundEnabled ? 'Alarm sound ACTIVE' : 'Alarm sound MUTED'}
        >
          {soundEnabled ? <Volume2 className="w-4 h-4 text-red-400" /> : <VolumeX className="w-4 h-4" />}
        </button>
      </div>
    </header>
  );
};
