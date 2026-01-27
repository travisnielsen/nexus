"use client";

import { useEffect } from "react";
import { MsalAuthProvider } from "@/components/MsalAuthProvider";
import { initializeAppInsights } from "@/lib/appInsights";

/**
 * Root providers for the application.
 * Note: CopilotKit is NOT included here - each page should wrap its content
 * with AuthenticatedCopilotKit (or NoAuthCopilotKit) to specify which agent to use.
 * 
 * When NEXT_PUBLIC_AUTH_ENABLED=false, MSAL provider is skipped.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  // Check if authentication is enabled via environment variable
  const isAuthEnabled = process.env.NEXT_PUBLIC_AUTH_ENABLED === "true";

  // Initialize Application Insights for distributed tracing
  useEffect(() => {
    const connectionString = process.env.NEXT_PUBLIC_APPINSIGHTS_CONNECTION_STRING;
    if (connectionString) {
      initializeAppInsights(connectionString);
    }
  }, []);

  // Skip MSAL provider when auth is disabled
  if (!isAuthEnabled) {
    return <>{children}</>;
  }

  return (
    <MsalAuthProvider>
      {children}
    </MsalAuthProvider>
  );
}
