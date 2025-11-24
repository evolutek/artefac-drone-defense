#!/bin/bash
# Artefac Drone Defense - Startup Script
# This script configures the display based on HOST_OS in .env before starting Docker services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${GREEN}[MAIN] ✓${NC} $1"; }
log_step() { echo -e "${BLUE}[MAIN] →${NC} $1"; }
log_warn() { echo -e "${YELLOW}[MAIN] ⚠${NC} $1"; }
log_error() { echo -e "${RED}[MAIN] ✗${NC} $1"; }

echo -e "\n${BLUE}=== Artefac Drone Defense - Starting Services ===${NC}\n"

# Load .env file
if [ ! -f .env ]; then
    log_error ".env file not found"
    echo "   Please copy .env.example to .env and configure HOST_OS"
    exit 1
fi

log_step "Loading configuration from .env"
export $(grep -v '^#' .env | xargs)

# Validate HOST_OS
if [ -z "$HOST_OS" ]; then
    log_error "HOST_OS not set in .env"
    echo "   Valid values: linux, macos, windows"
    exit 1
fi

if [ "$HOST_OS" != "linux" ] && [ "$HOST_OS" != "macos" ] && [ "$HOST_OS" != "windows" ]; then
    log_error "Invalid HOST_OS: $HOST_OS"
    echo "   Valid values: linux, macos, windows"
    exit 1
fi

# Run display setup script
if [ "$HOST_OS" != "macos" ]; then
    log_step "Setting up display for $HOST_OS"
    SCRIPT_PATH="./scripts/start_display_${HOST_OS}.sh"
    if [ ! -f "$SCRIPT_PATH" ]; then
        log_error "Display setup script not found: $SCRIPT_PATH"
        exit 1
    fi
    bash "$SCRIPT_PATH"
fi

# macOS-specific: Force GUI mode
if [ "$HOST_OS" = "macos" ]; then
    export HEADLESS=0
    log_info "macOS: Forcing GUI mode (HEADLESS=0)"
    export PX4_GZ_WORLD="${PX4_GZ_WORLD:-harmonic_heightmap}"
    log_step "Starting backend and MQTT"
    docker compose up -d mqtt backend || true
    log_step "Starting Vite dev server on port 3000"
    (cd frontend && npm run dev >/tmp/artefac_frontend_dev.log 2>&1 &) || true
    log_step "Waiting for http://127.0.0.1:3000"
    (cd frontend && npx wait-on http://127.0.0.1:3000) || true
    log_step "Starting Electron (Three.js)"
    (cd frontend && NATIVE_GAZEBO=1 npm run electron:dev >/tmp/artefac_electron.log 2>&1 &) || true
    log_step "Compiling Cocoa launcher (AppKit)"
    swiftc -framework AppKit macos/GazeboLauncher/main.swift -o /tmp/GazeboLauncher || true
    log_step "Launching Cocoa window for Gazebo (Metal)"
    (PX4_GZ_WORLD="$PX4_GZ_WORLD" /tmp/GazeboLauncher >/tmp/artefac_gazebo_native.log 2>&1 &) || true
    log_step "Starting Expo mobile"
    (cd mobile && npm install >/tmp/artefac_mobile_install.log 2>&1 && npm run start >/tmp/artefac_mobile.log 2>&1 &) || true
    log_info "Services started (macOS native)"
else
    echo -e "\n${BLUE}=== Starting Docker Compose Services ===${NC}\n"
    docker compose "$@"
fi
