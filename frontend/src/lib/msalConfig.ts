import { Configuration, LogLevel } from "@azure/msal-browser";

/**
 * MSAL Configuration
 * 
 * To configure this for your Azure AD tenant:
 * 1. Register an app in Azure AD (Portal > App registrations > New registration)
 * 2. Set the redirect URI to http://localhost:3000 (for development)
 * 3. Copy the Application (client) ID and Directory (tenant) ID
 * 4. Replace the values below or set environment variables
 */

export const msalConfig: Configuration = {
  auth: {
    clientId: process.env.NEXT_PUBLIC_AZURE_AD_CLIENT_ID || "YOUR_CLIENT_ID",
    authority: `https://login.microsoftonline.com/${process.env.NEXT_PUBLIC_AZURE_AD_TENANT_ID || "common"}`,
    redirectUri: typeof window !== "undefined" ? window.location.origin : "http://localhost:3000",
    postLogoutRedirectUri: typeof window !== "undefined" ? window.location.origin : "http://localhost:3000",
  },
  cache: {
    cacheLocation: "sessionStorage",
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      loggerCallback: (level, message, containsPii) => {
        if (containsPii) return;
        switch (level) {
          case LogLevel.Error:
            console.error(message);
            break;
          case LogLevel.Warning:
            console.warn(message);
            break;
          case LogLevel.Info:
            console.info(message);
            break;
          case LogLevel.Verbose:
            console.debug(message);
            break;
        }
      },
      logLevel: LogLevel.Warning,
    },
  },
};

// Scopes for the initial login - add more as needed
export const loginRequest = {
  scopes: ["User.Read"],
};

// Scopes for calling the backend API
// Option 1: If you've exposed an API scope in Azure Portal, use:
//   `api://${clientId}/access_as_user`
// Option 2: If you haven't set up API scopes, use the client ID directly
//   which will return an access token for the application itself
export const apiRequest = {
  scopes: [
    // Use openid and profile to get a proper JWT access token
    // If you've exposed API scopes, add them here
    `api://${process.env.NEXT_PUBLIC_AZURE_AD_CLIENT_ID}/access_as_user`,
  ],
};

// Scopes for Microsoft Graph API calls
export const graphConfig = {
  graphMeEndpoint: "https://graph.microsoft.com/v1.0/me",
};
