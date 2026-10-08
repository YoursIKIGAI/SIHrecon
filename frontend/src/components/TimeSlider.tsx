
import React, { useEffect, useState } from 'react';
import { Play, Pause, RotateCcw, Clock, CloudRain } from 'lucide-react';
import { TimestepSummary } from '../types';

interface TimeSliderProps {
  currentMinute: number;
  onMinuteChange: (minute: number) => void;
  timesteps: TimestepSummary[];
}

export const TimeSlider: React.FC<TimeSliderProps> = ({
  currentMinute,
  onMinuteChange,
  timesteps,
}) => {
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const minutesList =
    timesteps.length > 0
      ? timesteps.map((t) => t.minutes)
      : [0, 30, 60, 90, 120, 180];

  const currentSummary = timesteps.find((t) => t.minutes === currentMinute);

  // Auto-play animation loop
  useEffect(() => {
    let timer: any;

    if (isPlaying) {
      timer = setInterval(() => {
        const currentIndex = minutesList.indexOf(currentMinute);

        if (
          currentIndex === -1 ||
          currentIndex >= minutesList.length - 1
        ) {
          onMinuteChange(minutesList[0]);
        } else {
          onMinuteChange(minutesList[currentIndex + 1]);
        }
      }, 1600);
    }

    return () => clearInterval(timer);
  }, [isPlaying, minutesList, currentMinute, onMinuteChange]);

  const currentIndex = minutesList.indexOf(currentMinute);

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3 shadow-2xl backdrop-blur-md flex items-center gap-4">
      {/* Play/Pause & Reset */}
      <div className="flex items-center gap-1.5 shrink-0">
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className={`w-9 h-9 rounded-lg flex items-center justify-center transition-all ${
            isPlaying
              ? 'bg-amber-600 text-white shadow-lg shadow-amber-600/30'
              : 'bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/30'
          }`}
          title={
            isPlaying
              ? 'Pause timeline animation'
              : 'Play timeline progression'
          }
        >
          {isPlaying ? (
            <Pause className="w-4 h-4" />
          ) : (
            <Play className="w-4 h-4 fill-current ml-0.5" />
          )}
        </button>

        <button
          onClick={() => {
            setIsPlaying(false);
            onMinuteChange(minutesList[0]);
          }}
          className="w-9 h-9 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center justify-center transition-colors"
          title="Reset to T+0 (NOW)"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      {/* Discrete Timeline Scrubber */}
      <div className="flex-1 flex flex-col gap-1.5">
        <div className="flex items-center justify-between text-xs font-mono text-slate-400">
          <span className="flex items-center gap-1.5 text-blue-400 font-semibold">
            <Clock className="w-3.5 h-3.5" />
            FORECAST TIMELINE:
            <span className="bg-blue-950 px-2 py-0.5 rounded border border-blue-800 text-blue-200">
              {currentMinute === 0
                ? 'NOW (T+0)'
                : `T+${currentMinute} MIN`}
            </span>
          </span>

          {currentSummary && (
            <span className="flex items-center gap-1.5 text-amber-300 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-800/40 text-[11px]">
              <CloudRain className="w-3 h-3 text-amber-400" />
              Intensity:{' '}
              <strong>{currentSummary.rainfall_mm_hr} mm/hr</strong>
            </span>
          )}
        </div>

        {/* Steps track */}
        <div className="relative flex items-center justify-between w-full pt-1 pb-1">
          {/* Progress bar line */}
          <div className="absolute left-0 right-0 h-1.5 bg-slate-800 rounded-full -z-0">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-300"
              style={{
                width: `${
                  (currentIndex / Math.max(1, minutesList.length - 1)) * 100
                }%`,
              }}
            />
          </div>

          {/* Step buttons */}
          {minutesList.map((m, idx) => {
            const active = m === currentMinute;
            const past = m <= currentMinute;
            const stepLabel = m === 0 ? 'NOW' : `${m}m`;

            return (
              <button
                key={m}
                onClick={() => {
                  setIsPlaying(false);
                  onMinuteChange(m);
                }}
                className="relative z-10 flex flex-col items-center group focus:outline-none"
              >
                <div
                  className={`w-4 h-4 rounded-full border-2 transition-all flex items-center justify-center ${
                    active
                      ? 'bg-blue-500 border-white scale-125 shadow-lg shadow-blue-500/50'
                      : past
                      ? 'bg-blue-600 border-blue-400'
                      : 'bg-slate-900 border-slate-700 hover:border-slate-500'
                  }`}
                />

                <span
                  className={`mt-1.5 text-[10px] font-mono transition-colors ${
                    active
                      ? 'text-white font-bold'
                      : past
                      ? 'text-blue-300'
                      : 'text-slate-500 group-hover:text-slate-400'
                  }`}
                >
                  {stepLabel}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

