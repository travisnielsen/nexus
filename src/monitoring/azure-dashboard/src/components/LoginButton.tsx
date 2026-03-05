import { useMsal } from '@azure/msal-react'
import { logAnalyticsScopes } from '../lib/msalConfig'

export function LoginButton() {
  const { instance } = useMsal()

  const handleLogin = () => {
    // Use redirect instead of popup to avoid CORS issues
    instance.loginRedirect(logAnalyticsScopes)
  }

  return (
    <button
      onClick={handleLogin}
      className="px-6 py-3 bg-vscode-accent hover:bg-blue-600 text-white rounded-lg font-medium transition-colors"
    >
      Sign in with Microsoft
    </button>
  )
}

export function LogoutButton() {
  const { instance, accounts } = useMsal()

  const handleLogout = () => {
    // Use redirect instead of popup to avoid CORS issues
    instance.logoutRedirect({
      postLogoutRedirectUri: '/',
    })
  }

  const account = accounts[0]

  return (
    <div className="flex items-center gap-2">
      {account && (
        <span className="text-xs text-vscode-muted truncate max-w-32">
          {account.username}
        </span>
      )}
      <button
        onClick={handleLogout}
        className="px-3 py-1 text-xs text-vscode-muted hover:text-white hover:bg-red-600/20 rounded transition-colors"
      >
        Sign out
      </button>
    </div>
  )
}
