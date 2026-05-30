#!/bin/bash

# Get absolute path to the backend directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"

echo "Setting up backend Python projects..."

# Install dependencies for each backend project
for project in logistics logistics-data recommendations; do
    echo ""
    echo "=== Setting up $project ==="
    (cd "$BACKEND_DIR/$project" && uv sync) || { echo "Failed to set up $project"; exit 1; }
done

echo ""
echo "✅ All backend projects set up successfully"
