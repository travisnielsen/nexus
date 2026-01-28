import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { MsalProvider } from '@azure/msal-react'
import { PublicClientApplication, EventType } from '@azure/msal-browser'
import { msalConfig } from './lib/msalConfig'
import App from './App'
import './index.css'

const msalInstance = new PublicClientApplication(msalConfig)

// Initialize MSAL before rendering
async function initializeApp() {
  // Required: Initialize MSAL instance
  await msalInstance.initialize()

  // Handle redirect response after login
  await msalInstance.handleRedirectPromise()

  // Set the active account if one exists
  const accounts = msalInstance.getAllAccounts()
  if (accounts.length > 0) {
    msalInstance.setActiveAccount(accounts[0])
  }

  // Listen for login events
  msalInstance.addEventCallback((event) => {
    if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
      const payload = event.payload as { account?: { homeAccountId: string } }
      if (payload.account) {
        msalInstance.setActiveAccount(msalInstance.getAccountByHomeId(payload.account.homeAccountId))
      }
    }
  })

  // Render the app
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <MsalProvider instance={msalInstance}>
        <App />
      </MsalProvider>
    </StrictMode>,
  )
}

initializeApp().catch(console.error)
