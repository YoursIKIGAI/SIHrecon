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
  SlidersHorizontal,
  ShieldAlert,
  History,
  TestTube2,
  Sparkles
} from 'lucide-react';
import { ScenarioInfo, EngineMode, SimulationMode, HistoricalEventInfo } from '../types';

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
  // Upgraded Mode & Alert Props
  simulationMode?: SimulationMode;
  onSelectSimulationMode?: (mode: SimulationMode) => void;
  historicalEvents?: HistoricalEventInfo[];
  selectedHistoricalEvent?: string;
  onSelectHistoricalEvent?: (eventId: string) => void;
  activeAlertsCount?: number;
  onOpenAlertsModal?: () => void;
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
  simulationMode = 'live',
  onSelectSimulationMode,
  historicalEvents = [],
  selectedHistoricalEvent,
  onSelectHistoricalEvent,
  activeAlertsCount = 0,
  onOpenAlertsModal,
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
        {/* Left: Brand, City Selector & Mode Selector */}
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

            {/* Simulation Mode Toggle (Live / Historical / Demo) */}
            <div className="hidden md:flex items-center bg-slate-900/90 border border-slate-800 p-0.5 rounded-lg text-[11px] font-mono shadow-inner">
              <button
                onClick={() => onSelectSimulationMode?.('live')}
                className={`px-2 py-0.5 rounded-md font-bold transition-all flex items-center gap-1 ${
                  simulationMode === 'live'
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Live Hydrodynamic Nowcasting Mode"
              >
                <span className={`w-1.5 h-1.5 rounded-full ${simulationMode === 'live' ? 'bg-white' : 'bg-emerald-500'}`} />
                <span>Live</span>
              </button>

              <button
                onClick={() => onSelectSimulationMode?.('historical')}
                className={`px-2 py-0.5 rounded-md font-bold transition-all flex items-center gap-1 ${
                  simulationMode === 'historical'
                    ? 'bg-amber-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Historical Event Replay & Ground-Truth Validation"
              >
                <History className="w-3 h-3" />
                <span>Historical</span>
              </button>

              <button
                onClick={() => onSelectSimulationMode?.('demo')}
                className={`px-2 py-0.5 rounded-md font-bold transition-all flex items-center gap-1 ${
                  simulationMode === 'demo'
                    ? 'bg-purple-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Demonstration Stress-Test Scenario"
              >
                <TestTube2 className="w-3 h-3" />
                <span>Demo</span>
              </button>
            </div>
          </div>
        </div>

        {/* Center: Engine Mode Switcher & Doppler dBZ */}
        <div className="hidden lg:flex items-center gap-2.5 shrink-0">
          {/* Mode Toggle: Physics vs AI Surrogate */}
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

          {/* Radar Reflectivity / Doppler */}
          <div className="hidden xl:flex bg-slate-900/90 border border-slate-800 px-2.5 py-1 rounded-lg items-center gap-1.5 text-xs font-mono">
            <Radio className="w-3 h-3 text-red-400 animate-pulse" />
            <span className="text-slate-400 text-[10px]">Radar:</span>
            <span className={`font-bold text-[11px] ${radarReflectivityDbz >= 50 ? 'text-red-400' : 'text-amber-400'}`}>
              {radarReflectivityDbz} dBZ
            </span>
          </div>
        </div>

        {/* Right Desktop Controls */}
        <div className="hidden lg:flex items-center gap-2 shrink-0">
          {/* Historical Event Dropdown (When in Historical Mode) OR Scenario Selector (When in Live/Demo) */}
          {simulationMode === 'historical' && historicalEvents.length > 0 ? (
            <div className="flex items-center bg-amber-950/80 border border-amber-700/80 rounded-lg px-2 py-1 text-xs">
              <History className="w-3.5 h-3.5 text-amber-400 mr-1.5 shrink-0" />
              <select
                value={selectedHistoricalEvent || historicalEvents[0]?.id}
                onChange={(e) => onSelectHistoricalEvent?.(e.target.value)}
                className="bg-transparent text-xs font-bold text-amber-200 focus:outline-none cursor-pointer max-w-[200px] truncate"
              >
                {historicalEvents.map((ev) => (
                  <option key={ev.id} value={ev.id} className="bg-slate-900 text-white">
                    {ev.title} ({ev.event_date})
                  </option>
                ))}
              </select>
            </div>
          ) : (
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
          )}

          {/* Officer Alert Dashboard Trigger Button */}
          {onOpenAlertsModal && (
            <button
              onClick={onOpenAlertsModal}
              className={`px-2.5 py-1 text-xs font-bold rounded-lg border flex items-center gap-1.5 transition-all relative ${
                activeAlertsCount > 0
                  ? 'bg-red-950/80 border-red-600 text-red-200 hover:bg-red-900'
                  : 'bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-800'
              }`}
              title="Open Officer Alert Emergency Dashboard"
            >
              <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
              <span>ALERTS</span>
              {activeAlertsCount > 0 && (
                <span className="w-4 h-4 rounded-full bg-red-600 text-white text-[10px] font-mono flex items-center justify-center font-bold">
                  {activeAlertsCount}
                </span>
              )}
            </button>
          )}

          {/* Run Nowcast / Replay Button */}
          <button
            onClick={onRunSimulation}
            disabled={isLoading}
            className={`px-3 py-1 text-xs font-bold rounded-lg flex items-center gap-1.5 transition-all shadow-md ${
              simulationMode === 'historical'
                ? 'bg-amber-600 hover:bg-amber-500 text-white shadow-amber-900/40'
                : 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-900/40'
            }`}
          >
            <Play className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>{isLoading ? 'Simulating...' : simulationMode === 'historical' ? 'Run Replay' : 'Run Nowcast'}</span>
          </button>

          {/* Scientific Validation Modal Trigger */}
          <button
            onClick={onOpenValidation}
            className="p-1.5 text-slate-400 hover:text-white bg-slate-900 border border-slate-800 rounded-lg hover:bg-slate-800 transition-colors"
            title="Scientific Accuracy Benchmark & Validation"
          >
            <BarChart3 className="w-4 h-4 text-emerald-400" />
          </button>

          {/* Sound Mute Toggle */}
          <button
            onClick={onToggleSound}
            className="p-1.5 text-slate-400 hover:text-white bg-slate-900 border border-slate-800 rounded-lg hover:bg-slate-800 transition-colors"
            title={soundEnabled ? 'Mute Siren Alarm' : 'Enable Siren Alarm'}
          >
            {soundEnabled ? (
              <Volume2 className="w-4 h-4 text-cyan-400" />
            ) : (
              <VolumeX className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Mobile Hamburger Menu Toggle */}
        <div className="flex lg:hidden items-center gap-1.5">
          {onOpenAlertsModal && activeAlertsCount > 0 && (
            <button
              onClick={onOpenAlertsModal}
              className="p-1.5 bg-red-950 border border-red-700 rounded-lg text-red-300 relative"
            >
              <ShieldAlert className="w-4 h-4" />
              <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-red-600 rounded-full text-[9px] text-white flex items-center justify-center font-bold">
                {activeAlertsCount}
              </span>
            </button>
          )}

          <button
            onClick={() => setShowMobileMenu(!showMobileMenu)}
            className="p-1.5 bg-slate-900 border border-slate-800 rounded-lg text-slate-300"
          >
            {showMobileMenu ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </header>

      {/* Mobile Drawer Menu */}
      {showMobileMenu && (
        <div className="lg:hidden bg-slate-950 border-b border-slate-800 px-4 py-3 flex flex-col gap-2.5 z-20 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 uppercase text-[10px] font-bold">Simulation Mode:</span>
            <div className="flex gap-1">
              {(['live', 'historical', 'demo'] as SimulationMode[]).map((m) => (
                <button
                  key={m}
                  onClick={() => {
                    onSelectSimulationMode?.(m);
                    setShowMobileMenu(false);
                  }}
                  className={`px-2 py-1 rounded text-xs font-bold capitalize ${
                    simulationMode === m ? 'bg-blue-600 text-white' : 'bg-slate-900 text-slate-300'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-400 uppercase text-[10px] font-bold">Engine Pipeline:</span>
            <div className="flex gap-1">
              <button
                onClick={() => onToggleEngineMode('physics')}
                className={`px-2 py-1 rounded text-xs font-bold ${engineMode === 'physics' ? 'bg-blue-600 text-white' : 'bg-slate-900 text-slate-300'}`}
              >
                Physics
              </button>
              <button
                onClick={() => onToggleEngineMode('ml_surrogate')}
                className={`px-2 py-1 rounded text-xs font-bold ${engineMode === 'ml_surrogate' ? 'bg-cyan-600 text-white' : 'bg-slate-900 text-slate-300'}`}
              >
                AI Surrogate
              </button>
            </div>
          </div>

          <button
            onClick={() => {
              setShowMobileMenu(false);
              onRunSimulation();
            }}
            className="w-full py-2 bg-blue-600 text-white font-bold rounded-lg mt-1"
          >
            Execute Simulation
          </button>
        </div>
      )}
    </>
  );
};
