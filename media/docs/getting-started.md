# Getting Started

## Prerequisites

- Azure OpenAI credentials (for the Microsoft Agent Framework agent)
- Python 3.12+
- uv
- Node.js 20+ 
- Any of the following package managers:
  - pnpm (recommended)
  - npm
  - yarn
  - bun

It is assumed you have administrative permissions to an Azure subscription as well as the ability to register applications in Entra ID.

## Deploy Azure Infrastructure

Coming soon

## Install Dependencies

Install dependencies using your preferred package manager:

```bash
# Using pnpm (recommended)
pnpm install

# Using npm
npm install

# Using yarn
yarn install

# Using bun
bun install
```

> **Note:** This automatically sets up the Python environment as well. If you have manual issues, you can run: `npm run install:agent`

## Register an App ID in Entra ID

This repo supports user-level authentication to the agent API, which supports enterprise security as well as documenting user feedback. The application can be created using: [create-chat-app.ps1](../../scripts/create-chat-app.ps1). Be sure to sign-into your Entra ID tenant using `az login` first.

## Set Environment Variables

Using the output from the application enrollment script, set up your agent credentials. The backend automatically uses Azure when the Azure env vars below are present. Create an `.env` file inside the `backend/api` folder with one of the following configurations:

```env
# Microsoft Foundry settings
AZURE_OPENAI_ENDPOINT=https://[your-resource].services.ai.azure.com/
AZURE_OPENAI_PROJECT_ENDPOINT=https://[your-resource].services.ai.azure.com/api/projects/[your-project]
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4o

# Entra ID Authentication
AZURE_AD_CLIENT_ID=[your-app-id]
AZURE_AD_TENANT_ID=[your-tenant-id]
```

> [!IMPORTANT]
> The Entra ID section is optional. When the two environment variables are set, the API will require a valid token issued by the source tenant with the correct target scope. If you don't require user-level authorization to the API, you can delete this section.

Next, create a new `.env.local` file within the `frontend` directory and populate the values. You can use the [.env.example](../../frontend/.env.example) as a reference.

```env
NEXT_PUBLIC_AZURE_AD_CLIENT_ID=your-client-id-here
NEXT_PUBLIC_AZURE_AD_TENANT_ID=your-tenant-id-here
```

## Disabling Authentication (Development Only)

For local development or testing purposes, you can disable authentication entirely by setting the `AUTH_ENABLED` environment variable to `false` on both the API and frontend.

**API (.env file in the `backend/api` folder):**
```env
AUTH_ENABLED=false
```

**Frontend (.env.local file in the `frontend` folder):**
```env
NEXT_PUBLIC_AUTH_ENABLED=false
```

> [!WARNING]
> Do NOT use `AUTH_ENABLED=false` in production environments. This setting allows anonymous access to the API without any authentication or authorization checks.

## Start the Development Server

The following commands can be used to start the environment locally:

```bash
# Using pnpm
pnpm dev

# Using npm
npm run dev

# Using yarn
yarn dev

# Using bun
bun run dev
```

This will start both the UI and the Microsoft Agent Framework server concurrently.

## Available Scripts

The following scripts can also be run using your preferred package manager:

| Script | Description |
|--------|-------------|
| `dev` | Starts both UI and agent servers in development mode |
| `dev:debug` | Starts development servers with debug logging enabled |
| `dev:ui` | Starts only the Next.js UI server |
| `dev:agent` | Starts only the Microsoft Agent Framework server |
| `build` | Builds the Next.js application for production |
| `start` | Starts the production server |
| `lint` | Runs ESLint for code linting |
| `install:agent` | Installs Python dependencies for the agent |
