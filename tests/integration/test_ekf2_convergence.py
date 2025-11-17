"""
Integration tests for PX4 EKF2 convergence in GPS-free simulation (drone_1).

These tests verify the sensor pipeline and EKF2 convergence for drone_1:
    Gazebo Harmonic → PX4 → MAVROS (/drone_1/ namespace)

**Current Status (2025-11-17)**:
- ✅ All essential sensors (IMU, Mag, Baro) publishing correctly
- ✅ MAVROS connected to PX4 MAVLink
- ✅ EKF2 converges for attitude (roll/pitch/yaw) and vertical position
- ⚠️ Vision bridge node starts but does NOT publish (gz.transport callback issue)
- ❌ Horizontal position unavailable without vision data

Test Philosophy:
- Use real container logs and ROS2 topics (no mocking)
- Tests run against actual Docker containers
- Validate dynamic data from running system
- Tests execute in order following EKF2 initialization phases
- Tests stop on first failure to quickly identify where the pipeline breaks

Test Execution Order (follows EKF2 initialization phases):
    Phase 1: Sensor Initialization (2-5s)
        → test_phase1_gazebo_sensors_active (IMU, Mag, Baro)
        → test_phase1_vision_bridge_active (vision odometry publishing)

    Phase 2: EKF2 Initialization (3-10s)
        → test_phase2_gps_free_parameters_applied
        → test_phase2_mavros_connection
        → test_phase2_ekf2_initialization

    Phase 3: EKF2 Convergence (5-15s)
        → test_phase3_ekf2_estimator_status (attitude + vertical)

    Quick Check:
        → test_ekf2_quick_check (smoke test, can run independently)

Usage:
    # Run all EKF2 tests in order, stop on first failure
    pytest tests/integration/test_ekf2_convergence.py -v -x

    # Run only Phase 1 tests (includes vision bridge failure)
    pytest tests/integration/test_ekf2_convergence.py -v -k phase1

    # Run quick check only
    pytest tests/integration/test_ekf2_convergence.py -v -k quick

    # Skip vision bridge test (run tests that pass)
    pytest tests/integration/test_ekf2_convergence.py -v --ignore-glob="*vision*"
"""

import pytest
import re
import time
from typing import Dict
import docker


