#!/bin/bash
# macOS XQuartz Display Setup Script
# This script prepares XQuartz for Docker containers on macOS

set -e

echo "🍎 Setting up XQuartz display for macOS..."

# Check if XQuartz is installed
if ! command -v xquartz &> /dev/null && ! [ -d "/Applications/Utilities/XQuartz.app" ]; then
    echo "❌ ERROR: XQuartz is not installed!"
    echo "Please install XQuartz from: https://www.xquartz.org/"
    echo "Or use Homebrew: brew install --cask xquartz"
    exit 1
fi

# Check if XQuartz is running
if ! pgrep -x "Xquartz" > /dev/null; then
    echo "Starting XQuartz..."
    open -a XQuartz
    echo "⏳ Waiting for XQuartz to start (10 seconds)..."
    sleep 10
fi

# Get the host IP for Docker
HOST_IP=$(ifconfig en0 | grep "inet " | awk '{print $2}')
if [ -z "$HOST_IP" ]; then
    # Try with en1 if en0 doesn't have an IP
    HOST_IP=$(ifconfig en1 | grep "inet " | awk '{print $2}')
fi

if [ -z "$HOST_IP" ]; then
    echo "⚠️  WARNING: Could not detect host IP. Using host.docker.internal"
    export DISPLAY="host.docker.internal:0"
else
    export DISPLAY="$HOST_IP:0"
fi

# Allow connections from localhost
echo "Granting Docker containers access to XQuartz..."
xhost + "$HOST_IP" > /dev/null 2>&1 || true
xhost + 127.0.0.1 > /dev/null 2>&1 || true

# Create .docker.xauth for macOS
XAUTH_FILE="${HOME}/.docker.xauth"

# Remove existing xauth file if it has permission issues
if [ -f "$XAUTH_FILE" ]; then
    echo "Removing existing X authorization file to avoid lock issues..."
    rm -f "$XAUTH_FILE"
fi

# Create fresh xauth file with proper permissions
echo "Creating X authorization file: $XAUTH_FILE"
touch "$XAUTH_FILE"
chmod 600 "$XAUTH_FILE"

# Add X authorization entries - use full path instead of ~ to avoid lock issues
if xauth nlist "$DISPLAY" 2>/dev/null | sed -e 's/^..../ffff/' | xauth -f "$XAUTH_FILE" nmerge - 2>&1 | grep -v "already exists"; then
    echo "X authorization entries added successfully"
else
    echo "Warning: Could not add X authorization entries (this may be normal if no X session exists yet)"
fi

echo "✅ XQuartz display setup completed successfully!"
echo "   DISPLAY: $DISPLAY"
echo "   XAUTHORITY: $XAUTH_FILE"
echo ""
echo "⚠️  NOTE: Make sure 'Allow connections from network clients' is enabled in"
echo "   XQuartz -> Preferences -> Security"
