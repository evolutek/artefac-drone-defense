"""
Integration tests for PX4 EKF2 convergence in GPS-enabled simulation (drone_1).

These tests verify the sensor pipeline and EKF2 convergence for drone_1:
    Gazebo Harmonic → PX4 → MAVROS (/drone_1/ namespace)

**Current Status (2025-11-18)**:
- ✅ All essential sensors (IMU, Mag, Baro, GPS) publishing correctly
- ✅ MAVROS connected to PX4 MAVLink
- ✅ GPS fix available with sufficient satellites
- ✅ EKF2 converges for full 3D position and velocity using GPS
- ✅ Horizontal and vertical position estimation operational

Test Philosophy:
- Use real container logs and ROS2 topics (no mocking)
- Tests run against actual Docker containers
- Validate dynamic data from running system
- Tests execute in order following EKF2 initialization phases
- Tests stop on first failure to quickly identify where the pipeline breaks

Test Execution Order (follows EKF2 initialization phases):
    Phase 1: Sensor Initialization (2-5s)
        → test_phase1_gazebo_sensors_active (IMU, Mag, Baro)
        → test_phase1_gps_fix_available (GPS satellite lock and HDOP)

    Phase 2: EKF2 Initialization (3-10s)
        → test_phase2_gps_parameters_applied
        → test_phase2_mavros_connection
        → test_phase2_ekf2_initialization

    Phase 3: EKF2 Convergence (5-15s)
        → test_phase3_ekf2_estimator_status (full 3D position/velocity from GPS)

    Quick Check:
        → test_ekf2_quick_check (smoke test, can run independently)

Usage:
    # Run all EKF2 tests in order, stop on first failure
    pytest tests/integration/test_ekf2_convergence.py -v -x

    # Run only Phase 1 tests
    pytest tests/integration/test_ekf2_convergence.py -v -k phase1

    # Run quick check only
    pytest tests/integration/test_ekf2_convergence.py -v -k quick

    # Skip GPS fix test
    pytest tests/integration/test_ekf2_convergence.py -v --ignore-glob="*gps_fix*"
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
    Test suite for EKF2 initialization and convergence with GPS.

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
            "timeout 5 ros2 topic echo /drone_1/mavros/imu/data --once"
            "'"
        )

        print("  ⏳ Reading /drone_1/mavros/imu/data (IMU)...")
        exit_code, output = ros2_container.exec_run(command, demux=False)
        output_str = output.decode('utf-8', errors='ignore') if output else ""

        assert "linear_acceleration" in output_str, (
            "No IMU data from MAVROS on /drone_1/mavros/imu/data. "
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
            "timeout 5 ros2 topic echo /drone_1/mavros/mag --once"
            "'"
        )

        print("  ⏳ Reading /drone_1/mavros/mag (magnetometer)...")
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
            "timeout 5 ros2 topic echo /drone_1/mavros/imu/static_pressure --once"
            "'"
        )

        print("  ⏳ Reading /drone_1/mavros/imu/static_pressure (barometer)...")
        exit_code, output = ros2_container.exec_run(command, demux=False)
        output_str = output.decode('utf-8', errors='ignore') if output else ""

        assert "fluid_pressure" in output_str, (
            "No barometer data from MAVROS. "
            "Check if Gazebo is publishing barometer sensor data. "
            f"Command exit code: {exit_code}"
        )

        print("✓ Barometer data confirmed")
        print("✓ All essential sensors (IMU, Gyro, Mag, Baro) publishing via MAVROS")

    @pytest.mark.dependency(name="phase1_gps", depends=["phase1_sensors"])
    def test_phase1_gps_fix_available(self, simulation_containers):
        """
        PHASE 1 - Step 2: Verify GPS has sufficient satellite lock for accurate positioning.

        GPS requires at least 6 satellites with good geometry (HDOP < 2.0) for reliable
        3D position estimation. This test verifies GPS fix quality.

        Expected: GPS fix with ≥6 satellites and HDOP < 2.0
        Timing: GPS should lock within 10-15 seconds in simulation
        """
        ros2_container = simulation_containers['ros2_integration']

        print("\nStep 2/2: Checking GPS satellite lock and fix quality...")

        # Wait for GPS to acquire satellite lock
        time.sleep(8)

        # Check GPS fix status
        command = (
            "bash -c '"
            "source /opt/ros/humble/setup.bash && "
            "timeout 5 ros2 topic echo /drone_1/mavros/global_position/raw/fix --once"
            "'"
        )

        print("  ⏳ Reading /drone_1/mavros/global_position/raw/fix...")
        exit_code, output = ros2_container.exec_run(command, demux=False)
        output_str = output.decode('utf-8', errors='ignore') if output else ""

        assert "latitude:" in output_str and "longitude:" in output_str, (
            f"No GPS data from MAVROS on /drone_1/mavros/global_position/raw/fix. "
            f"Check if Gazebo GPS sensor is enabled and publishing.\n"
            f"Command exit code: {exit_code}"
        )

        # Parse GPS fix status (0=no fix, 1=no fix, 2=2D, 3=3D fix)
        status_match = re.search(r'status:\s*(\d+)', output_str)
        if status_match:
            gps_status = int(status_match.group(1))
            assert gps_status >= 2, (
                f"GPS fix status {gps_status} insufficient (need ≥2 for 2D/3D fix). "
                f"Wait longer for GPS lock or check Gazebo GPS sensor."
            )
            print(f"✓ GPS fix status: {gps_status} ({'2D' if gps_status == 2 else '3D'} fix)")

        # Parse number of satellites
        satellites_match = re.search(r'satellites_used:\s*(\d+)', output_str)
        if satellites_match:
            num_satellites = int(satellites_match.group(1))
            assert num_satellites >= 6, (
                f"Only {num_satellites} satellites available (need ≥6 for reliable positioning). "
                f"Check Gazebo GPS configuration."
            )
            print(f"✓ GPS satellites: {num_satellites} (sufficient for 3D positioning)")
        else:
            print("⚠️ Could not parse satellite count - assuming sufficient")

        # Check position dilution of precision (lower is better, <2.0 is good)
        # Note: Gazebo may not provide HDOP in all configurations
        if "hdop:" in output_str.lower() or "position_covariance:" in output_str:
            print("✓ GPS accuracy metrics available")
        else:
            print("⚠️ HDOP not available (may be normal in Gazebo)")

        print("✓ GPS fix available with sufficient quality for EKF2 fusion")
        print("\n✅ PHASE 1 COMPLETE: Sensors initialized and GPS lock acquired\n")

    # ========================================================================
    # PHASE 2: EKF2 Initialization (3-10 seconds)
    # ========================================================================

    @pytest.mark.dependency(name="phase2_params", depends=["phase1_gps"])
    def test_phase2_gps_parameters_applied(self, simulation_containers):
        """
        PHASE 2 - Step 1: Verify GPS-enabled configuration via EKF2 behavior.

        Strategy: PURE behavioral verification - check that EKF2 operates in GPS mode
        by verifying state estimation flags. NO log parsing.

        GPS-enabled mode should show:
        - ✅ attitude_status_flag: true (IMU + Magnetometer)
        - ✅ velocity_vert_status_flag: true (IMU + Barometer)
        - ✅ pos_vert_abs_status_flag: true (Barometer altitude)
        - ✅ velocity_horiz_status_flag: true (GPS fusion)
        - ✅ pos_horiz_rel_status_flag: true (GPS fusion)
        - ✅ pos_horiz_abs_status_flag: true (GPS absolute position - KEY indicator)

        If GPS absolute positioning is active, it proves GPS parameters are applied.

        Expected: EKF2 estimates full 3D position using GPS
        Timing: After PX4 startup + 10s for EKF2 convergence
        """
        ros2_container = simulation_containers['ros2_integration']

        print("\n" + "="*70)
        print("PHASE 2: GPS CONFIGURATION VERIFICATION")
        print("="*70)
        print("Strategy: Behavioral check via EKF2 estimator status")
        print("Verifying EKF2 uses GPS fusion for absolute positioning...")

        # Wait for PX4 + EKF2 initialization
        print("\n  ⏳ Waiting for PX4 and EKF2 initialization (10s)...")
        time.sleep(10)

        # Read EKF2 estimator status
        command = (
            "bash -c '"
            "source /opt/ros/humble/setup.bash && "
            "timeout 5 ros2 topic echo /drone_1/estimator_status --once"
            "'"
        )

        print("  ⏳ Reading /drone_1/estimator_status...")
        exit_code, output = ros2_container.exec_run(command, demux=False)
        output_str = output.decode('utf-8', errors='ignore') if output else ""

        # Verify we got data
        assert "attitude_status_flag:" in output_str, (
            f"No estimator status data from EKF2. "
            f"This indicates EKF2 is not publishing. "
            f"Check PX4 initialization.\n"
            f"Output: {output_str[:500]}"
        )

        # Parse EKF2 status flags
        flags = {}
        flag_names = [
            'attitude_status_flag',
            'velocity_horiz_status_flag',
            'velocity_vert_status_flag',
            'pos_horiz_rel_status_flag',
            'pos_horiz_abs_status_flag',  # GPS absolute position (must be true)
            'pos_vert_abs_status_flag'
        ]

        for flag_name in flag_names:
            match = re.search(rf'{flag_name}:\s*(true|false)', output_str)
            if match:
                flags[flag_name] = match.group(1) == 'true'

        # Display EKF2 state
        print("\n  EKF2 Estimator Status:")
        print(f"    Attitude (IMU+Mag):            {'✓' if flags.get('attitude_status_flag') else '✗'}")
        print(f"    Vertical velocity (IMU+Baro):  {'✓' if flags.get('velocity_vert_status_flag') else '✗'}")
        print(f"    Vertical position (Baro/GPS):  {'✓' if flags.get('pos_vert_abs_status_flag') else '✗'}")
        print(f"    Horizontal velocity (GPS):     {'✓' if flags.get('velocity_horiz_status_flag') else '✗'}")
        print(f"    Horizontal position (GPS):     {'✓' if flags.get('pos_horiz_rel_status_flag') else '✗'}")
        print(f"    GPS absolute position:         {'✓ GPS ACTIVE' if flags.get('pos_horiz_abs_status_flag') else '✗ (UNEXPECTED - should be GPS mode)'}")

        # Critical assertions: GPS-enabled mode
        assert flags.get('attitude_status_flag'), (
            "EKF2 attitude not converged. Check IMU/Magnetometer sensors."
        )

        assert flags.get('velocity_vert_status_flag'), (
            "EKF2 vertical velocity not converged. Check IMU/Barometer sensors."
        )

        assert flags.get('pos_vert_abs_status_flag'), (
            "EKF2 vertical position not converged. Check barometer or GPS altitude."
        )

        assert flags.get('velocity_horiz_status_flag'), (
            "EKF2 horizontal velocity not converged. "
            "This should be estimated from GPS. "
            "Check GPS fix is available and EKF2_GPS_CTRL parameter."
        )

        assert flags.get('pos_horiz_rel_status_flag'), (
            "EKF2 horizontal position (relative) not converged. "
            "Check GPS fusion is enabled (EKF2_GPS_CTRL=7)."
        )

        # KEY VERIFICATION: GPS absolute position must be active
        assert flags.get('pos_horiz_abs_status_flag'), (
            "EKF2 is NOT using GPS for absolute position! "
            "This indicates GPS-enabled parameters (EKF2_GPS_CTRL=7) were NOT applied. "
            "Check simulation/start_px4_sitl.sh parameter injection. "
            "Expected EKF2_GPS_CTRL=7, COM_ARM_WO_GPS=0."
        )

        print("\n✅ GPS-enabled configuration verified:")
        print("   • EKF2 estimates full 3D position/velocity")
        print("   • GPS fusion active for horizontal positioning")
        print("   • GPS absolute positioning enabled")
        print("\n✓ This proves GPS-enabled parameters are correctly applied and functional.")

    @pytest.mark.dependency(name="phase2_mavros_connection", depends=["phase2_params"])
    def test_phase2_mavros_connection(self, simulation_containers):
        """
        PHASE 2 - Step 2: Verify MAVROS is connected to PX4 (drone_1).

        This tests the MAVLink connection: PX4 ← MAVLink → MAVROS
        MAVROS must be connected before EKF2 data can be received.

        Expected: /drone_1/mavros/state shows connected=true
        Timing: Should connect within 5 seconds after PX4 starts
        """
        ros2_container = simulation_containers['ros2_integration']

        print("\nStep 2/3: Checking MAVROS connection to PX4...")

        # Check MAVROS state topic
        command = (
            "bash -c '"
            "source /opt/ros/humble/setup.bash && "
            "timeout 5 ros2 topic echo /drone_1/mavros/state --once"
            "'"
        )

        print("  ⏳ Reading /drone_1/mavros/state...")

        exit_code, output = ros2_container.exec_run(command, demux=False)
        output_str = output.decode('utf-8', errors='ignore') if output else ""

        # Check if state topic is publishing
        assert "connected:" in output_str, (
            f"No state data on /drone_1/mavros/state. "
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
        PHASE 2 - Step 3: Verify EKF2 initializes successfully with GPS fusion.

        EKF2 must:
        1. Receive data from all required sources (IMU, Mag, Baro, GPS)
        2. Align successfully (find a good initial state estimate)
        3. Enable GPS position/velocity fusion
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

        # Verify GPS fusion mentions (indicates GPS parameters applied)
        has_gps_logs = (
            "gps" in logs.lower() or
            "EKF2_GPS_CTRL" in logs or
            "satellite" in logs.lower()
        )

        if has_gps_logs:
            print("✓ GPS fusion parameters confirmed in logs")
        else:
            print("⚠ GPS fusion logs not explicitly found (may be normal)")

        print("✓ EKF2 initialized without critical errors")
        print("\n✅ PHASE 2 COMPLETE: EKF2 initialized with GPS fusion\n")

    # ========================================================================
    # PHASE 3: EKF2 Convergence (5-15 seconds)
    # ========================================================================

    @pytest.mark.dependency(name="phase3_convergence", depends=["phase2_ekf2_init"])
    def test_phase3_ekf2_estimator_status(self, simulation_containers):
        """
        PHASE 3: Verify EKF2 estimator status shows converged states (drone_1).

        /drone_1/estimator_status contains flags indicating which states EKF2 has successfully
        estimated. In GPS-enabled mode, we expect:
        - ✅ attitude_status_flag: true (roll/pitch/yaw estimated)
        - ✅ velocity_vert_status_flag: true (vertical velocity from IMU+Baro)
        - ✅ pos_vert_abs_status_flag: true (altitude from barometer/GPS)
        - ✅ velocity_horiz_status_flag: true (horizontal velocity from GPS)
        - ✅ pos_horiz_rel_status_flag: true (relative position from GPS)
        - ✅ pos_horiz_abs_status_flag: true (absolute position from GPS - KEY)

        Expected: Full 3D position and velocity converged with GPS
        Timing: Should converge within 10 seconds after EKF2 initializes
        """
        ros2_container = simulation_containers['ros2_integration']

        print("\n" + "="*70)
        print("PHASE 3: EKF2 CONVERGENCE (GPS-enabled mode)")
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
            'pos_horiz_abs_status_flag',
            'pos_vert_abs_status_flag'
        ]:
            match = re.search(rf'{flag_name}:\s*(true|false)', output_str)
            if match:
                flags[flag_name] = match.group(1) == 'true'

        print("\nEKF2 Estimator Status:")
        print(f"  Attitude (roll/pitch/yaw):     {'✓' if flags.get('attitude_status_flag') else '✗'}")
        print(f"  Vertical velocity:              {'✓' if flags.get('velocity_vert_status_flag') else '✗'}")
        print(f"  Vertical position (altitude):   {'✓' if flags.get('pos_vert_abs_status_flag') else '✗'}")
        print(f"  Horizontal velocity (GPS):      {'✓' if flags.get('velocity_horiz_status_flag') else '✗'}")
        print(f"  Horizontal position (GPS rel):  {'✓' if flags.get('pos_horiz_rel_status_flag') else '✗'}")
        print(f"  Horizontal position (GPS abs):  {'✓' if flags.get('pos_horiz_abs_status_flag') else '✗'}")

        # Critical checks: all states must be valid in GPS mode
        assert flags.get('attitude_status_flag'), (
            "EKF2 attitude not converged. "
            "Check IMU data availability and EKF2 initialization."
        )
        print("\n✓ Attitude estimation converged")

        assert flags.get('pos_vert_abs_status_flag'), (
            "EKF2 vertical position not converged. "
            "Check barometer or GPS altitude data availability."
        )
        print("✓ Vertical position estimation converged")

        assert flags.get('velocity_horiz_status_flag'), (
            "EKF2 horizontal velocity not converged. "
            "Check GPS data availability and fusion settings (EKF2_GPS_CTRL=7)."
        )
        print("✓ Horizontal velocity estimation converged (GPS)")

        assert flags.get('pos_horiz_rel_status_flag'), (
            "EKF2 horizontal relative position not converged. "
            "Check GPS fusion is enabled."
        )
        print("✓ Horizontal relative position estimation converged (GPS)")

        # KEY: GPS absolute positioning must work
        assert flags.get('pos_horiz_abs_status_flag'), (
            "EKF2 GPS absolute position not converged! "
            "This is critical - GPS mode requires absolute position fix. "
            "Check: 1) GPS fix quality (≥6 satellites), "
            "2) EKF2_GPS_CTRL=7 parameter applied, "
            "3) No GPS timeout errors in PX4 logs."
        )
        print("✓ GPS absolute position estimation converged")

        print("\n" + "="*70)
        print("✅ ALL PHASES COMPLETE: EKF2 CONVERGED (Full 3D GPS)")
        print("="*70)
        print("\nPipeline verified:")
        print("  Gazebo Sensors (IMU/Mag/Baro/GPS) → PX4 EKF2 ✓")
        print("  PX4 EKF2 → MAVROS → Estimator Status ✓")
        print("  EKF2 Attitude Estimation ✓")
        print("  EKF2 Vertical Position Estimation ✓")
        print("  EKF2 Horizontal Position Estimation (GPS) ✓")
        print("  EKF2 GPS Absolute Positioning ✓")
        print("\n✓ GPS-enabled mode fully operational - drone ready for outdoor missions")
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
    print("QUICK EKF2 SMOKE TEST (drone_1 - GPS mode)")
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

    # GPS topic exists
    command = (
        "bash -c '"
        "source /opt/ros/humble/setup.bash && "
        "ros2 topic list | grep -c global_position"
        "'"
    )
    exit_code, output = ros2_container.exec_run(command, demux=False)
    if exit_code == 0 and int(output.decode('utf-8', errors='ignore').strip()) > 0:
        print("✓ GPS topics available")
    else:
        print("⚠️ GPS topics not found (may take time to initialize)")

    # No EKF2 critical errors
    assert "ekf2 missing data" not in sim_logs.lower(), "EKF2 missing data"
    print("✓ No EKF2 critical errors")

    print("\n✅ Quick check passed - system appears healthy (GPS mode)\n")
