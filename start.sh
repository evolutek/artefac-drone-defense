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
log_info()  { echo -e "${GREEN}[MAIN] ✓${NC} $1"; }
log_step()  { echo -e "${BLUE}[MAIN] →${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[MAIN] ⚠${NC} $1"; }
log_error() { echo -e "${RED}[MAIN] ✗${NC} $1"; }

echo -e "\n${BLUE}=== Artefac Drone Defense - Starting Services ===${NC}\n"

# Load .env file
if [ ! -f .env ]; then
    log_error ".env file not found"
    echo "   Please copy .env.example to .env and configure HOST_OS"
    exit 1
fi

log_step "Loading configuration from .env"

# Export all variables defined in .env
set -o allexport
# shellcheck source=/dev/null
source .env
set +o allexport

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
log_step "Setting up display for $HOST_OS"
SCRIPT_PATH="./scripts/start_display_${HOST_OS}.sh"

if [ ! -f "$SCRIPT_PATH" ]; then
    log_error "Display setup script not found: $SCRIPT_PATH"
    exit 1
fi

bash "$SCRIPT_PATH"

# macOS-specific: Force GUI mode
if [ "$HOST_OS" = "macos" ]; then
    export HEADLESS=0
    log_info "macOS: Forcing GUI mode (HEADLESS=0)"
fi

# Start Docker Compose
echo -e "\n${BLUE}=== Starting Docker Compose Services ===${NC}\n"
docker compose "$@"
