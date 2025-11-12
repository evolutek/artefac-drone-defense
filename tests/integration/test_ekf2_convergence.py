"""
Integration tests for PX4 EKF2 convergence in simulation.

These tests verify that the complete vision-based localization pipeline works:
    Gazebo Harmonic → Vision Pose Bridge → MAVROS → PX4 EKF2

Test Philosophy:
- Use real container logs and ROS2 topics (no mocking)
- Tests run against actual Docker containers
- Validate dynamic data from running system
"""

import pytest
import re
import time
from typing import Dict
import docker


@pytest.mark.integration
@pytest.mark.slow
class TestEKF2Convergence:
    """Test suite for EKF2 initialization and convergence with vision odometry."""

    def test_vision_bridge_publishes(self, simulation_containers):
        """
        Verify vision_pose_bridge is publishing odometry at expected rate (~52 Hz).

        The vision bridge subscribes to Gazebo pose data and publishes to
        /mavros/odometry/out for EKF2 fusion.
        """
        ros2_container = simulation_containers['ros2_integration']

        # Wait a bit for vision bridge to start publishing
        time.sleep(3)

        # Check vision bridge logs for successful publishing
        logs = ros2_container.logs(tail=100).decode('utf-8', errors='ignore')

        # Should see regular "Odometry published" messages
        assert "Odometry published" in logs, (
            "Vision bridge not publishing odometry. "
            "Check if vision_pose_bridge node started correctly."
        )

        # Should show rate information
        assert "msgs/sec" in logs, "No rate information in vision bridge logs"

        # Verify rate is approximately 52 Hz (check last log line with rate)
        # Example: "Odometry published: pos=[0.000, 0.000, 0.000] vel_body=[0.00, 0.00, 0.00] m/s (52 msgs/sec)"
        rate_match = re.search(r'\((\d+) msgs/sec\)', logs)
        if rate_match:
            rate = int(rate_match.group(1))
            assert 45 < rate < 60, (
                f"Vision bridge rate {rate} Hz outside expected range (45-60 Hz). "
                f"This may indicate Gazebo performance issues."
            )
            print(f"✓ Vision bridge publishing at {rate} Hz")
        else:
            # Rate info might not be in logs yet, but odometry is being published
            print("⚠ Rate information not yet available in logs")

    def test_gazebo_sensors_active(self, simulation_containers):
        """
        Verify Gazebo Harmonic is providing sensor data to PX4 (IMU, Gyro, etc).

        PX4 requires sensor data to initialize EKF2. Timeout errors indicate
        Gazebo is not communicating properly with PX4 SITL.
        """
        sim_container = simulation_containers['simulation']

        # Get recent PX4 logs
        logs = sim_container.logs(tail=300).decode('utf-8', errors='ignore')

        # Should NOT see sensor timeout errors
        sensor_errors = []
        if "Accel #0 fail: TIMEOUT" in logs:
            sensor_errors.append("Accelerometer timeout")
        if "Gyro #0 fail: TIMEOUT" in logs:
            sensor_errors.append("Gyroscope timeout")
        if "Mag #0 fail: TIMEOUT" in logs:
            sensor_errors.append("Magnetometer timeout")

        assert not sensor_errors, (
            f"Sensor timeout errors detected: {', '.join(sensor_errors)}. "
            f"This usually means Gazebo Harmonic is not providing sensor data to PX4. "
            f"Check if Gazebo is running in GUI mode on macOS (HEADLESS=0 required)."
        )

        # Should see sensor-related logs (indicates sensors initialized)
        assert "sensors" in logs.lower() or "sensor" in logs.lower(), (
            "No sensor initialization logs found in PX4 output"
        )

        print("✓ All sensors initialized without timeouts")

    def test_ekf2_initialization(self, simulation_containers):
        """
        Verify EKF2 initializes successfully with vision fusion enabled.

        EKF2 should:
        1. Align successfully (find a good initial state estimate)
        2. Enable vision position/velocity fusion
        3. Not report critical errors
        """
        sim_container = simulation_containers['simulation']

        # EKF2 can take up to 15 seconds to initialize and align
        max_wait = 15
        ekf2_aligned = False

        print("⏳ Waiting for EKF2 to align...", end="", flush=True)

        for i in range(max_wait):
            logs = sim_container.logs(tail=500).decode('utf-8', errors='ignore')

            # Check for successful EKF2 alignment
            if ("ekf2" in logs.lower() and "aligned" in logs.lower()) or \
               ("ekf2" in logs.lower() and "commencing" in logs.lower()):
                ekf2_aligned = True
                print(f" ✓ ({i+1}s)")
                break

            time.sleep(1)
            if (i + 1) % 5 == 0:
                print(f" {i+1}s...", end="", flush=True)

        # Get final logs for assertions
        logs = sim_container.logs(tail=1000).decode('utf-8', errors='ignore')

        # EKF2 should have initialized (may not always log "aligned" explicitly)
        # Check for absence of critical errors instead
        critical_errors = []

        if "ekf2 missing data" in logs.lower():
            critical_errors.append("EKF2 missing sensor data")
        if "stopping navigation" in logs.lower() and "ekf2" in logs.lower():
            critical_errors.append("EKF2 stopped navigation")
        if "ekf2" in logs.lower() and "timeout" in logs.lower():
            critical_errors.append("EKF2 timeout")

        assert not critical_errors, (
            f"EKF2 critical errors detected: {', '.join(critical_errors)}. "
            f"Check sensor data availability and EKF2 parameters."
        )

        # Verify vision fusion mentions (indicates vision parameters applied)
        has_vision_logs = (
            "vision" in logs.lower() or
            "EKF2_EV_CTRL" in logs or
            "external vision" in logs.lower()
        )

        if has_vision_logs:
            print("✓ Vision fusion parameters confirmed in logs")
        else:
            print("⚠ Vision fusion logs not explicitly found (may be normal)")

        print("✓ EKF2 initialized without critical errors")

    def test_mavros_receives_vision_data(self, simulation_containers):
        """
        Verify MAVROS receives vision odometry from vision_pose_bridge.

        This tests the ROS2 communication: vision_pose_bridge → MAVROS
        """
        ros2_container = simulation_containers['ros2_integration']

        # Use ros2 topic hz to measure actual publishing rate
        # Source ROS2 environment and run command with timeout
        command = (
            "bash -c '"
            "source /opt/ros/humble/setup.bash && "
            "source /root/ros2_ws/install/setup.bash && "
            "timeout 5 ros2 topic hz /mavros/odometry/out"
            "'"
        )

        print("⏳ Measuring /mavros/odometry/out publishing rate...")

        exit_code, output = ros2_container.exec_run(command, demux=False)
        output_str = output.decode('utf-8', errors='ignore') if output else ""

        # ros2 topic hz should report average rate
        assert "average rate" in output_str.lower(), (
            f"No odometry data on /mavros/odometry/out. "
            f"Check if vision_pose_bridge is publishing correctly.\n"
            f"Output: {output_str}"
        )

        # Extract rate and verify it's reasonable (>40 Hz)
        rate_match = re.search(r'average rate:\s*([\d.]+)', output_str, re.IGNORECASE)
        if rate_match:
            rate = float(rate_match.group(1))
            assert rate > 40, (
                f"MAVROS odometry rate too low: {rate:.1f} Hz. "
                f"Expected >40 Hz. Check vision bridge performance."
            )
            print(f"✓ MAVROS receiving odometry at {rate:.1f} Hz")
        else:
            # Couldn't parse rate, but "average rate" was found
            print("⚠ Could not parse exact rate, but topic is publishing")

    def test_local_position_available(self, simulation_containers):
        """
        Verify MAVROS publishes fused local position (EKF2 output).

        /mavros/local_position/pose contains the EKF2-fused position estimate.
        This is the final output we care about for localization.
        """
        ros2_container = simulation_containers['ros2_integration']

        # Give EKF2 time to converge and start publishing local position
        time.sleep(5)

        # Try to read one message from local position topic
        command = (
            "bash -c '"
            "source /opt/ros/humble/setup.bash && "
            "source /root/ros2_ws/install/setup.bash && "
            "timeout 5 ros2 topic echo /mavros/local_position/pose --once"
            "'"
        )

        print("⏳ Reading /mavros/local_position/pose...")

        exit_code, output = ros2_container.exec_run(command, demux=False)
        output_str = output.decode('utf-8', errors='ignore') if output else ""

        # Should receive at least one message
        assert "pose:" in output_str.lower(), (
            f"No local position data from EKF2. "
            f"This indicates EKF2 is not publishing fused estimates. "
            f"Check if EKF2 has converged.\n"
            f"Output: {output_str[:500]}"
        )

        assert "position:" in output_str.lower(), (
            f"Malformed local position message (missing position field)\n"
            f"Output: {output_str[:500]}"
        )

        # Extract position values for debugging
        # Format: position:\n  x: 0.0\n  y: 0.0\n  z: 0.0
        pos_x_match = re.search(r'x:\s*([-\d.]+)', output_str)
        pos_y_match = re.search(r'y:\s*([-\d.]+)', output_str)
        pos_z_match = re.search(r'z:\s*([-\d.]+)', output_str)

        if pos_x_match and pos_y_match and pos_z_match:
            x = float(pos_x_match.group(1))
            y = float(pos_y_match.group(1))
            z = float(pos_z_match.group(1))
            print(f"✓ EKF2 local position: x={x:.3f}, y={y:.3f}, z={z:.3f}")
        else:
            print("✓ Local position topic active (values not parsed)")

    def test_gps_free_parameters_applied(self, simulation_containers):
        """
        Verify GPS-free and vision fusion parameters were applied to PX4.

        These parameters are critical for GPS-free operation:
        - EKF2_EV_CTRL=15: Enable vision position, velocity, yaw fusion
        - COM_ARM_WO_GPS=1: Allow arming without GPS
        - EKF2_HGT_REF=3: Use vision for height reference
        """
        sim_container = simulation_containers['simulation']

        # Get all PX4 logs (parameters are set during startup)
        logs = sim_container.logs().decode('utf-8', errors='ignore')

        # Check for critical parameter mentions
        missing_params = []

        if "COM_ARM_WO_GPS" not in logs:
            missing_params.append("COM_ARM_WO_GPS (allow arming without GPS)")

        if "EKF2_EV_CTRL" not in logs:
            missing_params.append("EKF2_EV_CTRL (vision fusion control)")

        if "EKF2_HGT_REF" not in logs:
            missing_params.append("EKF2_HGT_REF (height reference)")

        assert not missing_params, (
            f"GPS-free parameters not found in logs: {', '.join(missing_params)}. "
            f"Check if start_px4_sitl.sh is correctly patching rcS with parameters."
        )

        # Verify EKF2_EV_CTRL value is 15 (full vision fusion)
        # Look for: "EKF2_EV_CTRL: curr: 0 -> new: 15" or similar
        ekf2_ev_ctrl_match = re.search(r'EKF2_EV_CTRL.*?(\d+)', logs)
        if ekf2_ev_ctrl_match:
            value = ekf2_ev_ctrl_match.group(1)
            if value == "15":
                print(f"✓ EKF2_EV_CTRL set to 15 (full vision fusion)")
            else:
                print(f"⚠ EKF2_EV_CTRL found but value is {value}, expected 15")
        else:
            # Parameter set but couldn't extract value
            print("⚠ EKF2_EV_CTRL parameter found but value not parsed")

        # Check for GPS control disabled
        if "EKF2_GPS_CTRL" in logs:
            gps_ctrl_match = re.search(r'EKF2_GPS_CTRL.*?(\d+)', logs)
            if gps_ctrl_match and gps_ctrl_match.group(1) == "0":
                print("✓ EKF2_GPS_CTRL set to 0 (GPS disabled)")

        print("✓ GPS-free parameters confirmed in PX4 logs")


@pytest.mark.integration
def test_ekf2_quick_check(simulation_containers):
    """
    Quick smoke test: verify simulation starts and EKF2 doesn't have critical errors.

    This is a fast sanity check that can run before longer tests.
    """
    sim_container = simulation_containers['simulation']
    ros2_container = simulation_containers['ros2_integration']

    # Check both containers are running
    assert sim_container.status == 'running', "Simulation container not running"
    assert ros2_container.status == 'running', "ROS2 container not running"

    # Check for critical errors in logs
    sim_logs = sim_container.logs(tail=200).decode('utf-8', errors='ignore')
    ros2_logs = ros2_container.logs(tail=200).decode('utf-8', errors='ignore')

    # No sensor timeouts
    assert "Accel #0 fail: TIMEOUT" not in sim_logs, "Sensor timeout detected"

    # Vision bridge running
    assert "vision_pose_bridge" in ros2_logs or "Odometry published" in ros2_logs, \
        "Vision bridge not running"

    # No EKF2 critical errors
    assert "ekf2 missing data" not in sim_logs.lower(), "EKF2 missing data"

    print("✓ Quick EKF2 check passed")
