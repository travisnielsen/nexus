#!/bin/bash

# Navigate to the agent directory
cd "$(dirname "$0")/../backend" || exit 1

# Install dependencies and create virtual environment using uv
uv sync
