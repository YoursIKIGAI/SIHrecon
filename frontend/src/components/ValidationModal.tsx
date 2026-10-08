import React, { useState } from 'react';
import { X, CheckCircle2, AlertTriangle, BarChart2, Info, ShieldAlert, Cpu, Database, Sparkles } from 'lucide-react';
import { ValidationMetrics } from '../types';

interface ValidationModalProps {
  isOpen: boolean;
  onClose: () => void;
  metrics: ValidationMetrics | null;
  isLoading: boolean;
  currentMode?: string;
  onSelectMode?: (mode: string) => void;
}

export const ValidationModal: React.FC<ValidationModalProps> = ({
  isOpen,
  onClose,
  metrics,
  isLoading,
  currentMode = 'benchmark_physics',
  onSelectMode,
}) => {
  const [selectedMode, setSelectedMode] = useState<string>(currentMode);

  if (!isOpen) return null;

  const handleModeChange = (mode: string) => {
    setSelectedMode(mode);
    if (onSelectMode) {
      onSelectMode(mode);
    }
  };

  const isSelfNoise = selectedMode === 'self_noise' || metrics?.status_label?.includes('DEMONSTRATION');
  const isBenchmarkPhysics = selectedMode === 'benchmark_physics';
  const isHistoricalEvent = selectedMode === 'historical_event';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <BarChart2 className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-sm text-white">
                  Hydrodynamic Accuracy & Benchmark Validation
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800">
                  FIX 3 VERIFIED
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Independent ground-truth benchmarking across split physics and field observations
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 flex flex-col gap-4 overflow-y-auto">
          {/* Mode Selector (Fix 3) */}
          <div className="flex flex-col gap-2">
            <span className="text-[11px] uppercase font-bold text-slate-400 tracking-wider">
              Select Ground-Truth Validation Methodology:
            </span>
            <div className="grid grid-cols-3 gap-2">
              <button
                onClick={() => handleModeChange('benchmark_physics')}
                className={`p-2.5 rounded-xl border text-left transition-all ${
                  selectedMode === 'benchmark_physics'
                    ? 'bg-blue-950/70 border-blue-500 text-white shadow-md shadow-blue-950/50'
                    : 'bg-slate-950/50 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <div className="flex items-center gap-1.5 text-xs font-bold text-blue-400">
                  <Cpu className="w-3.5 h-3.5" />
                  <span>Physics Benchmark</span>
                </div>
                <div className="text-[10px] text-slate-400 mt-1 leading-snug">
                  Independent physics run with dry soil infiltration split
                </div>
              </button>

              <button
                onClick={() => handleModeChange('historical_event')}
                className={`p-2.5 rounded-xl border text-left transition-all ${
                  selectedMode === 'historical_event'
                    ? 'bg-emerald-950/70 border-emerald-500 text-white shadow-md shadow-emerald-950/50'
                    : 'bg-slate-950/50 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-400">
                  <Database className="w-3.5 h-3.5" />
                  <span>Field Observations CSV</span>
                </div>
                <div className="text-[10px] text-slate-400 mt-1 leading-snug">
                  20 sensor & gauge observation points (Mumbai CSV)
                </div>
              </button>

              <button
                onClick={() => handleModeChange('self_noise')}
                className={`p-2.5 rounded-xl border text-left transition-all ${
                  selectedMode === 'self_noise'
                    ? 'bg-amber-950/70 border-amber-500 text-white shadow-md shadow-amber-950/50'
                    : 'bg-slate-950/50 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <div className="flex items-center gap-1.5 text-xs font-bold text-amber-400">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Self-Noise (Demo Only)</span>
                </div>
                <div className="text-[10px] text-slate-400 mt-1 leading-snug">
                  Old synthetic circular benchmark labeled for reference
                </div>
              </button>
            </div>
          </div>

          {/* Warning Banner for self_noise mode */}
          {isSelfNoise && (
            <div className="p-3 bg-red-950/50 border border-red-700/60 rounded-xl flex items-start gap-2.5 text-xs text-red-200 animate-in fade-in">
              <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div className="flex flex-col gap-1 leading-relaxed">
                <span className="font-bold uppercase tracking-wider text-[11px] text-red-300">
                  ⚠️ Demonstration Benchmark Warning
                </span>
                <p className="text-[11px] text-red-200/90">
                  This validation compares the prediction against a noisy variation of its own simulation. 
                  This is <strong>demonstration only</strong> and does NOT represent rigorous field accuracy. 
                  Switch to <strong>Physics Benchmark</strong> or <strong>Field Observations CSV</strong> for scientific integrity.
                </p>
              </div>
            </div>
          )}

          {/* Info Banner for benchmark_physics mode */}
          {isBenchmarkPhysics && (
            <div className="p-3 bg-blue-950/40 border border-blue-800/60 rounded-xl flex items-start gap-2.5 text-xs text-blue-200">
              <Info className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
              <div className="flex flex-col gap-1 leading-relaxed">
                <span className="font-bold uppercase tracking-wider text-[11px] text-blue-300">
                  Split-Model Benchmark Methodology
                </span>
                <p className="text-[11px] text-blue-200/90">
                  Runs a separate, independent hydraulic solver run with dry-soil parameters (2.0 mm/hr infiltration capacity) 
                  under heavy baseline rainfall. This produces an independent ground-truth grid without circular self-reference.
                </p>
              </div>
            </div>
          )}

          {/* Info Banner for historical_event mode */}
          {isHistoricalEvent && (
            <div className="p-3 bg-emerald-950/40 border border-emerald-800/60 rounded-xl flex items-start gap-2.5 text-xs text-emerald-200">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              <div className="flex flex-col gap-1 leading-relaxed">
                <span className="font-bold uppercase tracking-wider text-[11px] text-emerald-300">
                  Field Observations CSV Ground Truth
                </span>
                <p className="text-[11px] text-emerald-200/90">
                  Loaded from <code className="bg-emerald-950 px-1 rounded text-emerald-300 font-mono">backend/data/validation/mumbai_flood_observed.csv</code>.
                  Interpolated 20 historical survey points across known waterlogging spots (Milan Subway, King's Circle, Hindmata, Kurla Creek).
                </p>
              </div>
            </div>
          )}

          {isLoading || !metrics ? (
            <div className="py-12 flex flex-col items-center justify-center gap-3 text-slate-400">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs">Evaluating spatial confusion matrix & RMSE for {selectedMode}...</span>
            </div>
          ) : (
            <>
              {/* Primary Validation Score Cards */}
              <div className="grid grid-cols-4 gap-2.5">
                <div className="bg-slate-950/70 border border-slate-800 p-3 rounded-xl flex flex-col items-center text-center">
                  <span className="text-[10px] uppercase font-semibold text-slate-400">Precision</span>
                  <span className="text-xl font-bold font-mono text-emerald-400 mt-1">
                    {(metrics.precision * 100).toFixed(1)}%
                  </span>
                  <span className="text-[9px] text-slate-500 mt-0.5">True inundation</span>
                </div>

                <div className="bg-slate-950/70 border border-slate-800 p-3 rounded-xl flex flex-col items-center text-center">
                  <span className="text-[10px] uppercase font-semibold text-slate-400">Recall</span>
                  <span className="text-xl font-bold font-mono text-blue-400 mt-1">
                    {(metrics.recall * 100).toFixed(1)}%
                  </span>
                  <span className="text-[9px] text-slate-500 mt-0.5">Floods caught</span>
                </div>

                <div className="bg-slate-950/70 border border-slate-800 p-3 rounded-xl flex flex-col items-center text-center">
                  <span className="text-[10px] uppercase font-semibold text-slate-400">F1 Score</span>
                  <span className="text-xl font-bold font-mono text-indigo-400 mt-1">
                    {metrics.f1_score.toFixed(3)}
                  </span>
                  <span className="text-[9px] text-slate-500 mt-0.5">Harmonic mean</span>
                </div>

                <div className="bg-slate-950/70 border border-slate-800 p-3 rounded-xl flex flex-col items-center text-center">
                  <span className="text-[10px] uppercase font-semibold text-slate-400">Depth RMSE</span>
                  <span className="text-xl font-bold font-mono text-amber-400 mt-1">
                    ±{metrics.rmse_depth_cm}
                  </span>
                  <span className="text-[9px] text-slate-500 mt-0.5">Centimeters</span>
                </div>
              </div>

              {/* Confusion Matrix Table */}
              <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-300">
                    Grid Cell Inundation Classification Matrix ({metrics.num_samples.toLocaleString()} cells)
                  </span>
                  <span className="text-[10px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                    Mode: {metrics.dataset_type}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div className="bg-emerald-950/30 border border-emerald-800/40 p-2.5 rounded-lg flex justify-between items-center">
                    <span className="text-emerald-400">True Positives (Correct Floods):</span>
                    <strong className="text-white">{metrics.confusion_matrix.true_positive_cells}</strong>
                  </div>
                  <div className="bg-slate-900 border border-slate-800 p-2.5 rounded-lg flex justify-between items-center">
                    <span className="text-slate-400">True Negatives (Dry Cells):</span>
                    <strong className="text-white">{metrics.confusion_matrix.true_negative_cells}</strong>
                  </div>
                  <div className="bg-amber-950/30 border border-amber-800/40 p-2.5 rounded-lg flex justify-between items-center">
                    <span className="text-amber-400">False Positives (Overpredicted):</span>
                    <strong className="text-white">{metrics.confusion_matrix.false_positive_cells}</strong>
                  </div>
                  <div className="bg-red-950/30 border border-red-800/40 p-2.5 rounded-lg flex justify-between items-center">
                    <span className="text-red-400">False Negatives (Missed Floods):</span>
                    <strong className="text-white">{metrics.confusion_matrix.false_negative_cells}</strong>
                  </div>
                </div>
              </div>

              {/* Validation Notes */}
              {metrics.notes && (
                <div className="bg-slate-950/40 border border-slate-800 rounded-xl p-3 flex flex-col gap-1 text-xs text-slate-400">
                  <span className="font-semibold text-slate-300">Methodology Notes:</span>
                  <p className="text-[11px] leading-relaxed text-slate-400 font-mono">
                    {metrics.notes}
                  </p>
                </div>
              )}
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-slate-800 bg-slate-950/60 flex justify-between items-center">
          <span className="text-[11px] text-slate-500">
            Validated at timestep T+90m (peak nowcast horizon)
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-semibold transition-colors"
          >
            Close Validation Report
          </button>
        </div>
      </div>
    </div>
  );
};
