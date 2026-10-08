import React, { useState } from 'react';
import { 
  CloudRain, 
  Activity, 
  Play, 
  Zap, 
  BarChart3, 
  BrainCircuit, 
  Radio, 
  Volume2, 
  VolumeX, 
  Cpu, 
  Building2, 
  RefreshCw, 
  Key, 
  ChevronDown,
  Menu,
  X,
  SlidersHorizontal
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
  activeCity?: string;
  onSwitchCity?: (cityKey: string) => void;
  cities?: Record<string, any>;
  onSelectRadarFeed?: (source: string, apiKey?: string, event?: string) => void;
  isWsConnected?: boolean;
  isAutoUpdating?: boolean;
  onToggleAutoUpdate?: () => void;
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
  activeCity = 'mumbai',
  onSwitchCity,
  cities = {},
  onSelectRadarFeed,
  isWsConnected = false,
  isAutoUpdating = false,
  onToggleAutoUpdate,
}) => {
  const [showRadarMenu, setShowRadarMenu] = useState<boolean>(false);
  const [showMobileMenu, setShowMobileMenu] = useState<boolean>(false);
  const [owmApiKey, setOwmApiKey] = useState<string>('');
  const [showApiKeyModal, setShowApiKeyModal] = useState<boolean>(false);

  const cityOptions = [
    { key: 'mumbai', label: 'Mumbai MMR' },
    { key: 'delhi', label: 'Delhi NCR' },
    { key: 'chennai', label: 'Chennai Basin' },
  ];

  const handleSelectLiveOwm = () => {
    setShowRadarMenu(false);
    setShowMobileMenu(false);
    if (!owmApiKey) {
      setShowApiKeyModal(true);
    } else {
      onSelectRadarFeed?.('openweathermap', owmApiKey);
    }
  };

  const handleApplyApiKey = () => {
    setShowApiKeyModal(false);
    if (owmApiKey.trim() && onSelectRadarFeed) {
      onSelectRadarFeed('openweathermap', owmApiKey.trim());
    }
  };

  return (
    <>
      <header className="h-14 bg-slate-950/95 border-b border-cyan-500/20 px-3 sm:px-4 flex items-center justify-between z-30 backdrop-blur-xl shrink-0 shadow-lg shadow-black/60 select-none">
        {/* Left: Brand & City Selector */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          <div className="relative">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center text-white shadow-md shadow-cyan-500/30">
              <CloudRain className="w-4.5 h-4.5 animate-pulse" />
            </div>
            <div
              className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-slate-950 ${
                isWsConnected ? 'bg-emerald-400' : 'bg-slate-500'
              }`}
              title={isWsConnected ? 'WebSocket Live Feed Connected' : 'WebSocket Disconnected'}
            />
          </div>

          <div className="flex items-center gap-1.5 sm:gap-2">
            <span className="font-extrabold text-xs tracking-wider text-white font-mono flex items-center gap-1">
              <span className="hidden xl:inline">METRO FLOOD NOWCAST</span>
              <span className="xl:hidden">NOWCAST</span>
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 font-sans font-semibold hidden 2xl:inline">
                COMMAND
              </span>
            </span>

            {/* City Dropdown */}
            <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg px-2 py-0.5 sm:py-1 text-xs">
              <Building2 className="w-3 h-3 text-amber-400 mr-1 sm:mr-1.5 shrink-0" />
              <select
                value={activeCity}
                onChange={(e) => onSwitchCity?.(e.target.value)}
                className="bg-transparent text-[11px] font-mono text-amber-300 font-bold focus:outline-none cursor-pointer"
              >
                {cityOptions.map((c) => (
                  <option key={c.key} value={c.key} className="bg-slate-900 text-white">
                    {c.label}
                  </option>
                ))}
              </select>
            </div>

            {isWsConnected && (
              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-700/60 items-center gap-1 animate-pulse hidden sm:flex">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                LIVE
              </span>
            )}
          </div>
        </div>

        {/* Center: Engine Mode Switcher & Doppler dBZ (Desktop & Tablet) */}
        <div className="hidden lg:flex items-center gap-2.5 shrink-0">
          {/* Mode Toggle */}
          <div className="bg-slate-900/90 p-0.5 rounded-lg border border-slate-800 flex items-center gap-0.5 shadow-inner">
            <button
              onClick={() => onToggleEngineMode('physics')}
              className={`px-2.5 py-1 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-all ${
                engineMode === 'physics'
                  ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Activity className="w-3 h-3" />
              <span>Hydro Physics</span>
            </button>

            <button
              onClick={() => onToggleEngineMode('ml_surrogate')}
              className={`px-2.5 py-1 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-all ${
                engineMode === 'ml_surrogate'
                  ? 'bg-gradient-to-r from-cyan-600 to-teal-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <BrainCircuit className="w-3 h-3 text-cyan-300" />
              <span>AI Surrogate</span>
            </button>
          </div>

          {/* Doppler dBZ */}
          <div className="hidden xl:flex bg-slate-900/90 border border-slate-800 px-2.5 py-1 rounded-lg items-center gap-1.5 text-xs font-mono">
            <Radio className="w-3 h-3 text-red-400 animate-pulse" />
            <span className="text-slate-400 text-[10px]">Radar:</span>
            <span className={`font-bold text-[11px] ${radarReflectivityDbz >= 50 ? 'text-red-400' : 'text-amber-400'}`}>
              {radarReflectivityDbz} dBZ
            </span>
          </div>
        </div>

        {/* Right Desktop Controls (>= lg: Desktop and Laptops) */}
        <div className="hidden lg:flex items-center gap-2 shrink-0">
          {/* Compact Scenario Selector Dropdown */}
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg px-2 py-1 text-xs">
            <Zap className="w-3.5 h-3.5 text-amber-400 mr-1.5 shrink-0" />
            <select
              value={currentScenario}
              onChange={(e) => onSelectScenario(e.target.value)}
              className="bg-transparent text-xs font-bold text-amber-300 focus:outline-none cursor-pointer uppercase"
              title="Select Rainfall Regime"
            >
              {Object.keys(scenarios).map((k) => (
                <option key={k} value={k} className="bg-slate-900 text-white">
                  {k.toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          {/* Radar Feeds Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowRadarMenu(!showRadarMenu)}
              className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-cyan-950/70 border border-cyan-800 text-cyan-300 hover:bg-cyan-900 transition-colors flex items-center gap-1.5"
              title="Select Doppler radar or historical event"
            >
              <Radio className="w-3 h-3 text-cyan-400" />
              <span>RADAR</span>
              <ChevronDown className="w-3 h-3" />
            </button>

            {showRadarMenu && (
              <div className="absolute right-0 top-full mt-2 w-56 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-1.5 z-40 animate-in fade-in">
                <div className="px-2 py-1 text-[10px] uppercase font-bold text-slate-400 border-b border-slate-800 mb-1">
                  Radar & Historical Feeds
                </div>
                <button
                  onClick={() => {
                    setShowRadarMenu(false);
                    onSelectRadarFeed?.('imd_historical', undefined, 'mumbai_2005');
                  }}
                  className="w-full text-left px-2.5 py-1.5 rounded-lg hover:bg-slate-800 text-xs text-slate-200 transition-colors flex flex-col"
                >
                  <span className="font-semibold text-cyan-300">Mumbai 2005 Cloudburst</span>
                  <span className="text-[10px] text-slate-400">944mm IMD Benchmark</span>
                </button>
                <button
                  onClick={handleSelectLiveOwm}
                  className="w-full text-left px-2.5 py-1.5 rounded-lg hover:bg-slate-800 text-xs text-slate-200 transition-colors flex flex-col mt-1"
                >
                  <span className="font-semibold text-emerald-300 flex items-center gap-1">
                    <span>OpenWeatherMap Live</span>
                    <Key className="w-3 h-3 text-emerald-400" />
                  </span>
                  <span className="text-[10px] text-slate-400">Live 3h forecast via API Key</span>
                </button>
              </div>
            )}
          </div>

          {/* Auto-Update */}
          {onToggleAutoUpdate && (
            <button
              onClick={onToggleAutoUpdate}
              className={`px-2.5 py-1 text-xs font-bold rounded-lg border flex items-center gap-1.5 transition-all ${
                isAutoUpdating
                  ? 'bg-emerald-950/80 border-emerald-600 text-emerald-300 shadow'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
              }`}
              title={isAutoUpdating ? 'Auto-Update ON' : 'Auto-Update OFF'}
            >
              <RefreshCw className={`w-3 h-3 ${isAutoUpdating ? 'animate-spin text-emerald-400' : ''}`} />
              <span className="text-[11px]">{isAutoUpdating ? 'AUTO' : 'OFF'}</span>
            </button>
          )}

          {/* Run Button */}
          <button
            onClick={onRunSimulation}
            disabled={isLoading}
            className={`px-3 py-1 text-xs font-bold rounded-lg flex items-center gap-1.5 transition-all shadow-md ${
              isLoading
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                : 'bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white shadow-emerald-600/30 hover:scale-[1.02]'
            }`}
          >
            {isLoading ? (
              <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Play className="w-3 h-3 fill-current" />
            )}
            <span>{isLoading ? 'Running...' : 'RUN'}</span>
          </button>

          {executionTimeMs !== undefined && (
            <div className="bg-slate-900/80 border border-slate-800 px-2 py-1 rounded-md text-[11px] font-mono text-emerald-400">
              {executionTimeMs.toFixed(0)}ms
            </div>
          )}

          <div className="w-px h-5 bg-slate-800" />

          {/* Quick tools */}
          <button
            onClick={onOpenTrainModel}
            className="p-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-cyan-700/60 text-cyan-300 rounded-lg transition-colors"
            title="Open AI / ML Surrogate Studio"
          >
            <Cpu className="w-4 h-4" />
          </button>

          <button
            onClick={onOpenValidation}
            className="p-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-blue-700 text-blue-300 rounded-lg transition-colors"
            title="Open Validation Report"
          >
            <BarChart3 className="w-4 h-4" />
          </button>

          <button
            onClick={onToggleSound}
            className={`p-1.5 rounded-lg border transition-colors ${
              soundEnabled
                ? 'bg-red-950/80 border-red-700 text-red-300'
                : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-slate-300'
            }`}
            title={soundEnabled ? 'Alarm Sound ACTIVE' : 'Alarm Sound MUTED'}
          >
            {soundEnabled ? <Volume2 className="w-4 h-4 text-red-400" /> : <VolumeX className="w-4 h-4" />}
          </button>
        </div>

        {/* Compact Right Controls (< lg: Tablets & Mobile) */}
        <div className="flex lg:hidden items-center gap-1.5 shrink-0">
          {/* Scenario Selector Dropdown (Tablet view) */}
          <div className="hidden sm:flex items-center bg-slate-900 border border-slate-800 rounded-lg px-2 py-1 text-xs">
            <Zap className="w-3 h-3 text-amber-400 mr-1.5 shrink-0" />
            <select
              value={currentScenario}
              onChange={(e) => onSelectScenario(e.target.value)}
              className="bg-transparent text-[11px] font-bold text-slate-200 focus:outline-none cursor-pointer"
            >
              {Object.keys(scenarios).map((k) => (
                <option key={k} value={k} className="bg-slate-900 text-white">
                  {k.toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          {/* Primary RUN Button — Always visible and prominent */}
          <button
            onClick={onRunSimulation}
            disabled={isLoading}
            className={`px-3 py-1.5 text-xs font-bold rounded-lg flex items-center gap-1.5 transition-all shadow-md ${
              isLoading
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                : 'bg-gradient-to-r from-emerald-600 to-teal-500 text-white shadow-emerald-600/30'
            }`}
          >
            {isLoading ? (
              <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Play className="w-3 h-3 fill-current" />
            )}
            <span className="hidden xs:inline sm:inline">{isLoading ? '...' : 'RUN'}</span>
          </button>

          {/* Hamburger / Menu Toggle for smaller viewports */}
          <button
            onClick={() => setShowMobileMenu(!showMobileMenu)}
            className="p-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 rounded-lg transition-colors flex items-center justify-center"
            title="Toggle Menu & Simulation Settings"
          >
            {showMobileMenu ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>
      </header>

      {/* Mobile / Tablet Full-Featured Drawer (< lg) */}
      {showMobileMenu && (
        <div className="lg:hidden fixed inset-x-0 top-14 z-40 bg-slate-950/95 border-b border-cyan-500/30 p-4 backdrop-blur-2xl shadow-2xl flex flex-col gap-3.5 animate-in slide-in-from-top-4 duration-200 max-h-[calc(100vh-4rem)] overflow-y-auto">
          {/* Engine Mode Toggle */}
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] uppercase font-bold text-slate-400">Simulation Engine</span>
            <div className="grid grid-cols-2 gap-2 bg-slate-900 p-1 rounded-xl border border-slate-800">
              <button
                onClick={() => {
                  onToggleEngineMode('physics');
                  setShowMobileMenu(false);
                }}
                className={`py-1.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 ${
                  engineMode === 'physics'
                    ? 'bg-blue-600 text-white shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Activity className="w-3.5 h-3.5" />
                <span>Hydro Physics</span>
              </button>

              <button
                onClick={() => {
                  onToggleEngineMode('ml_surrogate');
                  setShowMobileMenu(false);
                }}
                className={`py-1.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 ${
                  engineMode === 'ml_surrogate'
                    ? 'bg-cyan-600 text-white shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <BrainCircuit className="w-3.5 h-3.5" />
                <span>AI Surrogate</span>
              </button>
            </div>
          </div>

          {/* Rainfall Scenarios & Radar */}
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] uppercase font-bold text-slate-400">Rainfall Regime</span>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
              {Object.entries(scenarios).map(([key, sc]) => (
                <button
                  key={key}
                  onClick={() => {
                    onSelectScenario(key);
                    setShowMobileMenu(false);
                  }}
                  className={`py-1.5 px-2 text-xs font-semibold rounded-lg border text-center transition-all ${
                    currentScenario === key
                      ? 'bg-blue-600 border-blue-500 text-white shadow'
                      : 'bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-800'
                  }`}
                >
                  {key.toUpperCase()}
                </button>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-2 mt-1">
              <button
                onClick={() => {
                  setShowMobileMenu(false);
                  onSelectRadarFeed?.('imd_historical', undefined, 'mumbai_2005');
                }}
                className="py-1.5 px-2 bg-cyan-950/60 border border-cyan-800 text-cyan-300 hover:bg-cyan-900 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5"
              >
                <Radio className="w-3.5 h-3.5" />
                <span>Mumbai 2005 Event</span>
              </button>

              <button
                onClick={handleSelectLiveOwm}
                className="py-1.5 px-2 bg-emerald-950/60 border border-emerald-800 text-emerald-300 hover:bg-emerald-900 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5"
              >
                <Key className="w-3.5 h-3.5" />
                <span>Live Weather API</span>
              </button>
            </div>
          </div>

          {/* Tools & Auto Update */}
          <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800/80">
            {onToggleAutoUpdate && (
              <button
                onClick={onToggleAutoUpdate}
                className={`py-2 px-2 rounded-xl border text-xs font-bold flex items-center justify-center gap-1.5 ${
                  isAutoUpdating
                    ? 'bg-emerald-950/80 border-emerald-600 text-emerald-300'
                    : 'bg-slate-900 border-slate-800 text-slate-400'
                }`}
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isAutoUpdating ? 'animate-spin text-emerald-400' : ''}`} />
                <span>{isAutoUpdating ? 'Auto: ON' : 'Auto: OFF'}</span>
              </button>
            )}

            <button
              onClick={() => {
                setShowMobileMenu(false);
                onOpenTrainModel();
              }}
              className="py-2 px-2 bg-slate-900 border border-slate-800 text-cyan-300 hover:bg-slate-800 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5"
            >
              <Cpu className="w-3.5 h-3.5" />
              <span>AI Studio</span>
            </button>

            <button
              onClick={() => {
                setShowMobileMenu(false);
                onOpenValidation();
              }}
              className="py-2 px-2 bg-slate-900 border border-slate-800 text-blue-300 hover:bg-slate-800 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5"
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Validation</span>
            </button>
          </div>
        </div>
      )}

      {/* OpenWeatherMap API Key Modal */}
      {showApiKeyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md p-5 shadow-2xl flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h4 className="font-bold text-sm text-white flex items-center gap-2">
                <Key className="w-4 h-4 text-emerald-400" />
                OpenWeatherMap Live API Integration
              </h4>
              <button
                onClick={() => setShowApiKeyModal(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Enter your free OpenWeatherMap API Key to stream live rainfall forecasts directly into the hydrodynamic nowcaster.
            </p>
            <input
              type="text"
              placeholder="Paste OpenWeatherMap API Key (32-char hex)"
              value={owmApiKey}
              onChange={(e) => setOwmApiKey(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white font-mono placeholder-slate-500 focus:outline-none focus:border-cyan-400"
            />
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowApiKeyModal(false)}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleApplyApiKey}
                className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl shadow transition-colors"
              >
                Connect & Nowcast
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
