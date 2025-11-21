#!/bin/bash
# macOS XQuartz Display Setup Script
# This script prepares XQuartz for Docker containers on macOS

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() { echo -e "${GREEN}[DISPLAY] ✓${NC} $1"; }
log_step() { echo -e "${BLUE}[DISPLAY] →${NC} $1"; }
log_warn() { echo -e "${YELLOW}[DISPLAY] ⚠${NC} $1"; }
log_error() { echo -e "${RED}[DISPLAY] ✗${NC} $1"; }

log_step "macOS XQuartz display setup"

# Check XQuartz installation
if ! command -v xquartz &> /dev/null && ! [ -d "/Applications/Utilities/XQuartz.app" ]; then
    log_error "XQuartz not installed"
    echo "   Install from: https://www.xquartz.org/"
    echo "   Or use: brew install --cask xquartz"
    exit 1
fi

# Start XQuartz if needed
if ! pgrep -x "Xquartz" > /dev/null; then
    log_step "Starting XQuartz"
    open -a XQuartz
    sleep 10
fi

# Detect host IP
HOST_IP=$(ifconfig en0 | grep "inet " | awk '{print $2}')
[ -z "$HOST_IP" ] && HOST_IP=$(ifconfig en1 | grep "inet " | awk '{print $2}')

if [ -z "$HOST_IP" ]; then
    log_warn "Could not detect host IP, using host.docker.internal"
    export DISPLAY="host.docker.internal:0"
else
    export DISPLAY="$HOST_IP:0"
fi

# Grant X11 access
xhost + "$HOST_IP" > /dev/null 2>&1 || true
xhost + 127.0.0.1 > /dev/null 2>&1 || true

# Create fresh XAUTH file
XAUTH_FILE="${HOME}/.docker.xauth"
[ -f "$XAUTH_FILE" ] && rm -f "$XAUTH_FILE"
touch "$XAUTH_FILE"
chmod 600 "$XAUTH_FILE"

# Add X authorization
xauth nlist "$DISPLAY" 2>/dev/null | sed -e 's/^..../ffff/' | xauth -f "$XAUTH_FILE" nmerge - 2>/dev/null || true

log_info "Display configured - DISPLAY=$DISPLAY"
log_warn "Ensure 'Allow connections from network clients' is enabled"
echo "   XQuartz → Preferences → Security"
