import { Configuration, LogLevel } from '@azure/msal-browser'

/**
 * MSAL Configuration for Azure AD authentication.
 * 
 * Required environment variables (set in .env.local):
 * - VITE_AZURE_CLIENT_ID: Your Azure AD app registration client ID
 * - VITE_AZURE_TENANT_ID: Your Azure AD tenant ID
 * 
 * Your Azure AD app registration needs:
 * - API permissions: Log Analytics API (or Microsoft.OperationalInsights)
 *   - Data.Read scope for Log Analytics workspace queries
 * - Redirect URI: http://localhost:5173 (for development)
 */

const clientId = import.meta.env.VITE_AZURE_CLIENT_ID || ''
const tenantId = import.meta.env.VITE_AZURE_TENANT_ID || ''

export const msalConfig: Configuration = {
  auth: {
    clientId,
    authority: `https://login.microsoftonline.com/${tenantId}`,
    redirectUri: window.location.origin,
    postLogoutRedirectUri: window.location.origin,
    navigateToLoginRequestUrl: true,
  },
  cache: {
    cacheLocation: 'sessionStorage',
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      loggerCallback: (level, message, containsPii) => {
        if (containsPii) return
        switch (level) {
          case LogLevel.Error:
            console.error(message)
            break
          case LogLevel.Warning:
            console.warn(message)
            break
          case LogLevel.Info:
            console.info(message)
            break
          case LogLevel.Verbose:
            console.debug(message)
            break
        }
      },
      logLevel: LogLevel.Warning,
    },
  },
}

// Scopes required for Log Analytics API
export const logAnalyticsScopes = {
  scopes: ['https://api.loganalytics.io/.default'],
}

// Scopes required for Application Insights API (alternative)
export const appInsightsScopes = {
  scopes: ['https://api.applicationinsights.io/.default'],
}
