#!/bin/bash
# Test runner for artefac-drone-defense integration tests
# Usage: ./run_tests.sh [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="integration"  # Default to integration tests
TEST_SUBTYPE=""  # For unit backend/ros2/frontend
VERBOSE=false
STOP_ON_FAIL=false
KEEP_CONTAINERS=false
TEST_FILTER=""
SHOW_LOGS=false

print_usage() {
    echo "Usage: $0 [test_type] [options]"
    echo ""
    echo "Test Types:"
    echo "  unit              Run unit tests only (no Docker required)"
    echo "  unit backend      Run backend unit tests"
    echo "  unit ros2         Run ROS2 bridge unit tests"
    echo "  unit frontend     Run frontend unit tests"
    echo "  integration       Run integration tests (requires Docker)"
    echo "  (no argument)     Run integration tests (default)"
    echo ""
    echo "Options:"
    echo "  -v, --verbose        Verbose output (show print statements)"
    echo "  -x, --exitfirst      Stop on first test failure"
    echo "  -k EXPRESSION        Run only tests matching EXPRESSION"
    echo "  -s, --show-logs      Show container logs during tests"
    echo "  --keep               Keep containers running after tests"
    echo "  --quick              Run only quick smoke test"
    echo "  --ekf2-only          Run only EKF2 convergence tests"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 unit                               # Run all unit tests"
    echo "  $0 unit backend                       # Run backend unit tests"
    echo "  $0 integration                        # Run integration tests"
    echo "  $0 -v                                 # Run integration tests (verbose)"
    echo "  $0 unit -k test_create_drone          # Run specific unit test"
    echo "  $0 --quick                            # Run quick smoke test only"
    echo "  $0 integration -x --keep              # Stop on fail, keep containers"
}

# Parse command line arguments
# First, check if first argument is a test type
if [[ $# -gt 0 ]]; then
    case $1 in
        unit)
            TEST_TYPE="unit"
            shift
            # Check for subtype (backend/ros2/frontend)
            if [[ $# -gt 0 ]] && [[ ! $1 =~ ^- ]]; then
                TEST_SUBTYPE="$1"
                shift
            fi
            ;;
        integration)
            TEST_TYPE="integration"
            shift
            ;;
    esac
fi

# Parse remaining options
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -x|--exitfirst)
            STOP_ON_FAIL=true
            shift
            ;;
        -k)
            TEST_FILTER="$2"
            shift 2
            ;;
        -s|--show-logs)
            SHOW_LOGS=true
            shift
            ;;
        --keep)
            KEEP_CONTAINERS=true
            shift
            ;;
        --quick)
            TEST_FILTER="test_ekf2_quick_check"
            shift
            ;;
        --ekf2-only)
            TEST_FILTER="TestEKF2Convergence"
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            print_usage
            exit 1
            ;;
    esac
done

# Print header based on test type
if [ "$TEST_TYPE" = "unit" ]; then
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║            Artefac Drone Defense - Unit Tests                  ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
else
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║         Artefac Drone Defense - Integration Tests              ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
fi
echo ""

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠ Python virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

# Install/upgrade test dependencies
echo -e "${BLUE}Installing test dependencies...${NC}"
pip install -q -r tests/requirements.txt
if [ "$TEST_TYPE" = "unit" ]; then
    pip install -q -r backend/requirements.txt
fi
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Build pytest command based on test type
if [ "$TEST_TYPE" = "unit" ]; then
    # Unit tests don't need Docker
    if [ -n "$TEST_SUBTYPE" ]; then
        PYTEST_CMD="pytest tests/unit/$TEST_SUBTYPE/"
    else
        PYTEST_CMD="pytest tests/unit/"
    fi
else
    # Integration tests require Docker
    # Stop any existing containers
    echo -e "${YELLOW}Stopping any existing containers...${NC}"
    docker compose down --remove-orphans > /dev/null 2>&1 || true
    echo -e "${GREEN}✓ Cleaned up existing containers${NC}"
    echo ""

    PYTEST_CMD="pytest tests/integration/"
fi

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v -s"
else
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ "$STOP_ON_FAIL" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -x"
fi

if [ -n "$TEST_FILTER" ]; then
    PYTEST_CMD="$PYTEST_CMD -k '$TEST_FILTER'"
fi

if [ "$KEEP_CONTAINERS" = true ] && [ "$TEST_TYPE" = "integration" ]; then
    PYTEST_CMD="$PYTEST_CMD --keep-containers"
fi

# Add markers
if [ "$TEST_TYPE" = "integration" ]; then
    PYTEST_CMD="$PYTEST_CMD -m integration"
fi

# Add color
PYTEST_CMD="$PYTEST_CMD --color=yes"

# Show configuration
echo -e "${BLUE}Test Configuration:${NC}"
echo -e "  Test type:       $TEST_TYPE"
if [ -n "$TEST_SUBTYPE" ]; then
    echo -e "  Subtype:         $TEST_SUBTYPE"
fi
echo -e "  Verbose:         $VERBOSE"
echo -e "  Stop on fail:    $STOP_ON_FAIL"
if [ "$TEST_TYPE" = "integration" ]; then
    echo -e "  Keep containers: $KEEP_CONTAINERS"
fi
if [ -n "$TEST_FILTER" ]; then
    echo -e "  Filter:          $TEST_FILTER"
fi
echo ""

# Run tests
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    Running Tests...                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

eval $PYTEST_CMD
TEST_EXIT_CODE=$?

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}║                  ✓ All Tests Passed!                           ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"

    # Cleanup containers unless --keep flag (only for integration tests)
    if [ "$TEST_TYPE" = "integration" ]; then
        if [ "$KEEP_CONTAINERS" = false ]; then
            echo ""
            echo -e "${YELLOW}Cleaning up containers...${NC}"
            docker compose down > /dev/null 2>&1
            echo -e "${GREEN}✓ Containers stopped${NC}"
        else
            echo ""
            echo -e "${YELLOW}⚠ Containers kept running (--keep flag)${NC}"
            echo -e "${YELLOW}  Stop with: docker compose down${NC}"
        fi
    fi
else
    echo -e "${RED}║                  ✗ Tests Failed!                               ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"

    if [ "$TEST_TYPE" = "integration" ]; then
        if [ "$SHOW_LOGS" = true ] || [ "$KEEP_CONTAINERS" = true ]; then
            echo ""
            echo -e "${YELLOW}Container logs available:${NC}"
            echo -e "  docker logs artefac_simulation"
            echo -e "  docker logs artefac_ros2_integration"
        fi

        if [ "$KEEP_CONTAINERS" = false ]; then
            echo ""
            echo -e "${YELLOW}Cleaning up containers...${NC}"
            docker compose down > /dev/null 2>&1
            echo -e "${GREEN}✓ Containers stopped${NC}"
        fi
    fi
fi

exit $TEST_EXIT_CODE
