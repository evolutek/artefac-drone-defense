#!/bin/bash
# Windows (WSL2) X Server Display Setup Script
# This script prepares the X server connection for Docker containers on Windows WSL2

set -e

echo "🪟 Setting up X11 display for Windows WSL2..."

# Detect Windows host IP
if grep -qi microsoft /proc/version; then
    # WSL2: Get Windows host IP from resolv.conf
    WINDOWS_HOST=$(grep nameserver /etc/resolv.conf | awk '{print $2}')
    echo "Detected Windows host IP: $WINDOWS_HOST"
    export DISPLAY="$WINDOWS_HOST:0.0"
elif [ -n "$WSL_DISTRO_NAME" ]; then
    # Alternative WSL detection
    WINDOWS_HOST=$(ip route show | grep -i default | awk '{print $3}')
    echo "Detected Windows host IP: $WINDOWS_HOST"
    export DISPLAY="$WINDOWS_HOST:0.0"
else
    echo "⚠️  WARNING: Not running in WSL2 environment"
    echo "If you're using native Windows with Docker Desktop, you may need VcXsrv or X410"
    echo "Using default display :0"
    export DISPLAY=":0"
fi

# Create .docker.xauth
XAUTH_FILE="${HOME}/.docker.xauth"
if [ ! -f "$XAUTH_FILE" ]; then
    echo "Creating X authorization file: $XAUTH_FILE"
    touch "$XAUTH_FILE"
    chmod 600 "$XAUTH_FILE"
fi

# Try to set up xauth if available
if command -v xauth &> /dev/null; then
    xauth nlist "$DISPLAY" | sed -e 's/^..../ffff/' | xauth -f "$XAUTH_FILE" nmerge - 2>/dev/null || true
fi

echo "✅ Windows WSL2 display setup completed!"
echo "   DISPLAY: $DISPLAY"
echo "   XAUTHORITY: $XAUTH_FILE"
echo ""
echo "⚠️  IMPORTANT: Make sure you have an X Server running on Windows:"
echo "   - VcXsrv: Launch with 'Disable access control' checked"
echo "   - X410: Should work automatically"
echo "   - Xming: Configure to allow connections"
echo ""
echo "   VcXsrv recommended settings:"
echo "   - Multiple windows"
echo "   - Display number: 0"
echo "   - Disable access control: CHECKED ✓"
