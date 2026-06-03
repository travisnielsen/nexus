"use client";

import { MsalProvider } from "@azure/msal-react";
import { PublicClientApplication, EventType, EventMessage, AuthenticationResult } from "@azure/msal-browser";
import { msalConfig } from "@/lib/msalConfig";
import { useEffect, useState } from "react";

export function MsalAuthProvider({ children }: { children: React.ReactNode }) {
  const [msalInstance, setMsalInstance] = useState<PublicClientApplication | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    // This component is client-only, but guard anyway so module evaluation
    // never attempts browser APIs in SSR contexts.
    if (typeof window === "undefined") {
      return;
    }

    const initializeMsal = async () => {
      const instance = new PublicClientApplication(msalConfig);
      await instance.initialize();
      
      // Handle redirect response
      await instance.handleRedirectPromise();

      // Set active account if there is one
      const accounts = instance.getAllAccounts();
      if (accounts.length > 0) {
        instance.setActiveAccount(accounts[0]);
      }

      // Listen for sign-in events
      instance.addEventCallback((event: EventMessage) => {
        if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
          const payload = event.payload as AuthenticationResult;
          instance.setActiveAccount(payload.account);
        }
      });

      setMsalInstance(instance);
      setIsInitialized(true);
    };

    initializeMsal();
  }, []);

  if (!isInitialized || !msalInstance) {
    return null; // Or a loading spinner
  }

  return (
    <MsalProvider instance={msalInstance}>
      {children}
    </MsalProvider>
  );
}
