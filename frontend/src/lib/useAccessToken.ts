"use client";

import { useState, useEffect, useCallback } from "react";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionRequiredAuthError } from "@azure/msal-browser";
import { apiRequest, loginRequest } from "./msalConfig";

/**
 * Hook to acquire an access token for the backend API.
 * Returns the access token, loading state, and error if any.
 */
export function useAccessToken() {
  const { instance, accounts } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const acquireToken = useCallback(async () => {
    if (!isAuthenticated || accounts.length === 0) {
      setAccessToken(null);
      return null;
    }

    setIsLoading(true);
    setError(null);

    console.log("Acquiring token for scopes:", apiRequest.scopes);

    try {
      // Try to acquire token for the API scope first
      const response = await instance.acquireTokenSilent({
        ...apiRequest,
        account: accounts[0],
      });
      console.log("Token acquired successfully for API scope");
      setAccessToken(response.accessToken);
      return response.accessToken;
    } catch (apiScopeError) {
      console.warn("Failed to acquire token for API scope, trying fallback:", apiScopeError);
      
      // Fallback: try with basic scopes and use ID token
      try {
        const response = await instance.acquireTokenSilent({
          scopes: ["openid", "profile", "User.Read"],
          account: accounts[0],
        });
        console.log("Token acquired with fallback scopes");
        // Use the ID token if access token isn't a valid JWT
        const token = response.accessToken;
        // Check if it's a valid JWT (should have 3 parts)
        if (token && token.split('.').length === 3) {
          setAccessToken(token);
          return token;
        } else if (response.idToken) {
          console.log("Using ID token as fallback");
          setAccessToken(response.idToken);
          return response.idToken;
        }
        throw new Error("No valid token available");
      } catch (fallbackError) {
        console.error("Fallback token acquisition failed:", fallbackError);
        
        // Try interactive as last resort
        if (apiScopeError instanceof InteractionRequiredAuthError) {
          try {
            const response = await instance.acquireTokenPopup(apiRequest);
            console.log("Token acquired via popup");
            setAccessToken(response.accessToken);
            return response.accessToken;
          } catch (interactiveError) {
            console.error("Interactive token acquisition failed:", interactiveError);
            setError(interactiveError as Error);
            setAccessToken(null);
            return null;
          }
        }
        setError(apiScopeError as Error);
        setAccessToken(null);
        return null;
      }
    } finally {
      setIsLoading(false);
    }
  }, [instance, accounts, isAuthenticated]);

  // Acquire token on mount and when auth state changes
  useEffect(() => {
    acquireToken();
  }, [acquireToken]);

  return {
    accessToken,
    isLoading,
    error,
    acquireToken, // Expose this to manually refresh the token if needed
  };
}
