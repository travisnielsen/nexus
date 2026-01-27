import { useState, useEffect, useCallback } from 'react';
import { Flight, HistoricalPayload, DataSummary } from './logisticsTypes';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Check if auth is enabled
const isAuthEnabled = process.env.NEXT_PUBLIC_AUTH_ENABLED === 'true';

export interface FlightsResponse {
  flights: Flight[];
  total: number;
  limit: number;
  offset: number;
}

export interface HistoricalResponse {
  historicalData: HistoricalPayload[];
  routes: string[];
}

export interface UseLogisticsDataResult {
  // Data
  flights: Flight[];
  historicalData: HistoricalPayload[];
  summary: DataSummary | null;
  
  // Loading states
  isLoading: boolean;
  isLoadingFlights: boolean;
  isLoadingHistorical: boolean;
  
  // Error state
  error: string | null;
  
  // Refetch functions
  refetchFlights: (params?: FetchFlightsParams) => Promise<Flight[]>;
  refetchHistorical: (route?: string) => Promise<HistoricalPayload[]>;
  refetchSummary: () => Promise<DataSummary | null>;
  
  // Total count
  totalFlights: number;
}

export interface FetchFlightsParams {
  limit?: number;
  offset?: number;
  riskLevel?: 'low' | 'medium' | 'high' | 'critical';
  utilization?: 'over' | 'near_capacity' | 'optimal' | 'under';
  routeFrom?: string;
  routeTo?: string;
  dateFrom?: string;  // YYYY-MM-DD
  dateTo?: string;    // YYYY-MM-DD
  sortBy?: string;
  sortDesc?: boolean;
}

/**
 * Custom hook for fetching logistics data from REST API.
 * Loads initial data on mount and provides refetch functions for updates.
 * @param initialLimit - Maximum number of flights to fetch initially
 * @param accessToken - Optional access token for authenticated requests
 */
export function useLogisticsData(initialLimit: number = 100, accessToken?: string | null): UseLogisticsDataResult {
  const [flights, setFlights] = useState<Flight[]>([]);
  const [historicalData, setHistoricalData] = useState<HistoricalPayload[]>([]);
  const [summary, setSummary] = useState<DataSummary | null>(null);
  const [totalFlights, setTotalFlights] = useState(0);
  
  const [isLoadingFlights, setIsLoadingFlights] = useState(true);
  const [isLoadingHistorical, setIsLoadingHistorical] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Build headers with optional auth
  const getHeaders = useCallback((): HeadersInit => {
    const headers: HeadersInit = {};
    if (accessToken && isAuthEnabled) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }
    return headers;
  }, [accessToken]);

  // Fetch flights with optional filtering/pagination
  const fetchFlights = useCallback(async (params: FetchFlightsParams = {}): Promise<Flight[]> => {
    const {
      limit = initialLimit,
      offset = 0,
      riskLevel,
      utilization,
      routeFrom,
      routeTo,
      dateFrom,
      dateTo,
      sortBy = 'utilizationPercent',
      sortDesc = true,
    } = params;

    const queryParams = new URLSearchParams();
    queryParams.set('limit', limit.toString());
    queryParams.set('offset', offset.toString());
    queryParams.set('sort_by', sortBy);
    queryParams.set('sort_desc', sortDesc.toString());
    
    if (riskLevel) queryParams.set('risk_level', riskLevel);
    if (utilization) queryParams.set('utilization', utilization);
    if (routeFrom) queryParams.set('route_from', routeFrom);
    if (routeTo) queryParams.set('route_to', routeTo);
    if (dateFrom) queryParams.set('date_from', dateFrom);
    if (dateTo) queryParams.set('date_to', dateTo);

    setIsLoadingFlights(true);
    try {
      const response = await fetch(`${API_BASE_URL}/logistics/data/flights?${queryParams}`, {
        headers: getHeaders(),
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch flights: ${response.statusText}`);
      }
      const data: FlightsResponse = await response.json();
      setFlights(data.flights);
      setTotalFlights(data.total);
      setError(null);
      return data.flights;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch flights';
      setError(message);
      console.error('[useLogisticsData] Error fetching flights:', err);
      return [];
    } finally {
      setIsLoadingFlights(false);
    }
  }, [initialLimit, getHeaders]);

  // Fetch historical data with optional route filter
  const fetchHistorical = useCallback(async (route?: string): Promise<HistoricalPayload[]> => {
    const queryParams = new URLSearchParams();
    if (route) queryParams.set('route', route);

    setIsLoadingHistorical(true);
    try {
      const url = queryParams.toString() 
        ? `${API_BASE_URL}/logistics/data/historical?${queryParams}`
        : `${API_BASE_URL}/logistics/data/historical`;
      const response = await fetch(url, {
        headers: getHeaders(),
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch historical data: ${response.statusText}`);
      }
      const data: HistoricalResponse = await response.json();
      setHistoricalData(data.historicalData);
      setError(null);
      return data.historicalData;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch historical data';
      setError(message);
      console.error('[useLogisticsData] Error fetching historical:', err);
      return [];
    } finally {
      setIsLoadingHistorical(false);
    }
  }, [getHeaders]);

  // Fetch data summary for LLM context
  const fetchSummary = useCallback(async (): Promise<DataSummary | null> => {
    try {
      const response = await fetch(`${API_BASE_URL}/logistics/data/summary`, {
        headers: getHeaders(),
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch summary: ${response.statusText}`);
      }
      const data: DataSummary = await response.json();
      setSummary(data);
      return data;
    } catch (err) {
      console.error('[useLogisticsData] Error fetching summary:', err);
      return null;
    }
  }, [getHeaders]);

  // Initial data load on mount
  useEffect(() => {
    const loadInitialData = async () => {
      console.log('[useLogisticsData] Loading initial data...');
      
      // Fetch all data in parallel
      await Promise.all([
        fetchFlights({ limit: initialLimit, sortBy: 'utilizationPercent', sortDesc: true }),
        fetchHistorical(),
        fetchSummary(),
      ]);
      
      console.log('[useLogisticsData] Initial data loaded');
    };

    loadInitialData();
  }, [fetchFlights, fetchHistorical, fetchSummary, initialLimit]);

  const isLoading = isLoadingFlights || isLoadingHistorical;

  return {
    flights,
    historicalData,
    summary,
    isLoading,
    isLoadingFlights,
    isLoadingHistorical,
    error,
    refetchFlights: fetchFlights,
    refetchHistorical: fetchHistorical,
    refetchSummary: fetchSummary,
    totalFlights,
  };
}