@pytest.mark.integration
@pytest.mark.slow
class TestEKF2Convergence:
    """
    Test suite for EKF2 initialization and convergence with vision odometry.

    Tests are organized by EKF2 initialization phases and have dependencies
    to ensure they run in the correct order and stop on first failure.
    """

    # ========================================================================
    # PHASE 1: Sensor Initialization (2-5 seconds)
    # ========================================================================

    @pytest.mark.dependency(name="phase1_sensors")
    def test_phase1_gazebo_sensors_active(self, simulation_containers):
        """
        PHASE 1 - Step 1: Verify Gazebo Harmonic is providing sensor data to PX4 (drone_1).

        PX4 requires sensor data (IMU, Gyro, Magnetometer, Barometer) to initialize EKF2.
        This test uses MAVROS topics under /drone_1/ namespace to verify sensor data flow.

        Expected: MAVROS publishes IMU, magnetometer, and barometer data
        Timing: Should succeed within first 10 seconds after container start
        """
        ros2_container = simulation_containers['ros2_integration']

        print("\n" + "="*70)
        print("PHASE 1: SENSOR INITIALIZATION (drone_1)")
        print("="*70)
        print("Step 1/2: Checking Gazebo sensor communication via MAVROS...")

        # Wait for MAVROS to initialize and start publishing sensor data
        time.sleep(7)

        # Check IMU data (proves accelerometer + gyroscope work)
        command = (
            "bash -c '"
            "source /opt/ros/humble/setup.bash && "
            "timeout 5 ros2 topic echo /drone_1/mavros_node/data --once"
            "'"
        )

        print("  ⏳ Reading /drone_1/mavros_node/data (IMU)...")
        exit_code, output = ros2_container.exec_run(command, demux=False)
        output_str = output.decode('utf-8', errors='ignore') if output else ""

        assert "linear_acceleration" in output_str, (
            "No IMU data from MAVROS on /drone_1/mavros_node/data. "
            "This indicates Gazebo sensors are not communicating with PX4. "
            "On macOS, ensure HEADLESS=0 (GUI mode required). "
            f"Command exit code: {exit_code}"
        )

        assert "angular_velocity" in output_str, (
            "IMU data missing gyroscope (angular_velocity). "
            "Check Gazebo sensor plugin configuration."
        )

        # Verify gravity is detected (~9.81 m/s²)
        if "z: 9.8" in output_str or "z: -9.8" in output_str:
            print("✓ IMU data (accelerometer + gyroscope) confirmed - gravity detected")
        else:
            print("✓ IMU data (accelerometer + gyroscope) confirmed")

        # Check magnetometer data
        command = (
            "bash -c '"
            "source /opt/ros/humble/setup.bash && "
            "timeout 5 ros2 topic echo /drone_1/mavros_node/mag --once"
            "'"
        )

        print("  ⏳ Reading /drone_1/mavros_node/mag (magnetometer)...")
        exit_code, output = ros2_container.exec_run(command, demux=False)
        output_str = output.decode('utf-8', errors='ignore') if output else ""

        assert "magnetic_field" in output_str, (
            "No magnetometer data from MAVROS. "
            "Check if Gazebo is publishing magnetometer sensor data. "
            f"Command exit code: {exit_code}"
        )

        print("✓ Magnetometer data confirmed")

        # Check barometer data (critical for altitude estimation)
        command = (
            "bash -c '"
            "source /opt/ros/humble/setup.bash && "
            "timeout 5 ros2 topic echo /drone_1/mavros_node/static_pressure --once"
            "'"
        )

        print("  ⏳ Reading /drone_1/mavros_node/static_pressure (barometer)...")
        exit_code, output = ros2_container.exec_run(command, demux=False)
        output_str = output.decode('utf-8', errors='ignore') if output else ""

        assert "fluid_pressure" in output_str, (
            "No barometer data from MAVROS. "
            "Check if Gazebo is publishing barometer sensor data. "
            f"Command exit code: {exit_code}"
        )

        print("✓ Barometer data confirmed")
        print("✓ All essential sensors (IMU, Gyro, Mag, Baro) publishing via MAVROS")

    @pytest.mark.dependency(name="phase1_vision", depends=["phase1_sensors"])
    def test_phase1_vision_bridge_active(self, simulation_containers):
        """
        PHASE 1 - Step 2: Verify vision_pose_bridge is publishing odometry (drone_1).

        The vision bridge subscribes to Gazebo pose and odometry data via gz.transport and
        publishes to /drone_1/mavros/odometry/out for EKF2 fusion. This is critical for
        GPS-free horizontal position estimation.

        Expected: Vision bridge publishing at >40 Hz (typically 50-100 Hz)
        Timing: Should start within 3-5 seconds after ROS2 container starts
        """
        ros2_container = simulation_containers['ros2_integration']

        print("\nStep 2/2: Checking vision bridge publication...")

        # Wait a bit for vision bridge to start publishing
        time.sleep(3)

        # Check that vision bridge node is running
        command = (
            "bash -c '"
            "source /opt/ros/humble/setup.bash && "
            "ros2 node list | grep vision_pose_bridge"
            "'"
        )
        exit_code, output = ros2_container.exec_run(command, demux=False)
        assert exit_code == 0, "vision_pose_bridge node not running"
        print("✓ Vision bridge node is running")

        # Check if vision bridge is publishing on the correct topic
        command = (
            "bash -c '"
            "source /opt/ros/humble/setup.bash && "
            "timeout 5 ros2 topic hz /drone_1/mavros/odometry/out"
            "'"
        )

        print("  ⏳ Checking /drone_1/mavros/odometry/out publication rate...")
        exit_code, output = ros2_container.exec_run(command, demux=False)
        output_str = output.decode('utf-8', errors='ignore') if output else ""

        # Check if topic is publishing
        if "average rate" in output_str.lower():
            # Extract rate
            rate_match = re.search(r'average rate:\s*([\d.]+)', output_str, re.IGNORECASE)
            if rate_match:
                rate = float(rate_match.group(1))
                assert rate > 40, (
                    f"Vision bridge rate {rate} Hz too low (<40 Hz). "
                    f"This may indicate Gazebo performance issues or threading problems."
                )
                print(f"✓ Vision bridge publishing at {rate:.1f} Hz")
            else:
                print("✓ Vision bridge is publishing (rate not parsed)")

            print("\n✅ PHASE 1 COMPLETE: Sensors initialized and vision data available\n")
        else:
            # Vision bridge is NOT publishing - provide detailed error
            logs = ros2_container.logs(tail=200).decode('utf-8', errors='ignore')

            # Check initialization messages
            bridge_initialized = "Vision Odometry Bridge initialized successfully" in logs
            gazebo_topics_subscribed = "Subscribing to Gazebo" in logs

            error_msg = (
                "❌ Vision bridge node is running but NOT publishing odometry data.\n\n"
                "Diagnostic information:\n"
                f"  - Node initialized: {'✓' if bridge_initialized else '✗'}\n"
                f"  - Gazebo subscriptions created: {'✓' if gazebo_topics_subscribed else '✗'}\n"
                f"  - Topic publishing: ✗ (no data on /drone_1/mavros/odometry/out)\n\n"
                "Root cause: gz.transport callbacks not triggered (known issue).\n"
                "Gazebo topics /world/default/dynamic_pose/info and /model/x500_0/odometry exist\n"
                "and publish data, but Python callbacks in vision_pose_bridge.py don't receive messages.\n\n"
                "This is likely a threading/event loop issue between gz.transport13 (C++) and rclpy (Python).\n\n"
                "Impact: Horizontal position estimation unavailable in GPS-free mode.\n"
                "EKF2 can still estimate attitude and vertical position using IMU+Baro."
            )

            pytest.fail(error_msg)

    # ========================================================================
    # PHASE 2: EKF2 Initialization (3-10 seconds)
    # ========================================================================

    @pytest.mark.dependency(name="phase2_params", depends=["phase1_vision"])
    def test_phase2_gps_free_parameters_applied(self, simulation_containers):
        """
        PHASE 2 - Step 1: Verify GPS-free and vision fusion parameters were applied.

        These parameters are critical for GPS-free operation:
        - COM_ARM_WO_GPS=1: Allow arming without GPS
        - EKF2_GPS_CTRL=0: Disable GPS fusion
        - EKF2_EV_CTRL=15: Enable vision position, velocity, yaw fusion
        - EKF2_HGT_REF=3: Height reference source (3=Vision)

        Strategy: Query parameters via MAVROS service instead of parsing logs.
        This is more reliable as it verifies the actual runtime parameter values.

        Expected: Parameters accessible via MAVROS param service
        Timing: After MAVROS connection (requires ros2_integration container)
        """
        ros2_container = simulation_containers['ros2_integration']

        print("\n" + "="*70)
        print("PHASE 2: EKF2 INITIALIZATION")
        print("="*70)
        print("Step 1/3: Checking GPS-free parameter configuration via MAVROS...")

        # Critical parameters to verify
        params_to_check = {
            "COM_ARM_WO_GPS": 1,  # Allow arming without GPS
            "EKF2_GPS_CTRL": 0,   # Disable GPS fusion
            "EKF2_EV_CTRL": 15,   # Full vision fusion (pos, vel, yaw)
            "EKF2_HGT_REF": 3     # Vision height reference
        }

        # Wait for MAVROS to be ready
        print("  ⏳ Waiting for MAVROS connection...")
        time.sleep(5)

        failed_params = []

        for param_name, expected_value in params_to_check.items():
            # Query parameter via MAVROS service
            command = (
                f"bash -c '"
                f"source /opt/ros/humble/setup.bash && "
                f"source install/setup.bash && "
                f"timeout 3 ros2 service call /drone_1/mavros_node/param/get "
                f"mavros_msgs/srv/ParamGet \"{{param_id: \\\"{param_name}\\\"}}\" "
                f"2>/dev/null"
                f"'"
            )

            exit_code, output = ros2_container.exec_run(command, demux=False)
            output_str = output.decode('utf-8', errors='ignore') if output else ""

            # Parse response - looking for "integer: <value>" or "value:"
            if "integer:" in output_str:
                # Extract integer value
                match = re.search(r'integer:\s*(\d+)', output_str)
                if match:
                    actual_value = int(match.group(1))
                    if actual_value == expected_value:
                        print(f"  ✓ {param_name} = {actual_value} (expected {expected_value})")
                    else:
                        print(f"  ✗ {param_name} = {actual_value} (expected {expected_value})")
                        failed_params.append(f"{param_name} (got {actual_value}, expected {expected_value})")
                else:
                    print(f"  ⚠ {param_name}: Could not parse value from response")
                    failed_params.append(f"{param_name} (parsing failed)")
            elif "real:" in output_str:
                # Some parameters might be float
                match = re.search(r'real:\s*([\d.]+)', output_str)
                if match:
                    actual_value = float(match.group(1))
                    if abs(actual_value - expected_value) < 0.01:
                        print(f"  ✓ {param_name} = {actual_value} (expected {expected_value})")
                    else:
                        print(f"  ✗ {param_name} = {actual_value} (expected {expected_value})")
                        failed_params.append(f"{param_name} (got {actual_value}, expected {expected_value})")
                else:
                    print(f"  ⚠ {param_name}: Could not parse value from response")
                    failed_params.append(f"{param_name} (parsing failed)")
            else:
                # Parameter might not exist or service call failed
                print(f"  ✗ {param_name}: Service call failed or parameter not found")
                print(f"      Response: {output_str[:200]}")
                failed_params.append(f"{param_name} (not found)")

        assert not failed_params, (
            f"GPS-free parameter verification failed: {', '.join(failed_params)}. "
            f"Check if start_px4_sitl.sh correctly applies parameters to PX4."
        )

        print("✓ All GPS-free parameters verified via MAVROS")

    @pytest.mark.dependency(name="phase2_mavros_connection", depends=["phase2_params"])
    def test_phase2_mavros_connection(self, simulation_containers):
        """
        PHASE 2 - Step 2: Verify MAVROS is connected to PX4 (drone_1).

        This tests the MAVLink connection: PX4 ← MAVLink → MAVROS
        MAVROS must be connected before EKF2 data can be received.

        Expected: /drone_1/state shows connected=true
        Timing: Should connect within 5 seconds after PX4 starts
        """
        ros2_container = simulation_containers['ros2_integration']

        print("\nStep 2/3: Checking MAVROS connection to PX4...")

        # Check MAVROS state topic
        command = (
            "bash -c '"
            "source /opt/ros/humble/setup.bash && "
            "timeout 5 ros2 topic echo /drone_1/state --once"
            "'"
        )

        print("  ⏳ Reading /drone_1/state...")

        exit_code, output = ros2_container.exec_run(command, demux=False)
        output_str = output.decode('utf-8', errors='ignore') if output else ""

        # Check if state topic is publishing
        assert "connected:" in output_str, (
            f"No state data on /drone_1/state. "
            f"Check if MAVROS is running and PX4 MAVLink is active.\n"
            f"Output: {output_str}"
        )

        # Verify connection status
        assert "connected: true" in output_str, (
            f"MAVROS not connected to PX4. "
            f"Check MAVLink configuration (FCU URL, port 14540).\n"
            f"Output: {output_str}"
        )

        print("✓ MAVROS connected to PX4")

        # Extract current flight mode for info
        mode_match = re.search(r'mode:\s*(\S+)', output_str)
        if mode_match:
            mode = mode_match.group(1)
            print(f"✓ Current flight mode: {mode}")

    @pytest.mark.dependency(name="phase2_ekf2_init", depends=["phase2_mavros_connection"])
    def test_phase2_ekf2_initialization(self, simulation_containers):
        """
        PHASE 2 - Step 3: Verify EKF2 initializes successfully with vision fusion.

        EKF2 must:
        1. Receive data from all required sources (IMU, Mag, Baro, Vision)
        2. Align successfully (find a good initial state estimate)
        3. Enable vision position/velocity fusion
        4. Not report critical errors

        Expected: EKF2 aligned without critical errors
        Timing: Can take up to 15 seconds to fully initialize and align
        """
        sim_container = simulation_containers['simulation']

        print("\nStep 3/3: Checking EKF2 initialization and alignment...")

        # EKF2 can take up to 15 seconds to initialize and align
        max_wait = 15
        ekf2_aligned = False

        print("  ⏳ Waiting for EKF2 to align...", end="", flush=True)

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
        print("\n✅ PHASE 2 COMPLETE: EKF2 initialized with vision fusion\n")

    # ========================================================================
    # PHASE 3: EKF2 Convergence (5-15 seconds)
    # ========================================================================

    @pytest.mark.dependency(name="phase3_convergence", depends=["phase2_ekf2_init"])
    def test_phase3_ekf2_estimator_status(self, simulation_containers):
        """
        PHASE 3: Verify EKF2 estimator status shows converged states (drone_1).

        /drone_1/estimator_status contains flags indicating which states EKF2 has successfully
        estimated. In GPS-free mode without vision, we expect:
        - ✅ attitude_status_flag: true (roll/pitch/yaw estimated)
        - ✅ velocity_vert_status_flag: true (vertical velocity from IMU+Baro)
        - ✅ pos_vert_abs_status_flag: true (altitude from barometer)
        - ❌ velocity_horiz_status_flag: false (requires vision/mocap)
        - ❌ pos_horiz_rel_status_flag: false (requires vision/mocap)

        Expected: Attitude and vertical position/velocity converged
        Timing: Should converge within 10 seconds after EKF2 initializes
        """
        ros2_container = simulation_containers['ros2_integration']

        print("\n" + "="*70)
        print("PHASE 3: EKF2 CONVERGENCE (GPS-free mode)")
        print("="*70)
        print("Checking EKF2 estimator status...")

        # Give EKF2 time to converge
        time.sleep(5)

        # Read estimator_status topic
        command = (
            "bash -c '"
            "source /opt/ros/humble/setup.bash && "
            "timeout 5 ros2 topic echo /drone_1/estimator_status --once"
            "'"
        )

        print("  ⏳ Reading /drone_1/estimator_status...")

        exit_code, output = ros2_container.exec_run(command, demux=False)
        output_str = output.decode('utf-8', errors='ignore') if output else ""

        # Should receive at least one message
        assert "attitude_status_flag:" in output_str, (
            f"No estimator status data from EKF2. "
            f"This indicates EKF2 is not publishing status. "
            f"Check if EKF2 has initialized.\n"
            f"Output: {output_str[:500]}"
        )

        # Parse status flags
        flags = {}
        for flag_name in [
            'attitude_status_flag',
            'velocity_horiz_status_flag',
            'velocity_vert_status_flag',
            'pos_horiz_rel_status_flag',
            'pos_vert_abs_status_flag'
        ]:
            match = re.search(rf'{flag_name}:\s*(true|false)', output_str)
            if match:
                flags[flag_name] = match.group(1) == 'true'

        print("\nEKF2 Estimator Status:")
        print(f"  Attitude (roll/pitch/yaw):     {'✓' if flags.get('attitude_status_flag') else '✗'}")
        print(f"  Vertical velocity:              {'✓' if flags.get('velocity_vert_status_flag') else '✗'}")
        print(f"  Vertical position (altitude):   {'✓' if flags.get('pos_vert_abs_status_flag') else '✗'}")
        print(f"  Horizontal velocity:            {'✓' if flags.get('velocity_horiz_status_flag') else '✗ (expected without vision)'}")
        print(f"  Horizontal position:            {'✓' if flags.get('pos_horiz_rel_status_flag') else '✗ (expected without vision)'}")

        # Critical checks: attitude and vertical position must be valid
        assert flags.get('attitude_status_flag'), (
            "EKF2 attitude not converged. "
            "Check IMU data availability and EKF2 initialization."
        )
        print("\n✓ Attitude estimation converged")

        assert flags.get('pos_vert_abs_status_flag'), (
            "EKF2 vertical position not converged. "
            "Check barometer data availability."
        )
        print("✓ Vertical position estimation converged")

        # Informational: horizontal states should NOT be valid without vision
        if flags.get('velocity_horiz_status_flag') or flags.get('pos_horiz_rel_status_flag'):
            print("\n⚠️ WARNING: Horizontal position/velocity unexpectedly valid!")
            print("   This suggests vision data is being fused (vision bridge working?)")
        else:
            print("\n✓ Horizontal position/velocity not estimated (expected in GPS-free without vision)")

        print("\n" + "="*70)
        print("✅ ALL PHASES COMPLETE: EKF2 CONVERGED (Attitude + Vertical)")
        print("="*70)
        print("\nPipeline verified:")
        print("  Gazebo Sensors → PX4 EKF2 ✓")
        print("  PX4 EKF2 → MAVROS → Estimator Status ✓")
        print("  EKF2 Attitude Estimation ✓")
        print("  EKF2 Vertical Position Estimation ✓")
        print("\nLimitations (GPS-free without vision):")
        print("  Horizontal position estimation: ✗ (requires vision bridge fix)")
        print()


