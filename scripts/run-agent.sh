#!/bin/bash

# Navigate to the agent directory
cd "$(dirname "$0")/../backend" || exit 1

# Run the agent using uv
uv run main.py
