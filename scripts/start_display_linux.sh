#!/bin/bash
# Linux X11 Display Setup Script
# This script prepares the X11 display for Docker containers on Linux

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

log_step "Linux X11 display setup"

# Detect session type
SESSION_TYPE="${XDG_SESSION_TYPE:-x11}"
XAUTH_FILE="${HOME}/.docker.xauth"

# Clean up Docker-created directory if needed
if [ -d "$XAUTH_FILE" ]; then
    log_warn "Removing Docker-created directory: $XAUTH_FILE"
    sudo rm -rf "$XAUTH_FILE"
fi

# Create/fix XAUTH file
if [ ! -f "$XAUTH_FILE" ]; then
    touch "$XAUTH_FILE"
    chmod 600 "$XAUTH_FILE"
    chown $USER:$USER "$XAUTH_FILE" 2>/dev/null || true
else
    chmod 600 "$XAUTH_FILE" 2>/dev/null || sudo chmod 600 "$XAUTH_FILE"
    chown $USER:$USER "$XAUTH_FILE" 2>/dev/null || sudo chown $USER:$USER "$XAUTH_FILE"
fi

# Setup X11 auth based on session type
if [ "$SESSION_TYPE" = "wayland" ]; then
    log_step "Wayland session - using XWayland compatibility"

    WAYLAND_XAUTH=$(find /run/user/$(id -u)/ -name ".mutter-Xwaylandauth*" 2>/dev/null | head -n1)

    if [ -n "$WAYLAND_XAUTH" ]; then
        XAUTHORITY="$WAYLAND_XAUTH" xauth nlist "$DISPLAY" 2>/dev/null | sed -e 's/^..../ffff/' | xauth -f "$XAUTH_FILE" nmerge - 2>/dev/null || true
        XAUTHORITY="$WAYLAND_XAUTH" xhost +local:docker 2>/dev/null || true
    else
        log_warn "XWayland auth file not found, using fallback"
        xauth nlist "$DISPLAY" 2>/dev/null | sed -e 's/^..../ffff/' | xauth -f "$XAUTH_FILE" nmerge - 2>/dev/null || true
    fi
else
    log_step "X11 session - using standard X11 access"

    xauth nlist "$DISPLAY" 2>/dev/null | sed -e 's/^..../ffff/' | xauth -f "$XAUTH_FILE" nmerge - 2>/dev/null || true
    xhost +local:docker 2>/dev/null || true
fi

log_info "Display configured - DISPLAY=$DISPLAY"
