// Logistics Agent State Types

export interface Flight {
  id: string;
  flightNumber: string;
  flightDate: string;
  from: string;
  to: string;
  currentCubicFeet: number;
  maxCubicFeet: number;
  currentPounds: number;
  maxPounds: number;
  utilizationPercent: number;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  sortTime: string;
}

export interface HistoricalPayload {
  date: string;
  cubicFeet: number;
  pounds: number;
  predicted?: boolean;
  route?: string; // e.g., "LAX → ORD"
}

// Filter criteria for dashboard filtering
// filterType is ALWAYS present - never null
export interface DashboardFilter {
  filterType: 'all' | 'route' | 'utilization' | 'risk' | 'combined';  // REQUIRED - type of filter active
  routeFrom?: string | null;       // Origin airport code (e.g., "LAX")
  routeTo?: string | null;         // Destination airport code (e.g., "ORD")
  utilizationType?: 'over' | 'near_capacity' | 'optimal' | 'under' | null;
  riskLevel?: 'low' | 'medium' | 'high' | 'critical' | null;
  dateFrom?: string | null;        // Start date (YYYY-MM-DD)
  dateTo?: string | null;          // End date (YYYY-MM-DD)
  limit?: number | null;           // Max flights to display
}

// Default filter showing all flights
export const DEFAULT_FILTER: DashboardFilter = { filterType: 'all' };

// Recommendation for risk mitigation
export interface Recommendation {
  id: string;
  text: string;
  category: 'redistribution' | 'deferral' | 'expansion' | 'consolidation' | 'optimization';
}

// Result from get_recommendations backend tool
export interface RecommendationsResult {
  flightId: string;
  flightNumber: string;
  route: string;
  riskLevel: 'high' | 'critical' | 'low';
  utilizationPercent: number;
  recommendations: Recommendation[];
  generatedAt: string;
  message?: string;  // Optional message when no recommendations needed
  error?: string;    // Optional error message
}

// Feedback payload for recommendations
export interface RecommendationFeedback {
  flightId: string;
  flightNumber: string;
  recommendationId: string;
  vote: 'up' | 'down';
}

export interface FeedbackPayload {
  flightId: string;
  flightNumber: string;
  votes: Record<string, 'up' | 'down'>;
  comment?: string;
  timestamp: string;
}

export interface LogisticsAgentState {
  flights: Flight[];
  selectedFlight: Flight | null;
  historicalData: HistoricalPayload[];
  selectedRoute: string | null; // For filtering chart by route
  viewMode: 'list' | 'detail' | 'chart';
  highlightRisks: boolean;
  maxFlights: number;
  // Dashboard filter applied via chat - ALWAYS present, never null
  activeFilter: DashboardFilter;
}

// Initial empty state - data is fetched from REST API on page load
export const initialLogisticsState: LogisticsAgentState = {
  flights: [],
  selectedFlight: null,
  historicalData: [],
  selectedRoute: null,
  viewMode: 'list',
  highlightRisks: true,
  maxFlights: 100,
  activeFilter: DEFAULT_FILTER,  // Always has a filter
};

// Data summary interface for LLM context
export interface DataSummary {
  totalFlights: number;
  riskBreakdown: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  averageUtilization: number;
  airports: string[];
  routes: string[];
}

// Helper to get risk color based on level
export function getRiskColor(riskLevel: Flight['riskLevel']): string {
  switch (riskLevel) {
    case 'low':
      return '#3b82f6'; // blue - under-utilized
    case 'medium':
      return '#22c55e'; // green - optimal
    case 'high':
      return '#f97316'; // orange - approaching capacity
    case 'critical':
      return '#ef4444'; // red - over capacity
    default:
      return '#6b7280'; // gray
  }
}

// Helper to get risk label
export function getRiskLabel(riskLevel: Flight['riskLevel']): string {
  switch (riskLevel) {
    case 'low':
      return 'Under-utilized';
    case 'medium':
      return 'Optimal';
    case 'high':
      return 'Near Capacity';
    case 'critical':
      return 'Over Capacity';
    default:
      return 'Unknown';
  }
}
