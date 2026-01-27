# Logistics MCP Server (HTTP Transport)

An MCP (Model Context Protocol) server that exposes logistics flight data via HTTP.
This server provides both MCP protocol endpoints (for AI agents) and REST API endpoints (for direct HTTP access).

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│  Backend API    │────▶│  MCP Server     │
│   (Next.js)     │     │  (FastAPI)      │     │  (This Server)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │                        │
                              ▼                        │
                        ┌─────────────────┐           │
                        │  Agent Tools    │───────────┘
                        │  (via HTTP)     │
                        └─────────────────┘
```

## Endpoints

### REST API (Direct HTTP Access)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/flights` | GET | Get flights with filtering and pagination |
| `/api/flights/{flight_id}` | GET | Get a specific flight |
| `/api/summary` | GET | Get flight statistics summary |
| `/api/historical` | GET | Get historical payload data with predictions |
| `/api/predictions` | GET | Get predicted payload data for future flights |
| `/api/routes` | GET | Get list of available routes with statistics |

### MCP Protocol (For AI Agents)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/sse` | GET | SSE stream for MCP messages |
| `/mcp/messages/` | POST | Post MCP messages |

## MCP Tools Provided

| Tool | Description |
|------|-------------|
| `get_tables` | Get list of all DuckDB tables and their schemas |
| `query_data` | Run SQL queries against the flight data tables |

## DuckDB Tables

The server loads data into DuckDB for SQL query capabilities:

| Table | Description |
|-------|-------------|
| `flights` | Current flight data (id, flightNumber, flightDate, origin, destination, currentPounds, maxPounds, currentCubicFeet, maxCubicFeet, utilizationPercent, riskLevel, sortTime) |
| `historical_data` | Historical and predicted payload data (date, route, pounds, cubicFeet, predicted) |
| `oneview` | OneView integration data |
| `utilization` | Utilization tracking data |

## Setup

```bash
cd mcp
uv sync
```

## Running

### HTTP Server (Default)

```bash
uv run main.py
```

The server starts on `http://localhost:8001` by default.

### Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_HOST` | `0.0.0.0` | Host to bind to |
| `MCP_PORT` | `8001` | Port to listen on |
| `AUTH_ENABLED` | `false` | Set to `true` to enable authentication |
| `AZURE_AD_TENANT_ID` | | Azure AD tenant ID for authentication |
| `AZURE_AD_CLIENT_ID` | | App Registration client ID (token audience) |
| `AZURE_AD_APP_ID_URI` | | Optional: Custom App ID URI (defaults to `api://<client-id>`) |

Create a `.env` file from the example:

```bash
cp .env.example .env
# Edit .env with your values
```

## Authentication

The MCP server supports Azure AD (Entra ID) authentication. When enabled, all `/api/*` endpoints require a valid JWT bearer token.

### Setup

1. **Create an App Registration** in Azure AD for the MCP server
2. **Define an API scope** (e.g., `api://<client-id>/Flights.Read`)
3. **Configure the backend** as an authorized client application
4. **Set environment variables**:

   ```env
   AZURE_AD_TENANT_ID=<your-tenant-id>
   AZURE_AD_CLIENT_ID=<your-client-id>
   AUTH_ENABLED=true
   ```

### Public Endpoints

The following endpoints do not require authentication:
- `/health` - Health check endpoint

### Token Validation

The server validates:
- Token signature (via JWKS from Azure AD)
- Token issuer (`iss` claim)
- Token audience (`aud` claim - must match CLIENT_ID or App ID URI)
- Token expiration (`exp` claim)

### Testing with Authentication

```bash
# Get an access token (using Azure CLI)
TOKEN=$(az account get-access-token --resource api://<client-id> --query accessToken -o tsv)

# Make authenticated request
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8001/api/flights"
```

## Testing

### REST API

```bash
# Health check
curl http://localhost:8001/health

# Get all flights (first 10)
curl "http://localhost:8001/api/flights?limit=10"

# Get high-risk flights
curl "http://localhost:8001/api/flights?risk_level=high"

# Get over-utilized flights
curl "http://localhost:8001/api/flights?utilization=over"

# Get flights from LAX
curl "http://localhost:8001/api/flights?route_from=LAX"

# Get a specific flight
curl "http://localhost:8001/api/flights/LAX-ORD-1001"

# Get summary statistics
curl http://localhost:8001/api/summary

# Get historical data (last 7 days with predictions)
curl "http://localhost:8001/api/historical?days=7"

# Get historical data for a specific route
curl "http://localhost:8001/api/historical?days=7&route=LAX-ORD"

# Get predictions only
curl "http://localhost:8001/api/predictions?days=5"

# Get available routes with statistics
curl http://localhost:8001/api/routes
```

### MCP Inspector

```bash
npx @modelcontextprotocol/inspector
# Then connect to: http://localhost:8001/mcp/sse
```

## Query Parameters

### `/api/flights`

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | int | Max flights to return (1-200, default 100) |
| `offset` | int | Number of flights to skip |
| `risk_level` | string | Filter: `low`, `medium`, `high`, `critical` |
| `utilization` | string | Filter: `under`, `optimal`, `near_capacity`, `over` |
| `route_from` | string | Origin airport code (e.g., `LAX`) |
| `route_to` | string | Destination airport code (e.g., `ORD`) |
| `date_from` | string | Start date (YYYY-MM-DD) |
| `date_to` | string | End date (YYYY-MM-DD) |
| `sort_by` | string | Field to sort by (default: `utilizationPercent`) |
| `sort_desc` | bool | Sort descending (default: `true`) |

### `/api/historical`

| Parameter | Type | Description |
|-----------|------|-------------|
| `days` | int | Number of historical days to retrieve (default: 7) |
| `route` | string | Optional route filter (e.g., `LAX-ORD`, `LAX → ORD`) |
| `include_predictions` | bool | Include prediction data (default: `true`) |

### `/api/predictions`

| Parameter | Type | Description |
|-----------|------|-------------|
| `days` | int | Number of prediction days to retrieve (default: 7) |
| `route` | string | Optional route filter (e.g., `LAX-ORD`) |

## Docker

### Build

```bash
docker build -t logistics-mcp-server .
```

### Run

```bash
# Without authentication
docker run -p 8001:8001 logistics-mcp-server

# With authentication (using env file)
docker run -p 8001:8001 --env-file .env logistics-mcp-server

# With authentication (inline)
docker run -p 8001:8001 \
  -e AUTH_ENABLED=true \
  -e AZURE_AD_TENANT_ID=<your-tenant-id> \
  -e AZURE_AD_CLIENT_ID=<your-client-id> \
  logistics-mcp-server
```
