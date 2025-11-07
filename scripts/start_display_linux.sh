#!/bin/bash
# Linux X11 Display Setup Script
# This script prepares the X11 display for Docker containers on Linux

set -e

echo "🐧 Setting up X11 display for Linux..."

# Create .docker.xauth if it doesn't exist
XAUTH_FILE="${HOME}/.docker.xauth"
if [ ! -f "$XAUTH_FILE" ]; then
    echo "Creating X authorization file: $XAUTH_FILE"
    touch "$XAUTH_FILE"
fi

# Generate X authority entry
xauth nlist "$DISPLAY" | sed -e 's/^..../ffff/' | xauth -f "$XAUTH_FILE" nmerge - 2>/dev/null || true

# Allow local Docker containers to access X server
echo "Granting Docker containers access to X11..."
xhost +local:docker > /dev/null 2>&1

echo "✅ X11 display setup completed successfully!"
echo "   DISPLAY: $DISPLAY"
echo "   XAUTHORITY: $XAUTH_FILE"
