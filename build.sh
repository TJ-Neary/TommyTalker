#!/bin/bash
# TommyTalker Build Script
# Bundles the application into a standalone macOS .app

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Building TommyTalker..."

# Check for virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt
pip install pyinstaller

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build dist

# Run PyInstaller
echo "🔨 Running PyInstaller..."
pyinstaller TommyTalker.spec --noconfirm

# Check if build succeeded
if [ -d "dist/TommyTalker.app" ]; then
    echo ""
    echo "✅ Build successful!"
    echo "📍 App location: dist/TommyTalker.app"
    echo ""
    echo "To run the app:"
    echo "  open dist/TommyTalker.app"
    echo ""
    echo "To install to Applications:"
    echo "  cp -r dist/TommyTalker.app /Applications/"
else
    echo ""
    echo "❌ Build failed!"
    exit 1
fi
