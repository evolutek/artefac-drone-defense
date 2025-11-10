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

echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}  Artefac Drone Defense - Starting Services${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo ""

# Load .env file
if [ ! -f .env ]; then
    echo -e "${RED}✗${NC} .env file not found!"
    echo -e "   Please copy .env.example to .env and configure HOST_OS"
    exit 1
fi

echo -e "${GREEN}✓${NC} Loading configuration from .env file..."
export $(grep -v '^#' .env | xargs)
echo ""

# Check if HOST_OS is set
if [ -z "$HOST_OS" ]; then
    echo -e "${RED}✗${NC} HOST_OS is not set in .env file!"
    echo -e "   Please add HOST_OS to your .env file with one of these values:"
    echo -e "   - HOST_OS=linux"
    echo -e "   - HOST_OS=macos"
    echo -e "   - HOST_OS=windows"
    exit 1
fi

# Validate HOST_OS value
if [ "$HOST_OS" != "linux" ] && [ "$HOST_OS" != "macos" ] && [ "$HOST_OS" != "windows" ]; then
    echo -e "${RED}✗${NC} Invalid HOST_OS value: $HOST_OS"
    echo -e "   Valid values are: linux, macos, windows"
    exit 1
fi

# Run the appropriate display setup script
echo -e "${BLUE}→${NC} Setting up display for ${HOST_OS}..."
SCRIPT_PATH="./scripts/start_display_${HOST_OS}.sh"

if [ ! -f "$SCRIPT_PATH" ]; then
    echo -e "${RED}✗${NC} Display setup script not found: $SCRIPT_PATH"
    exit 1
fi

# Execute the display setup script
bash "$SCRIPT_PATH"

# Override HEADLESS to 0 on macOS (GUI required for proper Gazebo operation)
if [ "$HOST_OS" = "macos" ]; then
    export HEADLESS=0
    echo -e "${GREEN}✓${NC} macOS detected: Forcing HEADLESS=0 for GUI mode"
    echo ""
fi
echo ""

# Start Docker Compose services
echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}  Starting Docker Compose services...${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo ""

# Pass all arguments to docker-compose (e.g., ./start.sh up -d)
docker compose "$@"
