"""
Pytest configuration file for artefac-drone-defense tests.

This file makes fixtures available to all test files without explicit imports.
Pytest automatically discovers and loads this file.
"""

import pytest
import sys
from pathlib import Path

# Add project root to Python path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import fixtures to make them globally available
from tests.fixtures.docker_helpers import (
    container_manager,
    simulation_containers,
    full_system
)

# Pytest configuration
def pytest_configure(config):
    """Configure pytest before tests run."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests requiring Docker"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests requiring full system"
    )


def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addoption(
        "--keep-containers",
        action="store_true",
        default=False,
        help="Keep containers running after tests (for debugging)"
    )


@pytest.fixture(scope="session", autouse=True)
def test_environment_check():
    """Verify test environment is properly configured before running tests."""
    import docker
    import subprocess

    print("\n" + "="*70)
    print("🔍 Checking test environment...")
    print("="*70)

    # Check Docker daemon is running
    try:
        client = docker.from_env()
        client.ping()
        print("✓ Docker daemon is running")
    except Exception as e:
        pytest.exit(f"❌ Docker daemon not accessible: {e}")

    # Check docker-compose is available
    result = subprocess.run(
        ["docker", "compose", "version"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        pytest.exit("❌ docker compose not found")
    print(f"✓ docker compose available: {result.stdout.strip()}")

    # Check if project is in correct directory
    docker_compose_file = PROJECT_ROOT / "docker-compose.yml"
    if not docker_compose_file.exists():
        pytest.exit(f"❌ docker-compose.yml not found at {docker_compose_file}")
    print(f"✓ docker-compose.yml found")

    print("="*70)
    print("✅ Test environment ready\n")


@pytest.fixture(scope="function", autouse=True)
def cleanup_on_failure(request):
    """Capture and display container logs if test fails."""
    yield

    if hasattr(request.node, 'rep_call') and request.node.rep_call.failed:
        # Test failed, try to get container logs
        try:
            import docker
            client = docker.from_env()

            print("\n" + "="*70)
            print("❌ TEST FAILED - Container logs:")
            print("="*70)

            container_names = [
                "artefac_simulation",
                "artefac_ros2_integration",
                "artefac_mqtt",
                "artefac_backend"
            ]

            for container_name in container_names:
                try:
                    container = client.containers.get(container_name)
                    logs = container.logs(tail=30).decode('utf-8', errors='ignore')
                    print(f"\n📋 {container_name} (last 30 lines):")
                    print("-" * 70)
                    print(logs)
                except docker.errors.NotFound:
                    pass  # Container doesn't exist, skip

        except Exception as e:
            print(f"Could not retrieve logs: {e}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to capture test results for cleanup_on_failure fixture."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
