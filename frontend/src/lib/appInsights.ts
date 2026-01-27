/**
 * Application Insights configuration for frontend telemetry.
 * 
 * This enables:
 * - Automatic correlation of all HTTP requests within a session
 * - W3C Trace Context propagation (traceparent header)
 * - Page view tracking
 * - Dependency tracking (API calls)
 * 
 * All requests to /logistics will share the same operation_Id,
 * allowing unified tracing in Application Insights.
 */

import { ApplicationInsights, DistributedTracingModes } from '@microsoft/applicationinsights-web';
import { ReactPlugin } from '@microsoft/applicationinsights-react-js';

// React plugin for Application Insights
export const reactPlugin = new ReactPlugin();

// Application Insights instance (initialized lazily)
let appInsights: ApplicationInsights | null = null;

/**
 * Initialize Application Insights with the connection string.
 * Call this once at app startup.
 */
export function initializeAppInsights(connectionString: string | undefined): ApplicationInsights | null {
  if (!connectionString) {
    console.warn('[AppInsights] No connection string provided, telemetry disabled');
    return null;
  }

  if (appInsights) {
    return appInsights; // Already initialized
  }

  appInsights = new ApplicationInsights({
    config: {
      connectionString,
      extensions: [reactPlugin],
      
      // Enable W3C Trace Context for distributed tracing
      distributedTracingMode: DistributedTracingModes.W3C,
      
      // Correlation settings
      enableCorsCorrelation: true, // Enable cross-origin correlation
      correlationHeaderExcludedDomains: [], // Include all domains
      
      // Track all fetch/XHR requests as dependencies
      enableAutoRouteTracking: true,
      enableRequestHeaderTracking: true,
      enableResponseHeaderTracking: true,
      
      // Disable some noisy features for development
      disableFetchTracking: false,
      disableAjaxTracking: false,
      
      // Session configuration - keep session alive during conversation
      sessionRenewalMs: 30 * 60 * 1000, // 30 minutes
      sessionExpirationMs: 60 * 60 * 1000, // 1 hour
    },
  });

  appInsights.loadAppInsights();
  
  // Track initial page view
  appInsights.trackPageView({ name: 'Logistics Dashboard' });

  console.log('[AppInsights] Initialized with distributed tracing enabled');
  
  return appInsights;
}

/**
 * Get the current Application Insights instance.
 */
export function getAppInsights(): ApplicationInsights | null {
  return appInsights;
}

/**
 * Track a custom event.
 */
export function trackEvent(name: string, properties?: Record<string, string>) {
  appInsights?.trackEvent({ name, properties });
}

/**
 * Track the start of a conversation/session.
 * This creates a custom dimension that can be used to correlate all traces.
 */
export function trackConversationStart(threadId: string) {
  appInsights?.trackEvent({
    name: 'ConversationStart',
    properties: {
      threadId,
      conversationId: threadId,
    },
  });
  
  // Set the thread ID as a global property for all subsequent telemetry
  appInsights?.addTelemetryInitializer((envelope) => {
    if (envelope.data) {
      (envelope.data as Record<string, unknown>)['threadId'] = threadId;
    }
    return true;
  });
}

/**
 * Get the current operation ID for manual correlation.
 */
export function getCurrentOperationId(): string | undefined {
  return appInsights?.context?.telemetryTrace?.traceID;
}