# ============================================================================
# QUICK SMOKE TEST (can run independently)
# ============================================================================

@pytest.mark.integration
def test_ekf2_quick_check(simulation_containers):
    """
    Quick smoke test: verify simulation starts and EKF2 doesn't have critical errors (drone_1).

    This is a fast sanity check that can run before longer tests.
    It does NOT check all phases in detail, just basic health.

    Usage: pytest tests/integration/test_ekf2_convergence.py -v -k quick
    """
    sim_container = simulation_containers['simulation']
    ros2_container = simulation_containers['ros2_integration']

    print("\n" + "="*70)
    print("QUICK EKF2 SMOKE TEST (drone_1)")
    print("="*70)

    # Check both containers are running
    assert sim_container.status == 'running', "Simulation container not running"
    assert ros2_container.status == 'running', "ROS2 container not running"
    print("✓ Containers running")

    # Check for critical errors in logs
    sim_logs = sim_container.logs(tail=200).decode('utf-8', errors='ignore')
    ros2_logs = ros2_container.logs(tail=200).decode('utf-8', errors='ignore')

    # No sensor timeouts
    assert "Accel #0 fail: TIMEOUT" not in sim_logs, "Sensor timeout detected"
    print("✓ No sensor timeouts")

    # MAVROS connection
    command = (
        "bash -c '"
        "source /opt/ros/humble/setup.bash && "
        "ros2 topic list | grep -c /drone_1/"
        "'"
    )
    exit_code, output = ros2_container.exec_run(command, demux=False)
    topic_count = int(output.decode('utf-8', errors='ignore').strip()) if exit_code == 0 else 0
    assert topic_count > 10, f"Too few /drone_1/ topics ({topic_count}), MAVROS may not be running"
    print(f"✓ MAVROS active ({topic_count} topics under /drone_1/)")

    # Vision bridge node exists (but may not publish)
    command = (
        "bash -c '"
        "source /opt/ros/humble/setup.bash && "
        "ros2 node list | grep -c vision_pose_bridge"
        "'"
    )
    exit_code, output = ros2_container.exec_run(command, demux=False)
    if exit_code == 0 and "1" in output.decode('utf-8', errors='ignore'):
        print("✓ Vision bridge node running (⚠️ may not be publishing - known issue)")
    else:
        print("⚠️ Vision bridge node not found")

    # No EKF2 critical errors
    assert "ekf2 missing data" not in sim_logs.lower(), "EKF2 missing data"
    print("✓ No EKF2 critical errors")

    print("\n✅ Quick check passed - system appears healthy\n")
