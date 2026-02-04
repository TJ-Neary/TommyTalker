#!/bin/bash
# TommyTalker Development Runner
# Runs the application in development mode

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

echo "🚀 Starting TommyTalker in development mode..."
python main.py
