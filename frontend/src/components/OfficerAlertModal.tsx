import React, { useState } from 'react';
import { 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  MapPin, 
  Activity, 
  X, 
  Filter,
  Check,
  Info
} from 'lucide-react';
import { OfficerAlert } from '../types';
import { apiClient } from '../api/client';

interface OfficerAlertModalProps {
  isOpen: boolean;
  onClose: () => void;
  alerts: OfficerAlert[];
  onAlertStatusChange: (alertId: string, newStatus: 'active' | 'acknowledged' | 'resolved' | 'dismissed') => void;
  simulationMode?: string;
  activeCity?: string;
}

export const OfficerAlertModal: React.FC<OfficerAlertModalProps> = ({
  isOpen,
  onClose,
  alerts,
  onAlertStatusChange,
  simulationMode = 'live',
  activeCity = 'mumbai',
}) => {
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleUpdateStatus = async (alertId: string, status: 'active' | 'acknowledged' | 'resolved' | 'dismissed') => {
    try {
      setUpdatingId(alertId);
      await apiClient.updateAlertStatus(alertId, status);
      onAlertStatusChange(alertId, status);
    } catch (err) {
      console.error('Failed to update alert status:', err);
    } finally {
      setUpdatingId(null);
    }
  };

  const filteredAlerts = alerts.filter((a) => {
    if (filterSeverity !== 'all' && a.severity.toLowerCase() !== filterSeverity.toLowerCase()) {
      return false;
    }
    if (filterStatus !== 'all' && a.status.toLowerCase() !== filterStatus.toLowerCase()) {
      return false;
    }
    return true;
  });

  const getSeverityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'bg-red-500/20 text-red-400 border-red-500/50';
      case 'high':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/50';
      case 'moderate':
        return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/50';
      default:
        return 'bg-blue-500/20 text-blue-300 border-blue-500/50';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
        return 'bg-red-950 text-red-300 border-red-800';
      case 'acknowledged':
        return 'bg-yellow-950 text-yellow-300 border-yellow-800';
      case 'resolved':
        return 'bg-emerald-950 text-emerald-300 border-emerald-800';
      case 'dismissed':
        return 'bg-slate-800 text-slate-400 border-slate-700';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const isTestMode = simulationMode !== 'live';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-md animate-in fade-in">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-red-600/20 border border-red-500/40 flex items-center justify-center text-red-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm sm:text-base font-bold text-white tracking-wide">
                  MUNICIPAL OFFICER EMERGENCY ALERT DASHBOARD
                </h2>
                <span className="text-[10px] px-2 py-0.5 rounded-full font-mono font-bold uppercase bg-slate-800 border border-slate-700 text-cyan-300">
                  {activeCity}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Actionable hydrological warnings, road cuts, and drainage surcharge alerts.
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

        {/* Test Mode Isolation Warning Banner */}
        {isTestMode && (
          <div className="bg-amber-950/60 border-b border-amber-800/80 px-5 py-2 flex items-center justify-between text-xs text-amber-300">
            <div className="flex items-center gap-2">
              <Info className="w-4 h-4 text-amber-400 shrink-0" />
              <span>
                <strong>TEST SIMULATION MODE ACTIVE:</strong> Alerts displayed below are generated exclusively within the test environment. Real-world emergency dispatch feeds remain isolated.
              </span>
            </div>
            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-amber-900/80 border border-amber-700 font-bold">
              {simulationMode.toUpperCase()} REPLAY
            </span>
          </div>
        )}

        {/* Filter Toolbar */}
        <div className="px-5 py-2.5 border-b border-slate-800/80 bg-slate-950/40 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Severity:</span>
            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-slate-200 focus:outline-none"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="moderate">Moderate</option>
            </select>

            <span className="text-slate-400 ml-2">Status:</span>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-slate-200 focus:outline-none"
            >
              <option value="all">All Statuses</option>
              <option value="active">Active</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="resolved">Resolved</option>
              <option value="dismissed">Dismissed</option>
            </select>
          </div>

          <div className="text-slate-400 font-mono text-[11px]">
            Showing <strong className="text-white">{filteredAlerts.length}</strong> of {alerts.length} alert(s)
          </div>
        </div>

        {/* Alert Cards Container */}
        <div className="p-5 overflow-y-auto space-y-3.5 flex-1 max-h-[60vh]">
          {filteredAlerts.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              <CheckCircle2 className="w-10 h-10 mx-auto mb-2 text-emerald-500/60" />
              <p className="text-sm font-semibold text-slate-400">No matching alerts for the selected criteria.</p>
              <p className="text-xs text-slate-500 mt-1">All monitored roadway segments and drainage nodes operate within safe tolerances.</p>
            </div>
          ) : (
            filteredAlerts.map((alert) => (
              <div
                key={alert.alert_id}
                className={`p-4 rounded-xl border transition-all ${
                  alert.status === 'resolved' || alert.status === 'dismissed'
                    ? 'bg-slate-950/40 border-slate-800 opacity-60'
                    : 'bg-slate-950/80 border-slate-800 hover:border-slate-700'
                }`}
              >
                {/* Alert Top Row */}
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${getSeverityBadge(alert.severity)}`}>
                      {alert.severity.toUpperCase()}
                    </span>
                    <span className="text-xs font-mono font-bold text-slate-300">
                      {alert.alert_id}
                    </span>
                    <span className="text-slate-500 text-xs">•</span>
                    <span className="text-xs text-slate-300 flex items-center gap-1 font-semibold">
                      <MapPin className="w-3 h-3 text-red-400" />
                      {alert.locality}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-slate-400 font-mono flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {alert.timestamp.replace('T', ' ').slice(0, 19)}
                    </span>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase font-bold ${getStatusBadge(alert.status)}`}>
                      {alert.status}
                    </span>
                  </div>
                </div>

                {/* Trigger Condition */}
                <div className="text-xs text-slate-200 font-medium mb-1.5">
                  <span className="text-slate-400 text-[11px] uppercase mr-1">Condition:</span>
                  {alert.trigger_condition}
                </div>

                {/* Supporting Data & Confidence */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80 mb-2.5">
                  <div>
                    <span className="text-slate-500 uppercase text-[10px] block">Supporting Telemetry:</span>
                    <span className="text-slate-300">{alert.supporting_data}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 uppercase text-[10px] block">Model Confidence:</span>
                    <span className="text-cyan-400">{alert.confidence}</span>
                  </div>
                </div>

                {/* Recommended Action & Action Buttons */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-slate-900">
                  <div className="text-xs text-amber-300 flex-1 min-w-[200px]">
                    <span className="text-[10px] uppercase font-bold text-amber-500/90 mr-1.5">Recommended Action:</span>
                    {alert.recommended_action}
                  </div>

                  {/* Status Change Buttons */}
                  <div className="flex items-center gap-1.5 shrink-0">
                    {alert.status !== 'acknowledged' && alert.status !== 'resolved' && (
                      <button
                        disabled={updatingId === alert.alert_id}
                        onClick={() => handleUpdateStatus(alert.alert_id, 'acknowledged')}
                        className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-yellow-950/80 border border-yellow-700/80 text-yellow-300 hover:bg-yellow-900 transition-colors"
                      >
                        Acknowledge
                      </button>
                    )}
                    {alert.status !== 'resolved' && (
                      <button
                        disabled={updatingId === alert.alert_id}
                        onClick={() => handleUpdateStatus(alert.alert_id, 'resolved')}
                        className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-emerald-950/80 border border-emerald-700/80 text-emerald-300 hover:bg-emerald-900 transition-colors flex items-center gap-1"
                      >
                        <Check className="w-3 h-3" />
                        <span>Resolve</span>
                      </button>
                    )}
                    {alert.status !== 'dismissed' && (
                      <button
                        disabled={updatingId === alert.alert_id}
                        onClick={() => handleUpdateStatus(alert.alert_id, 'dismissed')}
                        className="px-2 py-1 text-xs rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                      >
                        Dismiss
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between text-xs text-slate-400">
          <span>
            Alert status updates are stored in active state and do not contaminate underlying physical predictions.
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-semibold transition-colors"
          >
            Close Dashboard
          </button>
        </div>
      </div>
    </div>
  );
};
