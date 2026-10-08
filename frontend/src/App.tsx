import React, { useState, useEffect, useCallback } from 'react';
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
  MLTrainingResponse
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
import { Activity, GitFork, Radio } from 'lucide-react';

export const App: React.FC = () => {
  // Scenario, Simulation, and Engine state
  const [scenarios, setScenarios] = useState<Record<string, ScenarioInfo>>({});
  const [currentScenario, setCurrentScenario] = useState<string>('extreme');
  const [simulationData, setSimulationData] = useState<SimulationResponse | null>(null);
  const [isLoadingSimulation, setIsLoadingSimulation] = useState<boolean>(false);
  const [currentMinute, setCurrentMinute] = useState<number>(90);
  const [engineMode, setEngineMode] = useState<EngineMode>('physics');

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

  // Modals state
  const [validationMetrics, setValidationMetrics] = useState<ValidationMetrics | null>(null);
  const [isValidationOpen, setIsValidationOpen] = useState<boolean>(false);
  const [isLoadingValidation, setIsLoadingValidation] = useState<boolean>(false);

  const [isTrainModalOpen, setIsTrainModalOpen] = useState<boolean>(false);
  const [mlMetrics, setMlMetrics] = useState<any>(null);

  // Layer visibility toggles
  const [showFloodLayer, setShowFloodLayer] = useState<boolean>(true);
  const [showDrainageLayer, setShowDrainageLayer] = useState<boolean>(true);
  const [showRoadsLayer, setShowRoadsLayer] = useState<boolean>(true);
  const [showRoutesLayer, setShowRoutesLayer] = useState<boolean>(true);

  // Active side panel tab
  const [activeTab, setActiveTab] = useState<'conditions' | 'routing' | 'drainage'>('routing');

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

  // 1. Initial Load: Scenarios, Drainage network, ML status, Initial Simulation
  useEffect(() => {
    const initApp = async () => {
      try {
        const [scenariosData, drainageData, mlStatus] = await Promise.all([
          apiClient.getScenarios(),
          apiClient.getDrainageNetwork(),
          apiClient.getMLStatus().catch(() => null),
        ]);
        setScenarios(scenariosData);
        setDrainageGeoJson(drainageData);
        if (mlStatus && mlStatus.metrics) {
          setMlMetrics(mlStatus.metrics);
        }

        await handleRunSimulation('extreme', 'physics');
      } catch (err) {
        console.error('Initialization error:', err);
      }
    };
    initApp();
  }, []);

  // 2. Run Simulation Handler
  const handleRunSimulation = async (
    scenarioToRun: string = currentScenario,
    modeToRun: EngineMode = engineMode
  ) => {
    setIsLoadingSimulation(true);
    try {
      const result = await apiClient.runSimulation(scenarioToRun, undefined, 180, modeToRun);
      setSimulationData(result);
      setCurrentScenario(scenarioToRun);
      setEngineMode(modeToRun);

      const mapData = await apiClient.getFloodMap(currentMinute);
      setFloodGeoJson(mapData);

      await fetchRoute(origin, destination, currentMinute, routingMode);

      // Play alert sound if critical zone detected
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

  // 3. Time slider change handler
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

  // 4. Fetch Route
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

  // 5. Map Click Handler
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

  // 6. Validation modal trigger
  const handleOpenValidation = async () => {
    setIsValidationOpen(true);
    setIsLoadingValidation(true);
    try {
      const metrics = await apiClient.validateSimulation(currentMinute);
      setValidationMetrics(metrics);
    } catch (err) {
      console.error('Validation fetch error:', err);
    } finally {
      setIsLoadingValidation(false);
    }
  };

  // 7. ML Model Training Handler
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
        onOpenValidation={handleOpenValidation}
        engineMode={engineMode}
        onToggleEngineMode={(mode) => {
          setEngineMode(mode);
          handleRunSimulation(currentScenario, mode);
        }}
        onOpenTrainModel={() => setIsTrainModalOpen(true)}
        radarReflectivityDbz={simulationData?.radar_reflectivity_dbz}
        soundEnabled={soundEnabled}
        onToggleSound={() => setSoundEnabled(!soundEnabled)}
      />

      {/* Main Map & Workspace */}
      <div className="relative flex-1 w-full h-[calc(100vh-4rem)] overflow-hidden">
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
        />

        {/* Floating Left Panel: Conditions & Drainage Health */}
        <div className="absolute top-4 left-4 z-20 w-80 max-h-[calc(100vh-8.5rem)] flex flex-col gap-3 pointer-events-auto">
          <div className="bg-slate-900/90 border border-slate-800 p-1 rounded-xl shadow-xl backdrop-blur-md flex items-center gap-1">
            <button
              onClick={() => setActiveTab('conditions')}
              className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition-all ${
                activeTab === 'conditions'
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Conditions</span>
            </button>
            <button
              onClick={() => setActiveTab('drainage')}
              className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition-all ${
                activeTab === 'drainage'
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <GitFork className="w-3.5 h-3.5" />
              <span>Drainage</span>
            </button>
          </div>

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
        </div>

        {/* Floating Right Panel: Routing Engine Controller */}
        <div className="absolute top-4 right-4 z-20 w-84 max-h-[calc(100vh-8.5rem)] overflow-y-auto pointer-events-auto">
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

        {/* Floating Bottom Center: Time Scrubber Slider */}
        <div className="absolute bottom-5 left-1/2 -translate-x-1/2 z-20 w-full max-w-xl px-4 pointer-events-auto">
          <TimeSlider
            currentMinute={currentMinute}
            onMinuteChange={handleMinuteChange}
            timesteps={simulationData?.timesteps || []}
          />
        </div>

        {/* Floating Bottom Left: Legend, Radar Toggle, & Layers */}
        <div className="absolute bottom-5 left-4 z-20 pointer-events-auto flex flex-col gap-2">
          {/* Weather Radar Toggle */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-2 shadow-xl backdrop-blur-md flex items-center justify-between text-xs font-semibold text-slate-300">
            <span className="flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 text-red-400" />
              Doppler Rain Echo
            </span>
            <input
              type="checkbox"
              checked={showRadarOverlay}
              onChange={(e) => setShowRadarOverlay(e.target.checked)}
              className="accent-cyan-400 cursor-pointer"
            />
          </div>

          <Legend
            showFloodLayer={showFloodLayer}
            onToggleFloodLayer={() => setShowFloodLayer(!showFloodLayer)}
            showDrainageLayer={showDrainageLayer}
            onToggleDrainageLayer={() => setShowDrainageLayer(!showDrainageLayer)}
            showRoadsLayer={showRoadsLayer}
            onToggleRoadsLayer={() => setShowRoadsLayer(!showRoadsLayer)}
            showRoutesLayer={showRoutesLayer}
            onToggleRoutesLayer={() => setShowRoutesLayer(!showRoutesLayer)}
          />
        </div>
      </div>

      {/* Validation Report Modal */}
      <ValidationModal
        isOpen={isValidationOpen}
        onClose={() => setIsValidationOpen(false)}
        metrics={validationMetrics}
        isLoading={isLoadingValidation}
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
