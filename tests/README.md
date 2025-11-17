# Integration Tests - Artefac Drone Defense

Automated integration tests for the multi-drone simulation system. These tests verify the complete vision-based localization pipeline: **Gazebo Harmonic → Vision Pose Bridge → MAVROS → PX4 EKF2**.

---

## Quick Start

### Option 1: Using the test script (recommended for local development)

```bash
# Run all EKF2 tests
./run_tests.sh

# Quick smoke test only (~30 seconds)
./run_tests.sh --quick

# Verbose output with print statements
./run_tests.sh -v

# Stop on first failure and keep containers for debugging
./run_tests.sh -x --keep
```

### Option 2: Using pytest directly

```bash
# Create virtual environment (first time only)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r tests/requirements.txt

# Run tests
pytest tests/integration/ -v -m integration
```

---

## Test Structure

```
tests/
├── conftest.py                      # Pytest configuration & global fixtures
├── requirements.txt                 # Test dependencies
├── fixtures/
│   └── docker_helpers.py            # Container orchestration helpers
└── integration/
    └── test_ekf2_convergence.py     # EKF2 convergence tests (7 tests)
```

---

## Available Tests

### EKF2 Convergence Test Suite (`test_ekf2_convergence.py`)

Tests are organized by **EKF2 initialization phases** and execute in sequence with dependencies. Each test depends on the previous phase succeeding. Tests stop on first failure when using `-x` flag.

#### Test Execution Order (Following EKF2 Phases)

**Phase 1: Sensor Initialization (2-5s)**
| Test | Description | Duration | What it validates |
|------|-------------|----------|-------------------|
| `test_phase1_gazebo_sensors_active` | Gazebo sensor data via MAVROS | ~10s | MAVROS publishes IMU and magnetometer data |
| `test_phase1_vision_bridge_active` | Vision bridge publishing rate | ~10s | Vision pose bridge publishes at >40 Hz (typically ~50-100 Hz) |

**Phase 2: EKF2 Initialization (3-10s)**
| Test | Description | Duration | What it validates |
|------|-------------|----------|-------------------|
| `test_phase2_gps_free_parameters_applied` | GPS-free configuration | ~5s | Vision fusion parameters correctly set (EKF2_EV_CTRL=15, etc.) |
| `test_phase2_mavros_receives_vision_data` | MAVROS odometry topic | ~10s | MAVROS receives vision data at >40 Hz |
| `test_phase2_ekf2_initialization` | EKF2 startup and alignment | ~20s | EKF2 initializes without critical errors |

**Phase 3: EKF2 Convergence (5-15s)**
| Test | Description | Duration | What it validates |
|------|-------------|----------|-------------------|
| `test_phase3_local_position_available` | EKF2 fused output | ~10s | MAVROS publishes local position from EKF2 with valid values |

**Quick Check (Independent)**
| Test | Description | Duration | What it validates |
|------|-------------|----------|-------------------|
| `test_ekf2_quick_check` | Quick smoke test | ~15s | Basic sanity check (containers + no critical errors) |

**Total runtime:** ~3-5 minutes for full suite (phases run sequentially)

**Test Dependencies:**
```
Phase 1: Sensors → Vision Bridge
         ↓
Phase 2: Parameters → MAVROS Vision → EKF2 Init
         ↓
Phase 3: Local Position Available
```

Use `pytest -x` or `./run_tests.sh -x` to stop on first failure and quickly identify which phase fails.

---

## Test Fixtures

### `simulation_containers` (used by EKF2 tests)

Starts `simulation` + `ros2_integration` containers and waits for healthchecks.

```python
def test_example(simulation_containers):
    sim = simulation_containers['simulation']
    ros2 = simulation_containers['ros2_integration']

    logs = sim.logs(tail=100).decode('utf-8')
    assert "PX4 ready" in logs
```

### `full_system` (for future E2E tests)

Starts all 5 services: `simulation`, `ros2_integration`, `mqtt`, `backend`, `frontend`.

### `container_manager` (low-level fixture)

Provides direct control over container lifecycle:

```python
def test_custom(container_manager):
    containers = container_manager.start_services(["simulation"])
    exit_code, output = container_manager.execute_in_container(
        containers['simulation'],
        "bash -c 'source /opt/ros/humble/setup.bash && ros2 topic list'"
    )
```

---

## Running Specific Tests

### Run all tests with stop-on-first-failure (recommended)
```bash
# Using test script (recommended)
./run_tests.sh integration -x

# Using pytest directly
pytest tests/integration/ -v -x -m integration
```

### Run tests by phase
```bash
# Phase 1 only (sensor initialization)
pytest tests/integration/test_ekf2_convergence.py -v -k phase1

# Phase 2 only (EKF2 initialization)
pytest tests/integration/test_ekf2_convergence.py -v -k phase2

# Phase 3 only (EKF2 convergence) - requires Phase 1 & 2 to pass
pytest tests/integration/test_ekf2_convergence.py -v -k phase3
```

### Run a single test
```bash
# Specific phase test
./run_tests.sh -k test_phase1_gazebo_sensors_active

# Quick check only
./run_tests.sh -k test_ekf2_quick_check
```

### Run tests matching a pattern
```bash
pytest tests/integration/ -v -k "ekf2 or vision"
```

### Run only the test class
```bash
pytest tests/integration/test_ekf2_convergence.py::TestEKF2Convergence -v -x
```

### Run with markers
```bash
# Only integration tests
pytest -v -m integration

# Exclude slow tests
pytest -v -m "not slow"
```

---

