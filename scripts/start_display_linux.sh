#!/bin/bash
# Linux X11 Display Setup Script
# This script prepares the X11 display for Docker containers on Linux

set -e

echo "🐧 Setting up X11 display for Linux..."

# Create .docker.xauth if it doesn't exist
XAUTH_FILE="${HOME}/.docker.xauth"

# If Docker created it as a directory, remove it first
if [ -d "$XAUTH_FILE" ]; then
    echo "⚠️  Removing Docker-created directory: $XAUTH_FILE"
    sudo rm -rf "$XAUTH_FILE"
fi

# Create the file (must exist BEFORE docker compose starts)
if [ ! -f "$XAUTH_FILE" ]; then
    echo "Creating X authorization file: $XAUTH_FILE"
    touch "$XAUTH_FILE"
    chmod 600 "$XAUTH_FILE"
    # Ensure ownership is correct
    chown $USER:$USER "$XAUTH_FILE" 2>/dev/null || true
else
    echo "X authorization file already exists: $XAUTH_FILE"
    # Ensure correct permissions
    chmod 600 "$XAUTH_FILE" 2>/dev/null || sudo chmod 600 "$XAUTH_FILE"
    chown $USER:$USER "$XAUTH_FILE" 2>/dev/null || sudo chown $USER:$USER "$XAUTH_FILE"
fi

# Generate X authority entry (suppress lock errors)
xauth nlist "$DISPLAY" 2>/dev/null | sed -e 's/^..../ffff/' | xauth -f "$XAUTH_FILE" nmerge - 2>/dev/null || echo "⚠️  xauth merge failed (non-critical)"

# Allow local Docker containers to access X server
echo "Granting Docker containers access to X11..."
xhost +local:docker > /dev/null 2>&1 || echo "⚠️  xhost command failed (non-critical)"

echo "✅ X11 display setup completed successfully!"
echo "   DISPLAY: $DISPLAY"
echo "   XAUTHORITY: $XAUTH_FILE"
