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
    chown "$USER:$USER" "$XAUTH_FILE" 2>/dev/null || true
else
    chmod 600 "$XAUTH_FILE" 2>/dev/null || sudo chmod 600 "$XAUTH_FILE"
    chown "$USER:$USER" "$XAUTH_FILE" 2>/dev/null || sudo chown "$USER:$USER" "$XAUTH_FILE"
fi

# Setup X11 auth based on session type
if [ "$SESSION_TYPE" = "wayland" ]; then
    log_step "Wayland session - using XWayland compatibility"

    # 1) On privilégie le XAUTHORITY déjà défini par la session (KDE, Sway, etc.)
    SOURCE_AUTH=""
    if [ -n "$XAUTHORITY" ] && [ -f "$XAUTHORITY" ]; then
        SOURCE_AUTH="$XAUTHORITY"
    else
        # 2) Fallback GNOME : fichiers .mutter-Xwaylandauth*
        WAYLAND_XAUTH=$(find "/run/user/$(id -u)/" -maxdepth 1 -name ".mutter-Xwaylandauth*" 2>/dev/null | head -n1)
        if [ -n "$WAYLAND_XAUTH" ]; then
            SOURCE_AUTH="$WAYLAND_XAUTH"
        fi
    fi

    if [ -n "$SOURCE_AUTH" ]; then
        # On copie les entrées du fichier source vers ~/.docker.xauth
        XAUTHORITY="$SOURCE_AUTH" xauth nlist "$DISPLAY" 2>/dev/null \
            | sed -e 's/^..../ffff/' \
            | xauth -f "$XAUTH_FILE" nmerge - 2>/dev/null || true

        XAUTHORITY="$SOURCE_AUTH" xhost +local:docker 2>/dev/null || true

        log_info "Merged XWayland auth from $SOURCE_AUTH into $XAUTH_FILE"
    else
        # Dernier recours : on tente avec xauth "brut" sur DISPLAY
        log_warn "No specific XWayland auth source found, using raw xauth on DISPLAY=$DISPLAY"
        xauth nlist "$DISPLAY" 2>/dev/null \
            | sed -e 's/^..../ffff/' \
            | xauth -f "$XAUTH_FILE" nmerge - 2>/dev/null || true
    fi
else
    log_step "X11 session - using standard X11 access"

    xauth nlist "$DISPLAY" 2>/dev/null \
        | sed -e 's/^..../ffff/' \
        | xauth -f "$XAUTH_FILE" nmerge - 2>/dev/null || true

    xhost +local:docker 2>/dev/null || true
fi

log_info "Display configured - DISPLAY=$DISPLAY"
