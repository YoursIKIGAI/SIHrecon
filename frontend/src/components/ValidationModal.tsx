import React from 'react';
import { X, CheckCircle2, AlertTriangle, BarChart2, Info, ShieldAlert } from 'lucide-react';
import { ValidationMetrics } from '../types';

interface ValidationModalProps {
  isOpen: boolean;
  onClose: () => void;
  metrics: ValidationMetrics | null;
  isLoading: boolean;
}

export const ValidationModal: React.FC<ValidationModalProps> = ({
  isOpen,
  onClose,
  metrics,
  isLoading,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <BarChart2 className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-white">
                Hydrodynamic Prediction Accuracy & Validation
              </h3>
              <p className="text-[11px] text-slate-400">
                Evaluation against ground-truth hydrodynamic benchmark
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-5 flex flex-col gap-4 overflow-y-auto">
          {/* Scientific Honesty Notice Banner */}
          <div className="p-3 bg-amber-950/40 border border-amber-800/60 rounded-xl flex items-start gap-2.5 text-xs text-amber-200">
            <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="flex flex-col gap-1 leading-relaxed">
              <span className="font-bold uppercase tracking-wider text-[11px] text-amber-300">
                Scientific Disclaimer & Data Transparency
              </span>
              <p className="text-[11px] text-amber-200/90">
                This validation compares against a <strong>high-fidelity synthetic kinematic benchmark</strong> for hackathon 
                demonstration. Real-world urban deployment requires calibration against municipal ultrasonic depth sensors 
                and road-mounted IoT water level gauges. Centimeter-level precision is not claimed on uncalibrated ungauged basins.
              </p>
            </div>
          </div>

          {isLoading || !metrics ? (
            <div className="py-12 flex flex-col items-center justify-center gap-3 text-slate-400">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs">Evaluating spatial confusion matrix & RMSE...</span>
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
                <span className="text-xs font-bold text-slate-300">
                  Grid Cell Inundation Classification Matrix (2,000 DEM cells)
                </span>
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

              {/* Model Assumptions & Limitations */}
              <div className="bg-slate-950/40 border border-slate-800 rounded-xl p-3 flex flex-col gap-1.5 text-xs text-slate-400">
                <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5 text-blue-400" />
                  Key Physical Assumptions & Architectural Decisions:
                </span>
                <ul className="list-disc pl-4 space-y-1 text-[11px] leading-relaxed">
                  <li>DEM D8 steepest descent routes overland surface water rapidly using vectorized topological sort order.</li>
                  <li>Subsurface drainage represents manholes as storage capacitors and pipes as maximum flow throttle constraints.</li>
                  <li>In extreme rainfall, pipe capacity surcharge causes localized ponding above design backflow levels.</li>
                  <li>Road water depth is evaluated as the maximum inundation across traversed grid cells, flagging routes &gt;40cm as impassable.</li>
                </ul>
              </div>
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3 border-t border-slate-800 bg-slate-950/60 flex justify-end">
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