## Test Options

### `run_tests.sh` options

| Option | Description |
|--------|-------------|
| `-v`, `--verbose` | Show detailed output and print statements |
| `-x`, `--exitfirst` | Stop after first failure |
| `-k EXPRESSION` | Run only tests matching EXPRESSION |
| `--keep` | Keep containers running after tests (for debugging) |
| `--quick` | Run only quick smoke test (~30s) |
| `--ekf2-only` | Run full EKF2 test suite |
| `-h`, `--help` | Show all options |

### Pytest options (when using pytest directly)

```bash
# Verbose with print statements
pytest tests/integration/ -v -s

# Stop on first failure
pytest tests/integration/ -x

# Run tests in parallel (faster, requires pytest-xdist)
pytest tests/integration/ -n 2

# Generate HTML report
pytest tests/integration/ --html=test-report.html
```

---

## Debugging Failed Tests

### 1. Keep containers running

```bash
./run_tests.sh --keep
```

Then inspect manually:
```bash
# Check logs
docker logs artefac_simulation
docker logs artefac_ros2_integration

# Access container shell
docker exec -it artefac_simulation bash
docker exec -it artefac_ros2_integration bash

# Check ROS2 topics
docker exec -it artefac_ros2_integration bash -c \
  "source /opt/ros/humble/setup.bash && ros2 topic list"
```

### 2. View container logs during tests

```bash
./run_tests.sh -v -s
```

The `conftest.py` automatically captures and displays logs when tests fail.

### 3. Run a single test with verbose output

```bash
pytest tests/integration/test_ekf2_convergence.py::test_ekf2_quick_check -v -s
```

---

## Common Issues

### Test timeout: "Containers did not become healthy"

**Cause:** Containers taking too long to start or healthcheck failing.

**Solution:**
1. Check Docker resources (CPU/RAM)
2. View logs: `docker compose logs simulation`
3. Increase timeout in `docker_helpers.py` (default: 120s)

### "No IMU data from MAVROS" assertion fails

**Cause:** Gazebo not providing sensor data to PX4, or MAVROS not connected.

**Solution:**
- **macOS:** Ensure `HEADLESS=0` (GUI mode required for sensors)
- **Linux:** Check GPU access with `nvidia-smi`
- Verify Gazebo process: `docker exec artefac_simulation ps aux | grep gz`
- Check MAVROS connection: `docker exec artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 topic list | grep mavros"`
- Manually test IMU topic: `docker exec artefac_ros2_integration bash -c "source /opt/ros/humble/setup.bash && ros2 topic echo /mavros/imu/data --once"`

### "Vision bridge not publishing odometry"

**Cause:** Vision pose bridge node not starting or Gazebo transport issues.

**Solution:**
1. Check ROS2 logs: `docker logs artefac_ros2_integration | grep vision`
2. Verify Gazebo is publishing: `gz topic -l` (inside container)
3. Check if `/model/x500_0/pose` topic exists in Gazebo

### Tests pass locally but fail in CI

**Cause:** Resource constraints or timing differences in CI environment.

**Solution:**
- Increase wait times in CI (slower startup)
- Check CI logs for healthcheck status
- Ensure Docker BuildKit cache is enabled

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/integration_tests.yml
name: Integration Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test-ekf2:
    runs-on: ubuntu-22.04

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        pip install -r tests/requirements.txt

    - name: Build containers
      run: docker compose build simulation ros2_integration

    - name: Run EKF2 tests
      run: pytest tests/integration/ -v -m integration

    - name: Upload logs on failure
      if: failure()
      uses: actions/upload-artifact@v3
      with:
        name: container-logs
        path: logs/

    - name: Cleanup
      if: always()
      run: docker compose down
```

---

## Writing New Tests

### Example: Testing a new feature

```python
# tests/integration/test_new_feature.py
import pytest

@pytest.mark.integration
def test_my_new_feature(simulation_containers):
    """Test description following Google docstring style."""

    # Arrange
    sim = simulation_containers['simulation']

    # Act
    exit_code, output = sim.exec_run("some_command")

    # Assert
    assert exit_code == 0, f"Command failed: {output}"
    assert "expected_output" in output.decode('utf-8')
```

### Best Practices

1. **Use descriptive test names**: `test_what_is_being_tested`
2. **Add docstrings**: Explain what the test validates and why
3. **Use real data**: No mocking - test against actual containers
4. **Clear assertions**: Include helpful error messages
5. **Proper cleanup**: Fixtures handle cleanup automatically
6. **Mark tests**: Use `@pytest.mark.integration` or `@pytest.mark.slow`

---

## Test Coverage (Future)

To add coverage reporting:

```bash
# Install coverage plugin
pip install pytest-cov

# Run tests with coverage
pytest tests/integration/ --cov=backend --cov=simulation/src --cov-report=html

# View report
open htmlcov/index.html
```

---

## Maintenance

### Adding new test dependencies

1. Add to `tests/requirements.txt`
2. Update installation in CI workflow
3. Document in this README

### Updating test fixtures

Fixtures are defined in:
- `tests/conftest.py` - Global configuration
- `tests/fixtures/docker_helpers.py` - Container orchestration

Changes to fixtures affect all tests using them.

---

## Support

- **Issues**: Create an issue in the project repository
- **Documentation**: See main `CLAUDE.md` for project architecture
- **Logs**: Check `logs/` directory (gitignored) for detailed container logs

---

**Last Updated:** 2025-11-12
**Test Framework:** pytest 7.4.3
**Python:** 3.10+
**Docker Compose:** V2
