import { HistoricalPayload } from '@/lib/logisticsTypes';

interface HistoricalChartProps {
  data: HistoricalPayload[];
  title?: string;
  themeColor: string;
  selectedRoute?: string | null;
  fillHeight?: boolean;
}

export function HistoricalChart({ data, title = "Payload History & Predictions", themeColor, selectedRoute, fillHeight = false }: HistoricalChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className={`bg-white/10 backdrop-blur-md rounded-xl p-6 w-full min-h-[400px] ${fillHeight ? 'flex-1 flex flex-col' : ''}`}>
        <h2 className="text-xl font-bold text-white mb-4">{title}</h2>
        <p className="text-gray-300 text-center py-8">
          No historical data available. Ask about payload history for a flight!
        </p>
      </div>
    );
  }

  // Find max values for scaling
  const maxPounds = Math.max(...data.map(d => d.pounds));
  const maxCubicFeet = Math.max(...data.map(d => d.cubicFeet));
  const maxValue = Math.max(maxPounds, maxCubicFeet);

  return (
    <div className={`bg-white/10 backdrop-blur-md rounded-xl p-6 w-full min-h-[400px] ${fillHeight ? 'flex-1 flex flex-col min-h-0' : ''}`}>
      <div className="flex items-center justify-between mb-2 flex-shrink-0">
        <div>
          <h2 className="text-xl font-bold text-white">{title}</h2>
          <p className="text-sm text-gray-400 mt-1">
            {selectedRoute ? (
              <span>Route: <span className="text-cyan-300 font-medium">{selectedRoute}</span></span>
            ) : (
              <span>All Routes (Aggregate)</span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: themeColor }} />
            <span className="text-gray-300">Pounds</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-cyan-400" />
            <span className="text-gray-300">Cubic Ft</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-white/30 border border-dashed border-white" />
            <span className="text-gray-300">Predicted</span>
          </div>
        </div>
      </div>

      {/* Chart Container */}
      <div className={`relative ${fillHeight ? 'flex-1 min-h-0 flex flex-col' : ''}`}>
        {/* Y-axis labels */}
        <div className={`absolute left-0 top-0 w-12 flex flex-col justify-between text-xs text-gray-400 ${fillHeight ? 'bottom-8' : 'bottom-8'}`} style={fillHeight ? {} : { height: '180px' }}>
          <span>{maxValue.toLocaleString()}</span>
          <span>{(maxValue * 0.75).toLocaleString()}</span>
          <span>{(maxValue * 0.5).toLocaleString()}</span>
          <span>{(maxValue * 0.25).toLocaleString()}</span>
          <span>0</span>
        </div>

        {/* Bars Container */}
        <div className={`ml-14 overflow-x-auto ${fillHeight ? 'flex-1 min-h-0' : ''}`}>
          <div className={`flex items-end justify-around w-full ${fillHeight ? 'h-full pb-8' : ''}`} style={fillHeight ? {} : { height: '220px' }}>
            {data.map((point, index) => {
              // For fillHeight mode, we use percentage-based heights
              const heightPercent = (value: number) => `${(value / maxValue) * 100}%`;
              // For fixed mode, use pixel heights
              const heightPx = (value: number) => `${(value / maxValue) * 180}px`;
              
              return (
                <div key={index} className="flex flex-col items-center h-full justify-end">
                  {/* Bars group */}
                  <div className={`flex items-end gap-1 ${fillHeight ? 'flex-1 min-h-0' : ''}`} style={fillHeight ? {} : { height: '180px' }}>
                    {/* Pounds bar */}
                    <div 
                      className={`w-6 rounded-t transition-all duration-300 ${point.predicted ? 'border-2 border-dashed border-white/50' : ''}`}
                      style={{ 
                        height: fillHeight ? heightPercent(point.pounds) : heightPx(point.pounds),
                        backgroundColor: point.predicted ? `${themeColor}80` : themeColor,
                      }}
                      title={`${point.pounds.toLocaleString()} lbs`}
                    />
                    {/* Cubic Feet bar */}
                    <div 
                      className={`w-6 rounded-t transition-all duration-300 ${point.predicted ? 'border-2 border-dashed border-white/50' : ''}`}
                      style={{ 
                        height: fillHeight ? heightPercent(point.cubicFeet) : heightPx(point.cubicFeet),
                        backgroundColor: point.predicted ? 'rgba(34, 211, 238, 0.5)' : '#22d3ee',
                      }}
                      title={`${point.cubicFeet.toLocaleString()} cu ft`}
                    />
                  </div>
                  {/* Date label */}
                  <span className={`text-xs ${point.predicted ? 'text-cyan-300' : 'text-gray-400'} whitespace-nowrap h-5 mt-2 flex-shrink-0`}>
                    {point.predicted && <span className="mr-1">📊</span>}
                    {point.date}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Grid lines */}
        <div className={`absolute left-14 right-0 top-0 pointer-events-none ${fillHeight ? 'bottom-8' : ''}`} style={fillHeight ? {} : { height: '180px' }}>
          {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => (
            <div 
              key={i}
              className="absolute w-full border-t border-white/10"
              style={{ bottom: `${ratio * 100}%` }}
            />
          ))}
        </div>
      </div>

      {/* Summary Stats */}
      <div className="mt-4 pt-4 border-t border-white/20 grid grid-cols-4 gap-4 text-center flex-shrink-0">
        <div>
          <p className="text-lg font-bold text-white">
            {Math.round(data.filter(d => !d.predicted).reduce((a, b) => a + b.pounds, 0) / data.filter(d => !d.predicted).length).toLocaleString()}
          </p>
          <p className="text-xs text-gray-400">Avg Lbs (Historical)</p>
        </div>
        <div>
          <p className="text-lg font-bold text-white">
            {Math.round(data.filter(d => !d.predicted).reduce((a, b) => a + b.cubicFeet, 0) / data.filter(d => !d.predicted).length).toLocaleString()}
          </p>
          <p className="text-xs text-gray-400">Avg Cu Ft (Historical)</p>
        </div>
        <div>
          <p className="text-lg font-bold text-cyan-300">
            {data.filter(d => d.predicted).length}
          </p>
          <p className="text-xs text-gray-400">Predicted Days</p>
        </div>
        <div>
          <p className="text-lg font-bold text-cyan-300">
            {data.filter(d => d.predicted).length > 0 
              ? Math.round(data.filter(d => d.predicted).reduce((a, b) => a + b.pounds, 0) / data.filter(d => d.predicted).length).toLocaleString()
              : 'N/A'}
          </p>
          <p className="text-xs text-gray-400">Predicted Avg Lbs</p>
        </div>
      </div>
    </div>
  );
}
