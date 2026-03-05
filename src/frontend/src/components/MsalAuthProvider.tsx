"use client";

import { MsalProvider } from "@azure/msal-react";
import { PublicClientApplication, EventType, EventMessage, AuthenticationResult } from "@azure/msal-browser";
import { msalConfig } from "@/lib/msalConfig";
import { useEffect, useState } from "react";

// Create the MSAL instance outside the component to avoid re-initialization
const msalInstance = new PublicClientApplication(msalConfig);

export function MsalAuthProvider({ children }: { children: React.ReactNode }) {
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    const initializeMsal = async () => {
      await msalInstance.initialize();
      
      // Handle redirect response
      await msalInstance.handleRedirectPromise();

      // Set active account if there is one
      const accounts = msalInstance.getAllAccounts();
      if (accounts.length > 0) {
        msalInstance.setActiveAccount(accounts[0]);
      }

      // Listen for sign-in events
      msalInstance.addEventCallback((event: EventMessage) => {
        if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
          const payload = event.payload as AuthenticationResult;
          msalInstance.setActiveAccount(payload.account);
        }
      });

      setIsInitialized(true);
    };

    initializeMsal();
  }, []);

  if (!isInitialized) {
    return null; // Or a loading spinner
  }

  return (
    <MsalProvider instance={msalInstance}>
      {children}
    </MsalProvider>
  );
}
