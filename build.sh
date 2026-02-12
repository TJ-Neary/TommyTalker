#!/bin/bash
# TommyTalker Build Script
# Bundles the application into a standalone macOS .app
#
# Usage:
#   ./build.sh              Build the .app bundle
#   ./build.sh --install    Build, install to /Applications, enable launch on login
#   ./build.sh --uninstall  Remove from /Applications and disable launch on login

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

APP_NAME="TommyTalker"
BUNDLE_ID="com.tommytalker.app"
LAUNCH_AGENT="$HOME/Library/LaunchAgents/$BUNDLE_ID.plist"

# ── Uninstall ────────────────────────────────────────────────────────────────

if [ "$1" = "--uninstall" ]; then
    echo "Uninstalling TommyTalker..."

    # Stop the launch agent if loaded
    if launchctl list "$BUNDLE_ID" &>/dev/null; then
        launchctl unload "$LAUNCH_AGENT" 2>/dev/null || true
        echo "  Disabled launch on login"
    fi

    # Remove LaunchAgent plist
    if [ -f "$LAUNCH_AGENT" ]; then
        rm "$LAUNCH_AGENT"
        echo "  Removed LaunchAgent"
    fi

    # Remove from Applications
    if [ -d "/Applications/$APP_NAME.app" ]; then
        rm -rf "/Applications/$APP_NAME.app"
        echo "  Removed /Applications/$APP_NAME.app"
    fi

    echo "Uninstall complete."
    exit 0
fi

# ── Build ────────────────────────────────────────────────────────────────────

echo "Building TommyTalker..."

# Check for virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
pip install pyinstaller

# Generate app icon if it doesn't exist
if [ ! -f "resources/TommyTalker.icns" ]; then
    echo "Generating app icon..."
    python scripts/generate_icon.py
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Run PyInstaller
echo "Running PyInstaller..."
pyinstaller TommyTalker.spec --noconfirm

# Check if build succeeded
if [ ! -d "dist/$APP_NAME.app" ]; then
    echo "Build failed!"
    exit 1
fi

echo ""
echo "Build successful!"
echo "App location: dist/$APP_NAME.app"

# ── Install ──────────────────────────────────────────────────────────────────

if [ "$1" = "--install" ]; then
    echo ""
    echo "Installing to /Applications..."

    # Kill running instance if any
    pkill -f "$APP_NAME.app/Contents/MacOS/$APP_NAME" 2>/dev/null || true

    # Copy to Applications (replace existing)
    rm -rf "/Applications/$APP_NAME.app"
    cp -r "dist/$APP_NAME.app" /Applications/
    echo "  Installed to /Applications/$APP_NAME.app"

    # Set up launch on login
    echo "  Configuring launch on login..."
    cp "resources/$BUNDLE_ID.plist" "$LAUNCH_AGENT"
    launchctl unload "$LAUNCH_AGENT" 2>/dev/null || true
    launchctl load "$LAUNCH_AGENT"
    echo "  Launch on login enabled"

    echo ""
    echo "Installation complete! TommyTalker will:"
    echo "  - Run from /Applications/TommyTalker.app"
    echo "  - Start automatically on login"
    echo "  - Live in the menu bar (no Dock icon)"
    echo ""
    echo "To start now:  open /Applications/$APP_NAME.app"
    echo "To uninstall:  ./build.sh --uninstall"
else
    echo ""
    echo "To run:     open dist/$APP_NAME.app"
    echo "To install: ./build.sh --install"
fi
