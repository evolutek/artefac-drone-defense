#!/bin/bash
# Artefac Drone Defense - macOS Native Gazebo GUI Launcher
# This script runs Gazebo server in Docker and GUI natively on macOS with Metal rendering

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${GREEN}[MACOS-NATIVE] ✓${NC} $1"; }
log_step() { echo -e "${BLUE}[MACOS-NATIVE] →${NC} $1"; }
log_warn() { echo -e "${YELLOW}[MACOS-NATIVE] ⚠${NC} $1"; }
log_error() { echo -e "${RED}[MACOS-NATIVE] ✗${NC} $1"; }

echo -e "\n${BLUE}=== Artefac Drone Defense - macOS Native GUI ===${NC}\n"

# Check if gz command is available
if ! command -v gz &> /dev/null; then
    log_error "Gazebo Harmonic not found"
    echo "   Please install: brew install gz-harmonic"
    exit 1
fi

log_info "Found $(gz sim --version | head -n1)"

# Load .env file
if [ ! -f .env ]; then
    log_error ".env file not found"
    echo "   Please copy .env.example to .env"
    exit 1
fi

log_step "Loading configuration from .env"
export $(grep -v '^#' .env | xargs)

# Force server-only mode for Docker
export HEADLESS=1
export HOST_OS=macos

# Configure Gazebo Transport for server/client communication
export GZ_PARTITION=${GZ_PARTITION:-artefac}
export GZ_IP=${GZ_IP:-127.0.0.1}

log_info "Gazebo Transport partition: $GZ_PARTITION"

# World file configuration
WORLD_FILE=${PX4_GZ_WORLD:-harmonic_heightmap}
WORLD_PATH="simulation/gazebo_worlds/${WORLD_FILE}.sdf"

if [ ! -f "$WORLD_PATH" ]; then
    log_error "World file not found: $WORLD_PATH"
    exit 1
fi

log_info "World file: $WORLD_FILE"

# Cleanup function
cleanup() {
    log_step "Stopping services..."
    docker compose down 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Start Docker Compose (server-only mode)
log_step "Starting Gazebo server in Docker (HEADLESS=1)..."
docker compose up -d simulation ros2_integration

# Wait for Gazebo server to be ready
log_step "Waiting for Gazebo server to initialize (15s)..."
sleep 5

# Check if server is running
log_step "Checking server status..."
for i in {1..10}; do
    if gz topic -l 2>/dev/null | grep -q "/clock"; then
        log_info "Gazebo server is ready!"
        break
    fi
    if [ $i -eq 10 ]; then
        log_error "Gazebo server failed to start"
        echo "   Check logs: docker compose logs simulation"
        exit 1
    fi
    echo -n "."
    sleep 1
done

# Launch native GUI
echo -e "\n${BLUE}=== Launching Native Gazebo GUI ===${NC}\n"
log_step "Starting GUI with Metal rendering..."
log_info "Opening Gazebo window (may take 10-15 seconds)..."

# Set resource paths to match Docker container
export GZ_SIM_RESOURCE_PATH="$(pwd)/simulation/gazebo_worlds:$(pwd)/simulation/models"

# Launch GUI
gz sim -g -v 4 "$WORLD_PATH" &
GUI_PID=$!

log_info "GUI launched (PID: $GUI_PID)"
log_info "Press Ctrl+C to stop all services"

# Wait for GUI to exit
wait $GUI_PID

log_step "GUI closed, stopping Docker services..."
