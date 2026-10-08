import React, { useState, useEffect, useCallback, useRef } from 'react';
import { apiClient } from './api/client';
import { 
  SimulationResponse, 
  RouteResponse, 
  ValidationMetrics, 
  ScenarioInfo, 
  FloodedRoadSegment, 
  DrainNodeStatus, 
  EngineMode, 
  BasemapType, 
  MLTrainingResponse,
  CityInfo,
} from './types';
import { Header } from './components/Header';
import { TimeSlider } from './components/TimeSlider';
import { CurrentConditions } from './components/CurrentConditions';
import { RoutingPanel } from './components/RoutingPanel';
import { DrainagePanel } from './components/DrainagePanel';
import { ValidationModal } from './components/ValidationModal';
import { ModelTrainingModal } from './components/ModelTrainingModal';
import { Legend } from './components/Legend';
import { MapView } from './map/MapView';
import { 
  Activity, 
  GitFork, 
  Layers, 
  ChevronLeft, 
  ChevronRight, 
  Navigation,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen
} from 'lucide-react';

const CITY_DEFAULTS: Record<string, { center: [number, number]; origin: [number, number]; destination: [number, number] }> = {
  mumbai: {
    center: [72.875, 19.075],
    origin: [72.870, 19.062],
    destination: [72.868, 19.088],
  },
  delhi: {
    center: [77.200, 28.650],
    origin: [77.190, 28.610],
    destination: [77.240, 28.670],
  },
  chennai: {
    center: [80.250, 13.060],
    origin: [80.230, 13.030],
    destination: [80.270, 13.090],
  },
};

