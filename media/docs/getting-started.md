# Getting Started

## Prerequisites

- Azure OpenAI credentials (for the Microsoft Agent Framework agent)
- Bash shell
- uv
- Node.js 20+
- npm

It is assumed you have administrative permissions to an Azure subscription as well as the ability to register applications in Entra ID.

## Deploy Azure Infrastructure

Coming soon

## Install Dependencies

From the repository root, run:

```bash
./devsetup.sh
```

This script configures the local monorepo development environment by:
- validating prerequisites (`uv`, optional Node.js)
- installing Python runtimes (`3.11`, `3.12`, `3.13`) via `uv`
- syncing backend dependencies with `uv sync --dev`
- installing frontend dependencies in `src/frontend`
- configuring git hooks in `.githooks/`

Optional:

```bash
./devsetup.sh 3.12
```

## Register an App ID in Entra ID

This repo supports user-level authentication to the agent API, which supports enterprise security as well as documenting user feedback. The application can be created using: [create-chat-app.ps1](../../src/scripts/create-chat-app.ps1). Be sure to sign-into your Entra ID tenant using `az login` first.

## Set Environment Variables

Using the output from the application enrollment script, set up your agent credentials. The backend automatically uses Azure when the Azure env vars below are present. Create an `.env` file inside the `src/backend/api` folder with one of the following configurations:

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

Next, create a new `.env.local` file within the `src/frontend` directory and populate the values. You can use the [.env.example](../../src/frontend/.env.example) as a reference.

```env
NEXT_PUBLIC_AZURE_AD_CLIENT_ID=your-client-id-here
NEXT_PUBLIC_AZURE_AD_TENANT_ID=your-tenant-id-here
```

## Disabling Authentication (Development Only)

For local development or testing purposes, you can disable authentication entirely by setting the `AUTH_ENABLED` environment variable to `false` on both the API and frontend.

**API (.env file in the `src/backend/api` folder):**
```env
AUTH_ENABLED=false
```

**Frontend (.env.local file in the `src/frontend` folder):**
```env
NEXT_PUBLIC_AUTH_ENABLED=false
```

> [!WARNING]
> Do NOT use `AUTH_ENABLED=false` in production environments. This setting allows anonymous access to the API without any authentication or authorization checks.

## Start the Development Server

Start all services from the repository root:

```bash
npm run dev
```

This starts the full local stack:
- frontend UI (`http://localhost:3000`)
- MCP server (`http://localhost:8001`)
- A2A server (`http://localhost:5002`)
- API server (`http://localhost:8000`)

## Available Scripts

The following scripts are available from the repository root:

| Script | Description |
|--------|-------------|
| `dev` | Starts frontend, MCP, A2A, and API servers in development mode |
| `dev:debug` | Starts development servers with debug logging enabled |
| `dev:ui` | Starts only the Next.js UI server |
| `dev:agent` | Compatibility alias; prefer `dev` for the full local stack |
| `build` | Builds the Next.js application for production |
| `start` | Starts the production server |
| `lint` | Runs ESLint for code linting |
