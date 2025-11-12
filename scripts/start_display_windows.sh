#!/bin/bash
# Windows (WSL2) X Server Display Setup Script
# This script prepares the X server connection for Docker containers on Windows WSL2

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

log_step "Windows WSL2 display setup"

# Detect Windows host IP
if grep -qi microsoft /proc/version; then
    WINDOWS_HOST=$(grep nameserver /etc/resolv.conf | awk '{print $2}')
    export DISPLAY="$WINDOWS_HOST:0.0"
elif [ -n "$WSL_DISTRO_NAME" ]; then
    WINDOWS_HOST=$(ip route show | grep -i default | awk '{print $3}')
    export DISPLAY="$WINDOWS_HOST:0.0"
else
    log_warn "Not running in WSL2 environment"
    export DISPLAY=":0"
fi

# Create XAUTH file
XAUTH_FILE="${HOME}/.docker.xauth"
if [ ! -f "$XAUTH_FILE" ]; then
    touch "$XAUTH_FILE"
    chmod 600 "$XAUTH_FILE"
fi

# Setup xauth if available
if command -v xauth &> /dev/null; then
    xauth nlist "$DISPLAY" | sed -e 's/^..../ffff/' | xauth -f "$XAUTH_FILE" nmerge - 2>/dev/null || true
fi

log_info "Display configured - DISPLAY=$DISPLAY"
log_warn "Ensure X Server is running on Windows"
echo "   VcXsrv: Launch with 'Disable access control' checked"
echo "   X410: Should work automatically"