export const App: React.FC = () => {
  // Scenario, Simulation, and Engine state
  const [scenarios, setScenarios] = useState<Record<string, ScenarioInfo>>({});
  const [currentScenario, setCurrentScenario] = useState<string>('extreme');
  const [simulationData, setSimulationData] = useState<SimulationResponse | null>(null);
  const [isLoadingSimulation, setIsLoadingSimulation] = useState<boolean>(false);
  const [currentMinute, setCurrentMinute] = useState<number>(90);
  const [engineMode, setEngineMode] = useState<EngineMode>('physics');

  // Multi-city state
  const [activeCity, setActiveCity] = useState<string>('mumbai');
  const [cities, setCities] = useState<Record<string, CityInfo>>({});
  const [cityCenter, setCityCenter] = useState<[number, number]>([72.875, 19.075]);

  // WebSocket live status & auto-update state
  const [isWsConnected, setIsWsConnected] = useState<boolean>(false);
  const [isAutoUpdating, setIsAutoUpdating] = useState<boolean>(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Basemap & Radar state
  const [basemap, setBasemap] = useState<BasemapType>('dark');
  const [showRadarOverlay, setShowRadarOverlay] = useState<boolean>(true);
  const [soundEnabled, setSoundEnabled] = useState<boolean>(false);

  // GeoJSON & Map layers
  const [floodGeoJson, setFloodGeoJson] = useState<any>(null);
  const [drainageGeoJson, setDrainageGeoJson] = useState<any>(null);

  // Routing state
  const [origin, setOrigin] = useState<[number, number]>([72.870, 19.062]); // Downtown Central
  const [destination, setDestination] = useState<[number, number]>([72.868, 19.088]); // Metro Airport
  const [routingMode, setRoutingMode] = useState<string>('car');
  const [routeResult, setRouteResult] = useState<RouteResponse | null>(null);
  const [isLoadingRoute, setIsLoadingRoute] = useState<boolean>(false);
  const [clickTarget, setClickTarget] = useState<'origin' | 'destination'>('origin');

  // Validation state
  const [validationMetrics, setValidationMetrics] = useState<ValidationMetrics | null>(null);
  const [validationMode, setValidationMode] = useState<string>('benchmark_physics');
  const [isValidationOpen, setIsValidationOpen] = useState<boolean>(false);
  const [isLoadingValidation, setIsLoadingValidation] = useState<boolean>(false);

  // ML Studio state
  const [isTrainModalOpen, setIsTrainModalOpen] = useState<boolean>(false);
  const [mlMetrics, setMlMetrics] = useState<any>(null);

  // Layer visibility toggles
  const [showFloodLayer, setShowFloodLayer] = useState<boolean>(true);
  const [showDrainageLayer, setShowDrainageLayer] = useState<boolean>(true);
  const [showRoadsLayer, setShowRoadsLayer] = useState<boolean>(true);
  const [showRoutesLayer, setShowRoutesLayer] = useState<boolean>(true);

  // Responsive UI Dock Layout State
  const [isLeftDockOpen, setIsLeftDockOpen] = useState<boolean>(() =>
    typeof window !== 'undefined' ? window.innerWidth >= 1024 : true
  );
  const [isRightDockOpen, setIsRightDockOpen] = useState<boolean>(() =>
    typeof window !== 'undefined' ? window.innerWidth >= 1280 : false
  );
  const [activeTab, setActiveTab] = useState<'conditions' | 'drainage' | 'layers'>('conditions');

  // Handle screen resize to enforce dock rules on mobile / tablet
  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      if (width < 1024) {
        // Mutual exclusion on screens < 1024px: cannot have both open simultaneously
        setIsRightDockOpen((rightOpen) => {
          if (rightOpen) setIsLeftDockOpen(false);
          return rightOpen;
        });
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleToggleLeftDock = (openState?: boolean) => {
    setIsLeftDockOpen((prev) => {
      const next = openState !== undefined ? openState : !prev;
      if (next && window.innerWidth < 1024) {
        setIsRightDockOpen(false);
      }
      return next;
    });
  };

  const handleToggleRightDock = (openState?: boolean) => {
    setIsRightDockOpen((prev) => {
      const next = openState !== undefined ? openState : !prev;
      if (next && window.innerWidth < 1024) {
        setIsLeftDockOpen(false);
      }
      return next;
    });
  };

  // Web Audio Synthetic Siren Beep for Emergency Alarm
  const playAlertSound = useCallback(() => {
    if (!soundEnabled) return;
    try {
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(880, audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.35);
      gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.35);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.35);
    } catch (e) {
      // AudioContext policy
    }
  }, [soundEnabled]);

  // 1. Initial Load: Scenarios, Cities, Drainage network, ML status, Initial Simulation
  useEffect(() => {
    const initApp = async () => {
      try {
        const [scenariosData, citiesData, drainageData, mlStatus] = await Promise.all([
          apiClient.getScenarios().catch(() => ({})),
          apiClient.getCities().catch(() => ({})),
          apiClient.getDrainageNetwork().catch(() => null),
          apiClient.getMLStatus().catch(() => null),
        ]);

        if (scenariosData) setScenarios(scenariosData);
        if (citiesData) setCities(citiesData);
        if (drainageData) setDrainageGeoJson(drainageData);
        if (mlStatus && mlStatus.metrics) setMlMetrics(mlStatus.metrics);

        await handleRunSimulation('extreme', 'physics');
      } catch (err) {
        console.error('Initialization error:', err);
      }
    };
    initApp();
  }, []);

  // 2. WebSocket Client with auto-reconnect
  useEffect(() => {
    let reconnectTimeout: any = null;
    let isCancelled = false;

    const connectWebSocket = () => {
      if (isCancelled) return;

      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsHost =
        window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
          ? `${window.location.hostname}:8000`
          : 'sihrecon.onrender.com';
      const wsUrl = `${wsProtocol}//${wsHost}/ws/live-feed`;

      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          setIsWsConnected(true);
        };

        ws.onmessage = async (event) => {
          try {
            const message = JSON.parse(event.data);
            if (message.type === 'simulation_update' && message.data) {
              setSimulationData(message.data);
              setIsAutoUpdating(!!message.auto_update);

              const mapData = await apiClient.getFloodMap(currentMinute).catch(() => null);
              if (mapData) setFloodGeoJson(mapData);

              fetchRoute(origin, destination, currentMinute, routingMode);
            }
          } catch (e) {
            console.error('WS parse error:', e);
          }
        };

        ws.onclose = () => {
          setIsWsConnected(false);
          if (!isCancelled) {
            reconnectTimeout = setTimeout(connectWebSocket, 5000);
          }
        };

        ws.onerror = () => {
          setIsWsConnected(false);
          ws.close();
        };
      } catch (e) {
        if (!isCancelled) {
          reconnectTimeout = setTimeout(connectWebSocket, 5000);
        }
      }
    };

    connectWebSocket();

    return () => {
      isCancelled = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (wsRef.current) wsRef.current.close();
    };
  }, [currentMinute, origin, destination, routingMode]);

  // 3. Run Simulation Handler
  const handleRunSimulation = async (
    scenarioToRun: string = currentScenario,
    modeToRun: EngineMode = engineMode,
    customRainfall?: any[]
  ) => {
    setIsLoadingSimulation(true);
    try {
      const result = await apiClient.runSimulation(
        scenarioToRun,
        customRainfall,
        180,
        modeToRun
      );
      setSimulationData(result);
      setCurrentScenario(scenarioToRun);
      setEngineMode(modeToRun);

      const mapData = await apiClient.getFloodMap(currentMinute);
      setFloodGeoJson(mapData);

      await fetchRoute(origin, destination, currentMinute, routingMode);

      const hasCritical = result.timesteps.some((t) => t.critical_zones_count > 0);
      if (hasCritical) {
        playAlertSound();
      }
    } catch (err) {
      console.error('Simulation execution failed:', err);
    } finally {
      setIsLoadingSimulation(false);
    }
  };

  // 4. Switch City Handler
  const handleSwitchCity = async (cityKey: string) => {
    try {
      setIsLoadingSimulation(true);
      await apiClient.switchCity(cityKey);
      setActiveCity(cityKey);

      const cfg = CITY_DEFAULTS[cityKey] || CITY_DEFAULTS.mumbai;
      setCityCenter(cfg.center);
      setOrigin(cfg.origin);
      setDestination(cfg.destination);

      const drainageData = await apiClient.getDrainageNetwork().catch(() => null);
      if (drainageData) setDrainageGeoJson(drainageData);

      await handleRunSimulation(currentScenario, engineMode);
    } catch (err) {
      console.error('Failed to switch city:', err);
    } finally {
      setIsLoadingSimulation(false);
    }
  };

  // 5. Radar Feed Selection Handler
  const handleSelectRadarFeed = async (source: string, apiKey?: string, event: string = 'mumbai_2005') => {
    try {
      setIsLoadingSimulation(true);
      const feedResult = await apiClient.getRadarFeed(source, apiKey, event);
      if (feedResult && feedResult.forecast && feedResult.forecast.length > 0) {
        setCurrentScenario(source === 'openweathermap' ? 'owm_live' : 'mumbai_2005');
        await handleRunSimulation('custom', engineMode, feedResult.forecast);
      }
    } catch (err) {
      console.error('Failed to load radar feed:', err);
    } finally {
      setIsLoadingSimulation(false);
    }
  };

  // 6. Toggle Background Auto-Update
  const handleToggleAutoUpdate = async () => {
    const nextState = !isAutoUpdating;
    try {
      await apiClient.triggerAutoUpdate(nextState, 60, currentScenario);
      setIsAutoUpdating(nextState);
    } catch (err) {
      console.error('Failed to toggle auto-update:', err);
    }
  };

  // 7. Time slider change handler
  const handleMinuteChange = useCallback(
    async (minute: number) => {
      setCurrentMinute(minute);
      try {
        const mapData = await apiClient.getFloodMap(minute);
        setFloodGeoJson(mapData);
        await fetchRoute(origin, destination, minute, routingMode);
      } catch (err) {
        console.error('Failed to update minute:', err);
      }
    },
    [origin, destination, routingMode]
  );

  // 8. Fetch Route
  const fetchRoute = async (
    orig: [number, number],
    dest: [number, number],
    minute: number,
    mode: string
  ) => {
    setIsLoadingRoute(true);
    try {
      const res = await apiClient.getRoute(orig, dest, minute, mode);
      setRouteResult(res);
    } catch (err) {
      console.error('Routing calculation failed:', err);
    } finally {
      setIsLoadingRoute(false);
    }
  };

  // 9. Map Click Handler
  const handleMapClick = (coords: [number, number]) => {
    if (clickTarget === 'origin') {
      setOrigin(coords);
      setClickTarget('destination');
      fetchRoute(coords, destination, currentMinute, routingMode);
    } else {
      setDestination(coords);
      setClickTarget('origin');
      fetchRoute(origin, coords, currentMinute, routingMode);
    }
  };

  // 10. Validation modal trigger
  const handleOpenValidation = async (mode: string = validationMode) => {
    setIsValidationOpen(true);
    setIsLoadingValidation(true);
    try {
      const metrics = await apiClient.validateSimulation(currentMinute, mode);
      setValidationMetrics(metrics);
    } catch (err) {
      console.error('Validation fetch error:', err);
    } finally {
      setIsLoadingValidation(false);
    }
  };

  const handleSelectValidationMode = (mode: string) => {
    setValidationMode(mode);
    handleOpenValidation(mode);
  };

  // 11. ML Model Training Handler
  const handleTrainMLModel = async (epochs: number, numStorms: number) => {
    const res = await apiClient.trainMLModel(epochs, numStorms);
    setMlMetrics(res);
    return res;
  };

  const currentFloodedRoads: FloodedRoadSegment[] =
    simulationData?.road_predictions?.[currentMinute] || [];
  const currentOverflowNodes: DrainNodeStatus[] =
    simulationData?.overflow_nodes?.[currentMinute] || [];

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-slate-950 text-slate-100 font-sans">
      {/* Top Command Bar */}
      <Header
        scenarios={scenarios}
        currentScenario={currentScenario}
        onSelectScenario={(sc) => {
          setCurrentScenario(sc);
          handleRunSimulation(sc, engineMode);
        }}
        onRunSimulation={() => handleRunSimulation(currentScenario, engineMode)}
        isLoading={isLoadingSimulation}
        executionTimeMs={simulationData?.execution_time_ms}
        onOpenValidation={() => handleOpenValidation(validationMode)}
        engineMode={engineMode}
        onToggleEngineMode={(mode) => {
          setEngineMode(mode);
          handleRunSimulation(currentScenario, mode);
        }}
        onOpenTrainModel={() => setIsTrainModalOpen(true)}
        radarReflectivityDbz={simulationData?.radar_reflectivity_dbz}
        soundEnabled={soundEnabled}
        onToggleSound={() => setSoundEnabled(!soundEnabled)}
        activeCity={activeCity}
        onSwitchCity={handleSwitchCity}
        cities={cities}
        onSelectRadarFeed={handleSelectRadarFeed}
        isWsConnected={isWsConnected}
        isAutoUpdating={isAutoUpdating}
        onToggleAutoUpdate={handleToggleAutoUpdate}
      />

      {/* Main Map & Interactive Workspace */}
      <div className="relative flex-1 w-full h-[calc(100vh-3.5rem)] overflow-hidden">
        <MapView
          floodGeoJson={floodGeoJson}
          drainageGeoJson={drainageGeoJson}
          floodedRoads={currentFloodedRoads}
          overflowNodes={currentOverflowNodes}
          routeResult={routeResult}
          origin={origin}
          destination={destination}
          onMapClick={handleMapClick}
          showFloodLayer={showFloodLayer}
          showDrainageLayer={showDrainageLayer}
          showRoadsLayer={showRoadsLayer}
          showRoutesLayer={showRoutesLayer}
          currentMinute={currentMinute}
          basemap={basemap}
          onBasemapChange={setBasemap}
          showRadarOverlay={showRadarOverlay}
          radarReflectivityDbz={simulationData?.radar_reflectivity_dbz}
          stormTrack={simulationData?.storm_track}
          cityCenter={cityCenter}
        />

        {/* ============================================================== */}
        {/* Unified Left Intelligence Dock (Tabs: Nowcast, Drainage, Layers) */}
        {/* ============================================================== */}
        {isLeftDockOpen ? (
          <div className="absolute top-3 sm:top-3.5 left-3 sm:left-3.5 z-30 sm:z-20 w-[calc(100vw-1.5rem)] sm:w-80 max-w-sm max-h-[calc(100vh-10.5rem)] sm:max-h-[calc(100vh-5.5rem)] flex flex-col bg-slate-900/95 border border-slate-800/90 rounded-2xl shadow-2xl backdrop-blur-xl overflow-hidden pointer-events-auto transition-all duration-300">
            {/* Dock Header & Navigation Tabs */}
            <div className="p-2 border-b border-slate-800 flex items-center justify-between bg-slate-950/70">
              <div className="flex items-center gap-1 p-0.5 bg-slate-900 rounded-xl border border-slate-800/80">
                <button
                  onClick={() => setActiveTab('conditions')}
                  className={`px-2 py-1 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all ${
                    activeTab === 'conditions'
                      ? 'bg-blue-600 text-white shadow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                  title="Real-time Nowcast Conditions & Road Blockages"
                >
                  <Activity className="w-3.5 h-3.5" />
                  <span>Nowcast</span>
                </button>

                <button
                  onClick={() => setActiveTab('drainage')}
                  className={`px-2 py-1 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all ${
                    activeTab === 'drainage'
                      ? 'bg-blue-600 text-white shadow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                  title="Subsurface Pipe Intake & Manhole Overflows"
                >
                  <GitFork className="w-3.5 h-3.5" />
                  <span>Drainage</span>
                </button>

                <button
                  onClick={() => setActiveTab('layers')}
                  className={`px-2 py-1 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all ${
                    activeTab === 'layers'
                      ? 'bg-blue-600 text-white shadow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                  title="Map Legend, Toggles, and GIS Export"
                >
                  <Layers className="w-3.5 h-3.5" />
                  <span>Layers</span>
                </button>
              </div>

              <button
                onClick={() => handleToggleLeftDock(false)}
                className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors ml-1"
                title="Collapse Nowcast Dock"
              >
                <PanelLeftClose className="w-4 h-4" />
              </button>
            </div>

            {/* Scrollable Dock Content */}
            <div className="p-3 overflow-y-auto flex-1 flex flex-col gap-3">
              {activeTab === 'conditions' && (
                <CurrentConditions
                  currentMinute={currentMinute}
                  timesteps={simulationData?.timesteps || []}
                  floodedRoads={currentFloodedRoads}
                />
              )}

              {activeTab === 'drainage' && (
                <DrainagePanel
                  overflowNodes={currentOverflowNodes}
                  currentMinute={currentMinute}
                />
              )}

              {activeTab === 'layers' && (
                <Legend
                  showFloodLayer={showFloodLayer}
                  onToggleFloodLayer={() => setShowFloodLayer(!showFloodLayer)}
                  showDrainageLayer={showDrainageLayer}
                  onToggleDrainageLayer={() => setShowDrainageLayer(!showDrainageLayer)}
                  showRoadsLayer={showRoadsLayer}
                  onToggleRoadsLayer={() => setShowRoadsLayer(!showRoadsLayer)}
                  showRoutesLayer={showRoutesLayer}
                  onToggleRoutesLayer={() => setShowRoutesLayer(!showRoutesLayer)}
                  showRadarOverlay={showRadarOverlay}
                  onToggleRadarOverlay={() => setShowRadarOverlay(!showRadarOverlay)}
                  currentMinute={currentMinute}
                />
              )}
            </div>
          </div>
        ) : (
          /* Collapsed Pill Button */
          <button
            onClick={() => handleToggleLeftDock(true)}
            className="absolute top-3 sm:top-3.5 left-3 sm:left-3.5 z-20 px-2.5 sm:px-3 py-1.5 sm:py-2 bg-slate-900/90 hover:bg-slate-800 border border-slate-800 text-slate-200 text-xs font-bold rounded-xl shadow-2xl backdrop-blur-md flex items-center gap-1.5 sm:gap-2 pointer-events-auto transition-all"
            title="Open Nowcast Dock"
          >
            <PanelLeftOpen className="w-3.5 sm:w-4 h-3.5 sm:h-4 text-cyan-400" />
            <span className="hidden xs:inline">Nowcast</span>
          </button>
        )}

        {/* ============================================================== */}
        {/* Right Collapsible Dock: Flood-Safe Emergency Routing */}
        {/* ============================================================== */}
        {isRightDockOpen ? (
          <div className="absolute top-3 sm:top-3.5 right-3 sm:right-3.5 z-30 sm:z-20 w-[calc(100vw-1.5rem)] sm:w-80 max-w-sm max-h-[calc(100vh-10.5rem)] sm:max-h-[calc(100vh-5.5rem)] flex flex-col bg-slate-900/95 border border-slate-800/90 rounded-2xl shadow-2xl backdrop-blur-xl overflow-hidden pointer-events-auto transition-all duration-300">
            {/* Dock Header */}
            <div className="p-2.5 border-b border-slate-800 flex items-center justify-between bg-slate-950/70">
              <div className="flex items-center gap-2 px-1">
                <Navigation className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Emergency Routing
                </span>
              </div>
              <button
                onClick={() => handleToggleRightDock(false)}
                className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                title="Collapse Routing Dock"
              >
                <PanelRightClose className="w-4 h-4" />
              </button>
            </div>

            {/* Routing Controller */}
            <div className="p-3 overflow-y-auto flex-1">
              <RoutingPanel
                origin={origin}
                destination={destination}
                onOriginChange={(coords) => {
                  setOrigin(coords);
                  fetchRoute(coords, destination, currentMinute, routingMode);
                }}
                onDestinationChange={(coords) => {
                  setDestination(coords);
                  fetchRoute(origin, coords, currentMinute, routingMode);
                }}
                routeResult={routeResult}
                isLoading={isLoadingRoute}
                onRecalculateRoute={() =>
                  fetchRoute(origin, destination, currentMinute, routingMode)
                }
                mode={routingMode}
                onModeChange={(m) => {
                  setRoutingMode(m);
                  fetchRoute(origin, destination, currentMinute, m);
                }}
              />
            </div>
          </div>
        ) : (
          /* Collapsed Pill Button */
          <button
            onClick={() => handleToggleRightDock(true)}
            className="absolute top-3 sm:top-3.5 right-3 sm:right-3.5 z-20 px-2.5 sm:px-3 py-1.5 sm:py-2 bg-slate-900/90 hover:bg-slate-800 border border-slate-800 text-slate-200 text-xs font-bold rounded-xl shadow-2xl backdrop-blur-md flex items-center gap-1.5 sm:gap-2 pointer-events-auto transition-all"
            title="Open Emergency Routing"
          >
            <Navigation className="w-3.5 sm:w-4 h-3.5 sm:h-4 text-emerald-400" />
            <span className="hidden xs:inline">Routing</span>
            <PanelRightOpen className="w-3.5 sm:w-4 h-3.5 sm:h-4 text-slate-400" />
          </button>
        )}

        {/* ============================================================== */}
        {/* Floating Bottom Center: Forecast Timeline Slider */}
        {/* ============================================================== */}
        <div className="absolute bottom-3 sm:bottom-4 left-1/2 -translate-x-1/2 z-20 w-full max-w-xl px-2 sm:px-4 pointer-events-auto">
          <TimeSlider
            currentMinute={currentMinute}
            onMinuteChange={handleMinuteChange}
            timesteps={simulationData?.timesteps || []}
          />
        </div>
      </div>

      {/* Validation Report Modal */}
      <ValidationModal
        isOpen={isValidationOpen}
        onClose={() => setIsValidationOpen(false)}
        metrics={validationMetrics}
        isLoading={isLoadingValidation}
        currentMode={validationMode}
        onSelectMode={handleSelectValidationMode}
      />

      {/* AI / Machine Learning Surrogate Model Studio Modal */}
      <ModelTrainingModal
        isOpen={isTrainModalOpen}
        onClose={() => setIsTrainModalOpen(false)}
        onTrain={handleTrainMLModel}
        currentMetrics={mlMetrics}
      />
    </div>
  );
};

export default App;
