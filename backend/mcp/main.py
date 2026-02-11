"""
Logistics MCP Server

An MCP server that exposes logistics flight data through MCP tools.
Uses DuckDB for SQL query capabilities on JSON data files.

Tools:
- get_tables: Gets the list of all tables and their schemas.
- query_data: Runs SQL queries on the flight data.

Resources:
- tables: Gets the list of all tables in the database.

REST API Endpoints:
- GET /api/flights: Get flights with filtering and pagination
- GET /api/flights/{id}: Get a specific flight by ID
- GET /api/summary: Get flight data summary
- GET /api/historical: Get historical payload data (with optional route filter)
- GET /api/predictions: Get predicted payload data for future flights
- GET /api/routes: Get list of available routes with statistics

DuckDB Tables:
- flights: Current flight data
- historical_data: Historical and predicted payload data (date, route, pounds, cubicFeet, predicted)
- oneview: OneView integration data
- utilization: Utilization tracking data

Transport: HTTP/SSE
Default URL: http://localhost:8001
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import duckdb
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse

from auth import EntraIDAuthMiddleware, is_auth_enabled, get_auth_config

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

# Server configuration
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8001"))

# Data file paths - local to MCP server
DATA_DIR = Path(__file__).parent / "data"
FLIGHTS_FILE = DATA_DIR / "flights.json"
ONEVIEW_FILE = DATA_DIR / "oneview.json"
UTILIZATION_FILE = DATA_DIR / "utilization.json"

# Historical data cache (loaded from flights.json)
_HISTORICAL_DATA_CACHE: list = []

# Cache for flight data (used by REST endpoints)
_FLIGHT_DATA_CACHE: dict = {}


class LogisticsMCP:
    """MCP server for logistics flight data using DuckDB."""

    def __init__(self):
        self._duckdb_conn: duckdb.DuckDBPyConnection | None = None

    def init(self):
        """Initialize the DuckDB connection with flight data."""
        self._get_connection()

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get or create the DuckDB connection with loaded data."""
        if self._duckdb_conn is not None:
            return self._duckdb_conn

        logger.info("Initializing DuckDB with JSON data files")
        self._duckdb_conn = duckdb.connect(":memory:")

        # Load flights data - the JSON has structure {"flights": [...]}
        if FLIGHTS_FILE.exists():
            self._duckdb_conn.execute(f"""
                CREATE TABLE flights AS 
                SELECT unnest(flights) AS flight FROM read_json_auto('{FLIGHTS_FILE}')
            """)
            # Flatten the nested structure
            self._duckdb_conn.execute("""
                CREATE OR REPLACE TABLE flights AS 
                SELECT 
                    flight.id as id,
                    flight.flightNumber as flightNumber,
                    flight.flightDate as flightDate,
                    flight."from" as origin,
                    flight."to" as destination,
                    flight.currentPounds as currentPounds,
                    flight.maxPounds as maxPounds,
                    flight.currentCubicFeet as currentCubicFeet,
                    flight.maxCubicFeet as maxCubicFeet,
                    flight.utilizationPercent as utilizationPercent,
                    flight.riskLevel as riskLevel,
                    flight.sortTime as sortTime
                FROM flights
            """)
            count = self._duckdb_conn.execute("SELECT COUNT(*) FROM flights").fetchone()
            logger.info(f"Loaded {count[0] if count else 0} flights into DuckDB")

        # Load oneview data if exists
        if ONEVIEW_FILE.exists():
            try:
                self._duckdb_conn.execute(f"""
                    CREATE TABLE oneview AS 
                    SELECT * FROM read_json_auto('{ONEVIEW_FILE}')
                """)
                count = self._duckdb_conn.execute(
                    "SELECT COUNT(*) FROM oneview"
                ).fetchone()
                logger.info(
                    f"Loaded {count[0] if count else 0} oneview records into DuckDB"
                )
            except Exception as e:
                logger.warning(f"Could not load oneview.json: {e}")

        # Load utilization data if exists
        if UTILIZATION_FILE.exists():
            try:
                self._duckdb_conn.execute(f"""
                    CREATE TABLE utilization AS 
                    SELECT * FROM read_json_auto('{UTILIZATION_FILE}')
                """)
                count = self._duckdb_conn.execute(
                    "SELECT COUNT(*) FROM utilization"
                ).fetchone()
                logger.info(
                    f"Loaded {count[0] if count else 0} utilization records into DuckDB"
                )
            except Exception as e:
                logger.warning(f"Could not load utilization.json: {e}")

        # Load historical data from flights.json (historicalData array)
        if FLIGHTS_FILE.exists():
            try:
                # Read the JSON file and extract historicalData
                with open(FLIGHTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                historical = data.get("historicalData", [])

                if historical:
                    # Create table from the historical data
                    self._duckdb_conn.execute("""
                        CREATE TABLE historical_data (
                            date VARCHAR,
                            route VARCHAR,
                            pounds INTEGER,
                            cubicFeet INTEGER,
                            predicted BOOLEAN
                        )
                    """)

                    # Insert historical data
                    for record in historical:
                        self._duckdb_conn.execute(
                            "INSERT INTO historical_data VALUES (?, ?, ?, ?, ?)",
                            [
                                record.get("date"),
                                record.get("route"),
                                record.get("pounds"),
                                record.get("cubicFeet"),
                                record.get("predicted", False),
                            ],
                        )

                    count = self._duckdb_conn.execute(
                        "SELECT COUNT(*) FROM historical_data"
                    ).fetchone()
                    logger.info(
                        f"Loaded {count[0] if count else 0} historical records into DuckDB"
                    )
            except Exception as e:
                logger.warning(f"Could not load historical data: {e}")

        return self._duckdb_conn

    def get_tables(self) -> str:
        """Gets the list of all tables and their schemas."""
        try:
            conn = self._get_connection()
            result = conn.execute("SHOW TABLES").fetchall()
            tables = [row[0] for row in result]

            # Get schema for each table
            table_info = {}
            for table in tables:
                schema = conn.execute(f"DESCRIBE {table}").fetchall()
                table_info[table] = [
                    {"column": row[0], "type": row[1]} for row in schema
                ]

            return json.dumps(
                {
                    "tables": tables,
                    "schemas": table_info,
                }
            )
        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return json.dumps({"error": str(e)})

    def query_data(self, query: str) -> str:
        """Runs SQL queries on the flight data.

        Args:
            query: SQL query to execute. Available tables: 'flights' with columns
                   (id, flightNumber, flightDate, origin, destination, currentPounds,
                   maxPounds, currentCubicFeet, maxCubicFeet, utilizationPercent,
                   riskLevel, sortTime).

        Returns:
            JSON string with columns and rows from the query result.
        """
        try:
            conn = self._get_connection()
            result = conn.execute(query)
            colnames = [desc[0] for desc in result.description]
            rows = result.fetchall()

            # Convert rows to serializable format
            serializable_rows = []
            for row in rows:
                row_data = []
                for val in row:
                    if hasattr(val, "isoformat"):
                        val = val.isoformat()
                    row_data.append(val)
                serializable_rows.append(row_data)

            return json.dumps(
                {
                    "columns": colnames,
                    "rows": serializable_rows,
                    "row_count": len(rows),
                }
            )
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return json.dumps({"error": str(e)})

    def get_tables_resource(self) -> str:
        """Gets list of tables as a resource."""
        return self.get_tables()


# ============================================================================
# REST API Functions (for direct HTTP access - used by MCP client)
# ============================================================================


def _load_flight_data() -> dict:
    """Load and cache flight data from the JSON file."""
    global _HISTORICAL_DATA_CACHE
    if not _FLIGHT_DATA_CACHE:
        logger.info(f"Loading flight data from {FLIGHTS_FILE}")
        with open(FLIGHTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Also cache historical data
            if not _HISTORICAL_DATA_CACHE:
                _HISTORICAL_DATA_CACHE = data.get("historicalData", [])
                logger.info(f"Loaded {len(_HISTORICAL_DATA_CACHE)} historical records")
            _FLIGHT_DATA_CACHE.update(data)
        logger.info(f"Loaded {len(_FLIGHT_DATA_CACHE.get('flights', []))} flights")
    return _FLIGHT_DATA_CACHE


def get_flights(
    limit: int = 100,
    offset: int = 0,
    risk_level: str | None = None,
    utilization: str | None = None,
    route_from: str | None = None,
    route_to: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_by: str = "utilizationPercent",
    sort_desc: bool = True,
) -> dict[str, Any]:
    """Get flights with filtering, sorting, and pagination."""
    data = _load_flight_data()
    all_flights = data.get("flights", [])

    # Apply filters
    filtered = all_flights

    if risk_level:
        filtered = [f for f in filtered if f.get("riskLevel") == risk_level]

    if utilization:
        if utilization == "over":
            filtered = [f for f in filtered if f.get("utilizationPercent", 0) > 95]
        elif utilization == "near_capacity":
            filtered = [
                f for f in filtered if 85 <= f.get("utilizationPercent", 0) <= 95
            ]
        elif utilization == "under":
            filtered = [f for f in filtered if f.get("utilizationPercent", 0) < 50]
        elif utilization == "optimal":
            filtered = [
                f for f in filtered if 50 <= f.get("utilizationPercent", 0) < 85
            ]

    if route_from:
        filtered = [
            f for f in filtered if f.get("from", "").upper() == route_from.upper()
        ]

    if route_to:
        filtered = [f for f in filtered if f.get("to", "").upper() == route_to.upper()]

    if date_from:
        filtered = [f for f in filtered if f.get("flightDate", "") >= date_from]

    if date_to:
        filtered = [f for f in filtered if f.get("flightDate", "") <= date_to]

    # Sort
    if sort_by and filtered:
        filtered = sorted(
            filtered,
            key=lambda x: (
                x.get(sort_by, 0)
                if isinstance(x.get(sort_by), (int, float))
                else str(x.get(sort_by, ""))
            ),
            reverse=sort_desc,
        )

    total = len(filtered)
    paginated = filtered[offset : offset + limit]

    return {
        "flights": paginated,
        "total": total,
        "query": {
            "limit": limit,
            "offset": offset,
            "risk_level": risk_level,
            "utilization": utilization,
            "route_from": route_from,
            "route_to": route_to,
            "date_from": date_from,
            "date_to": date_to,
        },
    }


def get_flight_by_id(flight_id: str) -> dict[str, Any]:
    """Get a specific flight by ID or flight number."""
    data = _load_flight_data()
    all_flights = data.get("flights", [])

    search = flight_id.upper().replace(" ", "").replace("-", "")
    for flight in all_flights:
        flight_num = flight.get("flightNumber", "").upper().replace("-", "")
        if flight.get("id") == flight_id or flight_num == search:
            return {"flight": flight}

    return {"flight": None, "error": f"Flight {flight_id} not found"}


def get_flight_summary() -> dict[str, Any]:
    """Get a summary of all available flight data."""
    data = _load_flight_data()
    flights = data.get("flights", [])

    risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    route_counts: dict[str, int] = {}
    total_utilization = 0

    for f in flights:
        risk = f.get("riskLevel", "unknown")
        if risk in risk_counts:
            risk_counts[risk] += 1

        route = f"{f.get('from', '?')} → {f.get('to', '?')}"
        route_counts[route] = route_counts.get(route, 0) + 1
        total_utilization += f.get("utilizationPercent", 0)

    avg_utilization = total_utilization / len(flights) if flights else 0

    airports = set()
    for f in flights:
        airports.add(f.get("from", ""))
        airports.add(f.get("to", ""))
    airports.discard("")

    return {
        "totalFlights": len(flights),
        "riskBreakdown": risk_counts,
        "averageUtilization": round(avg_utilization, 1),
        "uniqueRoutes": len(route_counts),
        "topRoutes": sorted(route_counts.items(), key=lambda x: x[1], reverse=True)[
            :10
        ],
        "airports": sorted(list(airports)),
        "flightsAtRisk": risk_counts["high"] + risk_counts["critical"],
        "underUtilizedFlights": risk_counts["low"],
    }


def get_historical_data(
    days: int = 7,
    route: str | None = None,
    include_predictions: bool = True,
) -> dict[str, Any]:
    """Get historical payload data with optional route filtering.

    Args:
        days: Number of historical days to retrieve (default: 7)
        route: Optional route filter (e.g., 'LAX → ORD' or 'LAX-ORD')
        include_predictions: Whether to include prediction data (default: True)

    Returns:
        Dict with historical data, predictions, and summary statistics
    """
    _load_flight_data()  # Ensure data is loaded
    all_data = _HISTORICAL_DATA_CACHE.copy()

    # Filter by route if specified
    if route:
        # Normalize route format
        normalized = (
            route.replace("-", " → ").replace("->", " → ").replace(" - ", " → ")
        )
        all_data = [d for d in all_data if d.get("route") == normalized]

    # Separate historical and predicted data
    historical = [d for d in all_data if not d.get("predicted", False)]
    predictions = [d for d in all_data if d.get("predicted", False)]

    # Sort by date (descending for historical to get most recent first)
    historical = sorted(historical, key=lambda x: x.get("date", ""), reverse=True)
    predictions = sorted(predictions, key=lambda x: x.get("date", ""))

    # Limit historical to requested number of unique days (not records)
    if historical:
        unique_dates = sorted(set(d.get("date", "") for d in historical), reverse=True)[
            :days
        ]
        historical = [d for d in historical if d.get("date", "") in unique_dates]
        # Re-sort ascending for display
        historical = sorted(historical, key=lambda x: x.get("date", ""))

    # Calculate statistics
    if historical:
        avg_pounds = sum(d.get("pounds", 0) for d in historical) // len(historical)
        avg_cubic = sum(d.get("cubicFeet", 0) for d in historical) // len(historical)
        unique_hist_dates = len(set(d.get("date", "") for d in historical))
    else:
        avg_pounds = 0
        avg_cubic = 0
        unique_hist_dates = 0

    unique_pred_dates = (
        len(set(d.get("date", "") for d in predictions)) if predictions else 0
    )

    result = {
        "historical": historical,
        "predictions": predictions if include_predictions else [],
        "summary": {
            "historicalDays": unique_hist_dates,
            "predictionDays": unique_pred_dates if include_predictions else 0,
            "averagePounds": avg_pounds,
            "averageCubicFeet": avg_cubic,
            "route": route,
        },
    }

    return result


def get_predictions(
    days: int = 7,
    route: str | None = None,
) -> dict[str, Any]:
    """Get predicted payload data for future flights.

    Args:
        days: Number of prediction days to retrieve (default: 7)
        route: Optional route filter (e.g., 'LAX → ORD')

    Returns:
        Dict with prediction data
    """
    _load_flight_data()  # Ensure data is loaded
    all_data = _HISTORICAL_DATA_CACHE.copy()

    # Filter by route if specified
    if route:
        normalized = (
            route.replace("-", " → ").replace("->", " → ").replace(" - ", " → ")
        )
        all_data = [d for d in all_data if d.get("route") == normalized]

    # Get only predictions
    predictions = [d for d in all_data if d.get("predicted", False)]
    predictions = sorted(predictions, key=lambda x: x.get("date", ""))
    predictions = predictions[:days]

    # Get unique routes in predictions
    routes = list(set(d.get("route", "") for d in predictions))

    return {
        "predictions": predictions,
        "totalPredictions": len(predictions),
        "routes": routes,
        "query": {
            "days": days,
            "route": route,
        },
    }


def get_available_routes() -> dict[str, Any]:
    """Get list of all available routes in historical data."""
    _load_flight_data()  # Ensure data is loaded

    routes: dict[str, dict] = {}
    for record in _HISTORICAL_DATA_CACHE:
        route = record.get("route", "")
        if route:
            if route not in routes:
                routes[route] = {
                    "historical_count": 0,
                    "prediction_count": 0,
                    "total_pounds": 0,
                }
            if record.get("predicted"):
                routes[route]["prediction_count"] += 1
            else:
                routes[route]["historical_count"] += 1
                routes[route]["total_pounds"] += record.get("pounds", 0)

    route_list = []
    for route, stats in routes.items():
        avg_pounds = stats["total_pounds"] // max(1, stats["historical_count"])
        route_list.append(
            {
                "route": route,
                "historicalRecords": stats["historical_count"],
                "predictionRecords": stats["prediction_count"],
                "averagePounds": avg_pounds,
            }
        )

    return {
        "routes": sorted(
            route_list, key=lambda x: x["historicalRecords"], reverse=True
        ),
        "totalRoutes": len(route_list),
    }


# ============================================================================
# REST API Endpoints (Starlette)
# ============================================================================


async def rest_get_historical(request: Request) -> JSONResponse:
    """REST endpoint for getting historical data."""
    params = request.query_params
    result = get_historical_data(
        days=int(params.get("days", 7)),
        route=params.get("route"),
        include_predictions=params.get("include_predictions", "true").lower() == "true",
    )
    return JSONResponse(result)


async def rest_get_predictions(request: Request) -> JSONResponse:
    """REST endpoint for getting predictions."""
    params = request.query_params
    result = get_predictions(
        days=int(params.get("days", 7)),
        route=params.get("route"),
    )
    return JSONResponse(result)


async def rest_get_routes(request: Request) -> JSONResponse:
    """REST endpoint for getting available routes."""
    result = get_available_routes()
    return JSONResponse(result)


async def rest_get_flights(request: Request) -> JSONResponse:
    """REST endpoint for getting flights."""
    params = request.query_params
    result = get_flights(
        limit=int(params.get("limit", 100)),
        offset=int(params.get("offset", 0)),
        risk_level=params.get("risk_level"),
        utilization=params.get("utilization"),
        route_from=params.get("route_from"),
        route_to=params.get("route_to"),
        date_from=params.get("date_from"),
        date_to=params.get("date_to"),
        sort_by=params.get("sort_by", "utilizationPercent"),
        sort_desc=params.get("sort_desc", "true").lower() == "true",
    )
    return JSONResponse(result)


async def rest_get_flight(request: Request) -> JSONResponse:
    """REST endpoint for getting a single flight."""
    flight_id = request.path_params["flight_id"]
    result = get_flight_by_id(flight_id)
    return JSONResponse(result)


async def rest_get_summary(request: Request) -> JSONResponse:
    """REST endpoint for getting flight summary."""
    result = get_flight_summary()
    return JSONResponse(result)


async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint."""
    data = _load_flight_data()
    return JSONResponse(
        {
            "status": "healthy",
            "server": "logistics-mcp",
            "transport": "http/sse",
            "flights_loaded": len(data.get("flights", [])),
            "historical_records": len(_HISTORICAL_DATA_CACHE),
            "auth_enabled": is_auth_enabled(),
        }
    )


# Create Starlette app with REST routes
rest_app = Starlette(
    debug=True,
    routes=[
        Route("/health", health_check, methods=["GET"]),
        Route("/api/flights", rest_get_flights, methods=["GET"]),
        Route("/api/flights/{flight_id:str}", rest_get_flight, methods=["GET"]),
        Route("/api/summary", rest_get_summary, methods=["GET"]),
        Route("/api/historical", rest_get_historical, methods=["GET"]),
        Route("/api/predictions", rest_get_predictions, methods=["GET"]),
        Route("/api/routes", rest_get_routes, methods=["GET"]),
    ],
)

# Add authentication middleware
rest_app.add_middleware(EntraIDAuthMiddleware)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting Logistics MCP Server on {MCP_HOST}:{MCP_PORT}")
    logger.info(f"REST API: http://{MCP_HOST}:{MCP_PORT}/api/flights")

    # Pre-load flight data
    _load_flight_data()

    uvicorn.run(rest_app, host=MCP_HOST, port=MCP_PORT)
