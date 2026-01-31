"use client";

import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { loginRequest } from "@/lib/msalConfig";

/**
 * Internal component that uses MSAL hooks.
 * Must only be rendered when MsalProvider is present.
 */
function AuthButtonWithMsal() {
  const { instance, accounts, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();

  const handleSignIn = async () => {
    // Prevent multiple concurrent login attempts
    if (inProgress !== InteractionStatus.None) {
      console.log("Login already in progress, skipping...");
      return;
    }
    
    try {
      await instance.loginPopup(loginRequest);
    } catch (error) {
      console.error("Login failed:", error);
    }
  };

  const handleSignOut = async () => {
    // Prevent logout if another interaction is in progress
    if (inProgress !== InteractionStatus.None) {
      console.log("Interaction in progress, skipping logout...");
      return;
    }
    
    try {
      await instance.logoutPopup({
        postLogoutRedirectUri: window.location.origin,
        mainWindowRedirectUri: window.location.origin,
      });
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  if (isAuthenticated && accounts.length > 0) {
    const account = accounts[0];
    const displayName = account.name || account.username || "User";
    const isInteracting = inProgress !== InteractionStatus.None;

    return (
      <button
        onClick={handleSignOut}
        disabled={isInteracting}
        className={`text-gray-300 hover:text-white transition-colors flex items-center gap-2 ${isInteracting ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <span className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white text-sm font-medium">
          {displayName.charAt(0).toUpperCase()}
        </span>
        <span>{displayName}</span>
      </button>
    );
  }

  const isInteracting = inProgress !== InteractionStatus.None;
  
  return (
    <button
      onClick={handleSignIn}
      disabled={isInteracting}
      className={`text-gray-300 hover:text-white transition-colors ${isInteracting ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      {isInteracting ? "Signing in..." : "Sign In"}
    </button>
  );
}

/**
 * Auth button component that handles sign in/out.
 * When AUTH_ENABLED=false, shows a "No Auth Mode" indicator instead.
 */
export function AuthButton() {
  // Check if authentication is enabled via environment variable
  const isAuthEnabled = process.env.NEXT_PUBLIC_AUTH_ENABLED === "true";

  // When auth is disabled, show a simple "No Auth" indicator
  if (!isAuthEnabled) {
    return (
      <span className="text-gray-400 flex items-center gap-2">
        <span className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center text-white text-sm font-medium">
          ?
        </span>
        <span>No Auth Mode</span>
      </span>
    );
  }

  return <AuthButtonWithMsal />;
}
