#!/bin/bash
# TommyTalker Development Runner
# Runs the application in development mode

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for virtual environment
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -e .
    pip install -r requirements-dev.txt
elif [ -d "venv" ]; then
    source venv/bin/activate
else
    source .venv/bin/activate
fi

echo "Starting TommyTalker in development mode..."
PYTHONPATH=src python -m tommy_talker.main
