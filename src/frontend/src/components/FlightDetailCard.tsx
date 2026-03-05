import { Flight } from '@/lib/logisticsTypes';
import { RiskBadge } from './RiskBadge';

interface FlightDetailCardProps {
  flight: Flight;
  themeColor: string;
  onClose?: () => void;
}

// Simple airplane icon
function AirplaneIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-8 h-8">
      <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
    </svg>
  );
}

// Progress bar component
function CapacityBar({ current, max, label, unit }: { current: number; max: number; label: string; unit: string }) {
  const safeMax = max || 1; // Prevent division by zero
  const safeCurrent = current ?? 0;
  const percentage = Math.min((safeCurrent / safeMax) * 100, 100);
  const isOver = safeCurrent > safeMax;
  
  const barColor = isOver 
    ? '#ef4444' 
    : percentage > 80 
    ? '#f97316' 
    : percentage < 50 
    ? '#3b82f6' 
    : '#22c55e';

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-gray-300">{label}</span>
        <span className="text-white font-medium">
          {safeCurrent.toLocaleString()} / {safeMax.toLocaleString()} {unit}
        </span>
      </div>
      <div className="h-3 bg-white/20 rounded-full overflow-hidden">
        <div 
          className="h-full rounded-full transition-all duration-500"
          style={{ 
            width: `${Math.min(percentage, 100)}%`,
            backgroundColor: barColor
          }}
        />
      </div>
      <div className="flex justify-between text-xs text-gray-400">
        <span>{percentage.toFixed(1)}% utilized</span>
        {isOver && <span className="text-red-400">⚠️ Over capacity by {(safeCurrent - safeMax).toLocaleString()} {unit}</span>}
      </div>
    </div>
  );
}

export function FlightDetailCard({ flight, themeColor, onClose }: FlightDetailCardProps) {
  return (
    <div 
      style={{ backgroundColor: themeColor }}
      className="rounded-xl shadow-xl w-full"
    >
      <div className="bg-white/20 backdrop-blur-md p-6 rounded-xl">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-white/20 rounded-xl text-white">
              <AirplaneIcon />
            </div>
            <div>
              <h3 className="text-2xl font-bold text-white">{flight.flightNumber}</h3>
              <p className="text-gray-200">
                {flight.from} → {flight.to}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <RiskBadge riskLevel={flight.riskLevel} />
            {onClose && (
              <button 
                onClick={onClose}
                className="p-2 hover:bg-white/20 rounded-lg transition-colors text-white"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {/* Sort Time & Date */}
        <div className="bg-white/10 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-gray-200">
              <span>📅</span>
              <span className="text-sm">Flight Date:</span>
              <span className="text-white font-semibold">{flight.flightDate || '—'}</span>
            </div>
            <div className="flex items-center gap-2 text-gray-200">
              <span>🕐</span>
              <span className="text-sm">Sort Time:</span>
              <span className="text-white font-semibold">{flight.sortTime}</span>
            </div>
          </div>
        </div>

        {/* Capacity Bars */}
        <div className="space-y-6">
          <CapacityBar 
            current={flight.currentPounds} 
            max={flight.maxPounds} 
            label="Weight Capacity" 
            unit="lbs"
          />
          <CapacityBar 
            current={flight.currentCubicFeet} 
            max={flight.maxCubicFeet} 
            label="Volume Capacity" 
            unit="cu ft"
          />
        </div>

        {/* Utilization Summary */}
        <div className="mt-6 pt-6 border-t border-white/20">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-3xl font-bold text-white">{flight.utilizationPercent ?? 0}%</p>
              <p className="text-sm text-gray-300">Overall Utilization</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-white">
                {Math.max(0, (flight.maxPounds ?? 0) - (flight.currentPounds ?? 0)).toLocaleString()}
              </p>
              <p className="text-sm text-gray-300">Lbs Available</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-white">
                {Math.max(0, (flight.maxCubicFeet ?? 0) - (flight.currentCubicFeet ?? 0)).toLocaleString()}
              </p>
              <p className="text-sm text-gray-300">Cu Ft Available</p>
            </div>
          </div>
        </div>

        {/* Recommendations moved to chat via get_recommendations tool */}
        {(flight.riskLevel === 'high' || flight.riskLevel === 'critical') && (
          <div className="mt-6 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
            <p className="text-sm text-amber-200 flex items-center gap-2">
              <span>⚠️</span>
              <span>This flight has elevated risk. Ask the assistant for mitigation recommendations.</span>
            </p>
          </div>
        )}

        {flight.riskLevel === 'low' && (
          <div className="mt-6 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
            <p className="text-sm text-blue-200 flex items-center gap-2">
              <span>💡</span>
              <span>This flight has available capacity. Ask the assistant for optimization suggestions.</span>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
