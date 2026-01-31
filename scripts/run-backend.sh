#!/bin/bash

# Run all backend services concurrently

BACKEND_DIR="$(dirname "$0")/../backend"

echo "Starting all backend services..."

# Start MCP server (port 8001)
echo "Starting MCP server on port 8001..."
(cd "$BACKEND_DIR/mcp" && uv run uvicorn main:rest_app --host 0.0.0.0 --port 8001 --reload) &
MCP_PID=$!

# Start A2A agent (port 5002)
echo "Starting A2A agent on port 5002..."
(cd "$BACKEND_DIR/agent-a2a" && uv run uvicorn main:app --host 0.0.0.0 --port 5002 --reload) &
A2A_PID=$!

# Wait for dependencies to start
sleep 2

# Start API server (port 8000)
echo "Starting API server on port 8000..."
(cd "$BACKEND_DIR/api" && uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload) &
API_PID=$!

echo ""
echo "All services started:"
echo "  - MCP Server:  http://localhost:8001 (PID: $MCP_PID)"
echo "  - A2A Agent:   http://localhost:5002 (PID: $A2A_PID)"
echo "  - API Server:  http://localhost:8000 (PID: $API_PID)"
echo ""
echo "Press Ctrl+C to stop all services"

# Handle cleanup on exit
cleanup() {
    echo ""
    echo "Stopping all services..."
    kill $MCP_PID $A2A_PID $API_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for all processes
wait
