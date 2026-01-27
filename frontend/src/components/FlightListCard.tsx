import { useState } from 'react';
import { Flight, LogisticsAgentState } from '@/lib/logisticsTypes';
import { RiskBadge } from './RiskBadge';

interface FlightListCardProps {
  flights: Flight[];
  selectedFlightId?: string | null;
  onSelectFlight?: (flight: Flight) => void;
  highlightRisks: boolean;
  themeColor: string;
  pageSize?: number;
  minItems?: number;
}

export function FlightListCard({ 
  flights, 
  selectedFlightId, 
  onSelectFlight, 
  highlightRisks,
  themeColor,
  pageSize = 5,
  minItems = 5
}: FlightListCardProps) {
  // Ensure we show at least minItems if available
  const effectivePageSize = Math.max(pageSize, Math.min(minItems, flights?.length || 0));
  const [currentPage, setCurrentPage] = useState(1);
  
  if (!flights || flights.length === 0) {
    return (
      <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 w-full">
        <h2 className="text-xl font-bold text-white mb-4">Flight Shipments</h2>
        <p className="text-gray-300 text-center py-8">
          No flights to display. Ask the assistant to show flight data!
        </p>
      </div>
    );
  }

  // Sort flights by date (ascending)
  const sortedFlights = [...flights].sort((a, b) => {
    const dateA = new Date(a.flightDate);
    const dateB = new Date(b.flightDate);
    return dateA.getTime() - dateB.getTime();
  });

  const totalFlights = sortedFlights.length;
  const totalPages = Math.ceil(totalFlights / effectivePageSize);
  const startIndex = (currentPage - 1) * effectivePageSize;
  const endIndex = Math.min(startIndex + effectivePageSize, totalFlights);
  const displayedFlights = sortedFlights.slice(startIndex, endIndex);

  const goToPage = (page: number) => {
    setCurrentPage(Math.max(1, Math.min(page, totalPages)));
  };

  return (
    <div className="bg-white/10 backdrop-blur-md rounded-xl p-4 w-full overflow-hidden flex flex-col flex-shrink-0">
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <h2 className="text-xl font-bold text-white">Flight Shipments</h2>
        <span className="text-sm text-gray-300 whitespace-nowrap">
          Showing {startIndex + 1}-{endIndex} of {totalFlights} flights
        </span>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-white/20">
              <th className="pb-2 pr-4 text-sm font-semibold text-gray-300">Flight #</th>
              <th className="pb-2 px-4 text-sm font-semibold text-gray-300">Date</th>
              <th className="pb-2 px-4 text-sm font-semibold text-gray-300">Route</th>
              <th className="pb-2 px-4 text-sm font-semibold text-gray-300 text-right">Utilization</th>
              <th className="pb-2 pl-4 text-sm font-semibold text-gray-300">Status</th>
            </tr>
          </thead>
          <tbody>
            {displayedFlights.map((flight, index) => {
              const isSelected = selectedFlightId === flight.id;
              const rowBgColor = highlightRisks && flight.riskLevel === 'critical' 
                ? 'bg-red-500/10' 
                : highlightRisks && flight.riskLevel === 'high'
                ? 'bg-orange-500/10'
                : isSelected 
                ? 'bg-white/10' 
                : '';
              
              // Safe number formatting with fallback
              const formatNumber = (val: number | undefined) => 
                typeof val === 'number' ? val.toLocaleString() : '—';
              
              return (
                <tr 
                  key={flight.id || `flight-${index}`}
                  onClick={() => onSelectFlight?.(flight)}
                  className={`border-b border-white/10 cursor-pointer hover:bg-white/10 transition-colors ${rowBgColor}`}
                >
                  <td className="py-2 pr-4 text-white font-medium">{flight.flightNumber || '—'}</td>
                  <td className="py-2 px-4 text-gray-300">{flight.flightDate || '—'}</td>
                  <td className="py-2 px-4 text-gray-300">
                    <span className="text-white">{flight.from || '—'}</span>
                    <span className="mx-2">→</span>
                    <span className="text-white">{flight.to || '—'}</span>
                  </td>
                  <td className="py-2 px-4 text-right">
                    <span 
                      className="font-semibold"
                      style={{ 
                        color: highlightRisks 
                          ? (flight.utilizationPercent ?? 0) > 95 ? '#ef4444' 
                            : (flight.utilizationPercent ?? 0) > 80 ? '#f97316'
                            : (flight.utilizationPercent ?? 0) < 50 ? '#3b82f6'
                            : '#22c55e'
                          : 'white'
                      }}
                    >
                      {flight.utilizationPercent ?? 0}%
                    </span>
                  </td>
                  <td className="py-2 pl-4">
                    <RiskBadge riskLevel={flight.riskLevel} size="sm" />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-white/10">
          <button
            onClick={() => goToPage(currentPage - 1)}
            disabled={currentPage === 1}
            className="px-3 py-1 text-sm rounded bg-white/10 text-gray-300 hover:bg-white/20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex-shrink-0"
          >
            ← Previous
          </button>
          
          <div className="flex items-center gap-1 overflow-hidden">
            {(() => {
              // Show limited page numbers with ellipsis
              const maxVisible = 7;
              const pages: (number | string)[] = [];
              
              if (totalPages <= maxVisible) {
                // Show all pages
                for (let i = 1; i <= totalPages; i++) pages.push(i);
              } else {
                // Always show first page
                pages.push(1);
                
                if (currentPage > 3) {
                  pages.push('...');
                }
                
                // Show pages around current
                const start = Math.max(2, currentPage - 1);
                const end = Math.min(totalPages - 1, currentPage + 1);
                
                for (let i = start; i <= end; i++) {
                  if (!pages.includes(i)) pages.push(i);
                }
                
                if (currentPage < totalPages - 2) {
                  pages.push('...');
                }
                
                // Always show last page
                if (!pages.includes(totalPages)) pages.push(totalPages);
              }
              
              return pages.map((page, idx) => (
                typeof page === 'string' ? (
                  <span key={`ellipsis-${idx}`} className="px-1 text-gray-500">...</span>
                ) : (
                  <button
                    key={page}
                    onClick={() => goToPage(page)}
                    className={`w-8 h-8 text-sm rounded transition-colors flex-shrink-0 ${
                      page === currentPage
                        ? 'bg-white/20 text-white font-semibold'
                        : 'text-gray-400 hover:bg-white/10 hover:text-white'
                    }`}
                  >
                    {page}
                  </button>
                )
              ));
            })()}
          </div>
          
          <button
            onClick={() => goToPage(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="px-3 py-1 text-sm rounded bg-white/10 text-gray-300 hover:bg-white/20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex-shrink-0"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
