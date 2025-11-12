"""
Docker container orchestration helpers for integration tests.

These fixtures manage the lifecycle of Docker containers during tests:
- Starting containers with proper dependency order
- Waiting for healthchecks to pass
- Capturing logs on test failures
- Automatic cleanup after tests
"""

import docker
import subprocess
import time
from typing import Dict, List, Optional
import pytest


class ContainerManager:
    """Manages Docker containers for integration tests."""

    def __init__(self):
        self.client = docker.from_env()
        self.started_services = []

    def start_services(self, services: List[str], timeout: int = 120) -> Dict[str, docker.models.containers.Container]:
        """
        Start specified Docker Compose services and wait for them to be healthy.

        Args:
            services: List of service names from docker-compose.yml
            timeout: Maximum time to wait for healthchecks (seconds)

        Returns:
            Dictionary mapping service names to Container objects

        Raises:
            TimeoutError: If containers don't become healthy within timeout
        """
        print(f"\n🚀 Starting services: {', '.join(services)}")

        # Start services using docker compose
        cmd = ["docker", "compose", "up", "-d"] + services
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Failed to start services: {result.stderr}")

        self.started_services.extend(services)

        # Wait for healthchecks to pass
        containers = {}
        start_time = time.time()

        # Map service names to container names
        service_to_container = {
            "simulation": "artefac_simulation",
            "ros2_integration": "artefac_ros2_integration",
            "mqtt": "artefac_mqtt",
            "backend": "artefac_backend",
            "frontend": "artefac_frontend"
        }

        for service in services:
            container_name = service_to_container.get(service, f"artefac_{service}")

            print(f"⏳ Waiting for {service} to be healthy...", end="", flush=True)

            while time.time() - start_time < timeout:
                try:
                    container = self.client.containers.get(container_name)

                    # Check if container has healthcheck
                    health_status = container.attrs.get('State', {}).get('Health', {}).get('Status')

                    if health_status == 'healthy':
                        containers[service] = container
                        elapsed = time.time() - start_time
                        print(f" ✓ ({elapsed:.1f}s)")
                        break
                    elif health_status == 'unhealthy':
                        # Container is unhealthy, fail fast
                        logs = container.logs(tail=50).decode('utf-8', errors='ignore')
                        raise RuntimeError(f"{service} became unhealthy:\n{logs}")

                    # Container might not have healthcheck, just check if running
                    if container.attrs['State']['Status'] == 'running' and health_status is None:
                        containers[service] = container
                        elapsed = time.time() - start_time
                        print(f" ✓ (no healthcheck, {elapsed:.1f}s)")
                        break

                except docker.errors.NotFound:
                    pass  # Container not yet created

                time.sleep(2)
            else:
                # Timeout reached
                raise TimeoutError(f"{service} did not become healthy within {timeout}s")

        print("✅ All services started successfully\n")
        return containers

    def get_container_logs(self, container: docker.models.containers.Container,
                          tail: int = 100) -> str:
        """Get recent logs from a container."""
        return container.logs(tail=tail).decode('utf-8', errors='ignore')

    def execute_in_container(self, container: docker.models.containers.Container,
                            command: str) -> tuple[int, str]:
        """
        Execute a command inside a container.

        Returns:
            Tuple of (exit_code, output)
        """
        result = container.exec_run(command, demux=False)
        output = result.output.decode('utf-8', errors='ignore') if result.output else ""
        return result.exit_code, output

    def stop_services(self):
        """Stop all started services."""
        if self.started_services:
            print(f"\n🛑 Stopping services: {', '.join(self.started_services)}")
            subprocess.run(["docker", "compose", "down"], capture_output=True)
            self.started_services = []


@pytest.fixture(scope="function")
def container_manager():
    """
    Pytest fixture providing a ContainerManager instance.

    Automatically cleans up containers after each test.
    """
    manager = ContainerManager()
    yield manager
    manager.stop_services()


@pytest.fixture(scope="function")
def simulation_containers(container_manager):
    """
    Start simulation and ROS2 integration containers for EKF2 tests.

    This is the minimal set needed to test PX4 SITL + Gazebo + MAVROS.
    """
    containers = container_manager.start_services(["simulation", "ros2_integration"])

    # Give extra time for PX4 to initialize
    print("⏳ Allowing 10s for PX4 initialization...")
    time.sleep(10)

    return containers


@pytest.fixture(scope="function")
def full_system(container_manager):
    """
    Start all services for end-to-end tests.

    Services: simulation, ros2_integration, mqtt, backend, frontend
    """
    containers = container_manager.start_services([
        "simulation",
        "ros2_integration",
        "mqtt",
        "backend",
        "frontend"
    ])

    # Give extra time for full system to stabilize
    print("⏳ Allowing 15s for full system initialization...")
    time.sleep(15)

    return containers
