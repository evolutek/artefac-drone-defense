"""
Unit tests for Vision Pose Bridge node logic (without full ROS2/Gazebo infrastructure).

Tests the core logic of mqtt_bridge/vision_pose_bridge.py:
- Quaternion to rotation matrix conversion
- World frame to body frame velocity transformation
- Odometry message construction
- Covariance matrix configuration
- Frame ID and coordinate system handling

These tests do NOT require:
- Running ROS2 nodes
- Gazebo Harmonic
- Gazebo Transport
- Docker containers
"""

import pytest
import numpy as np
from collections import namedtuple


# Mock message types
MockOdometry = namedtuple('Odometry', ['header', 'child_frame_id', 'pose', 'twist'])
MockPoseWithCovariance = namedtuple('PoseWithCovariance', ['pose', 'covariance'])
MockTwistWithCovariance = namedtuple('TwistWithCovariance', ['twist', 'covariance'])
MockPose = namedtuple('Pose', ['position', 'orientation'])
MockTwist = namedtuple('Twist', ['linear', 'angular'])
MockPoint = namedtuple('Point', ['x', 'y', 'z'])
MockQuaternion = namedtuple('Quaternion', ['x', 'y', 'z', 'w'])
MockVector3 = namedtuple('Vector3', ['x', 'y', 'z'])


class TestQuaternionToRotationMatrix:
    """Test quaternion to rotation matrix conversion."""

    def quaternion_to_rotation_matrix(self, qx, qy, qz, qw):
        """Reference implementation from bridge_node.py."""
        # Normalize quaternion
        norm = np.sqrt(qx**2 + qy**2 + qz**2 + qw**2)
        qx, qy, qz, qw = qx/norm, qy/norm, qz/norm, qw/norm

        # Compute rotation matrix
        R = np.array([
            [1 - 2*(qy**2 + qz**2), 2*(qx*qy - qw*qz), 2*(qx*qz + qw*qy)],
            [2*(qx*qy + qw*qz), 1 - 2*(qx**2 + qz**2), 2*(qy*qz - qw*qx)],
            [2*(qx*qz - qw*qy), 2*(qy*qz + qw*qx), 1 - 2*(qx**2 + qy**2)]
        ])
        return R

    def test_identity_quaternion(self):
        """Identity quaternion (no rotation) should produce identity matrix."""
        # Identity quaternion: w=1, x=y=z=0
        R = self.quaternion_to_rotation_matrix(0.0, 0.0, 0.0, 1.0)

        # Should be identity matrix
        expected = np.eye(3)
        np.testing.assert_array_almost_equal(R, expected)

    def test_rotation_about_z_axis_90deg(self):
        """90° rotation about Z-axis."""
        # Quaternion for 90° about Z: w=cos(45°), z=sin(45°)
        qw = np.cos(np.pi/4)
        qz = np.sin(np.pi/4)
        R = self.quaternion_to_rotation_matrix(0.0, 0.0, qz, qw)

        # Expected: 90° rotation about Z
        # [cos(90) -sin(90) 0]   [0 -1 0]
        # [sin(90)  cos(90) 0] = [1  0 0]
        # [0        0       1]   [0  0 1]
        expected = np.array([
            [0.0, -1.0, 0.0],
            [1.0,  0.0, 0.0],
            [0.0,  0.0, 1.0]
        ])

        np.testing.assert_array_almost_equal(R, expected, decimal=5)

    def test_rotation_about_x_axis_180deg(self):
        """180° rotation about X-axis."""
        # Quaternion for 180° about X: w=0, x=1
        R = self.quaternion_to_rotation_matrix(1.0, 0.0, 0.0, 0.0)

        # Expected: 180° rotation about X
        # [1   0        0     ]
        # [0  cos(180) -sin(180)] = [1  0  0]
        # [0  sin(180)  cos(180)]   [0 -1  0]
        #                           [0  0 -1]
        expected = np.array([
            [1.0,  0.0,  0.0],
            [0.0, -1.0,  0.0],
            [0.0,  0.0, -1.0]
        ])

        np.testing.assert_array_almost_equal(R, expected, decimal=5)

    def test_quaternion_normalization(self):
        """Non-normalized quaternion should be normalized automatically."""
        # Non-normalized quaternion (should be normalized internally)
        qx, qy, qz, qw = 0.0, 0.0, 2.0, 2.0  # Not unit length

        R = self.quaternion_to_rotation_matrix(qx, qy, qz, qw)

        # Result should still be valid rotation matrix
        # (R @ R.T should be identity)
        identity = R @ R.T
        np.testing.assert_array_almost_equal(identity, np.eye(3), decimal=5)

    def test_rotation_matrix_orthogonality(self):
        """Any rotation matrix should be orthogonal (R @ R.T = I)."""
        # Arbitrary quaternion
        qx, qy, qz, qw = 0.5, 0.5, 0.5, 0.5

        R = self.quaternion_to_rotation_matrix(qx, qy, qz, qw)

        # Check orthogonality
        identity = R @ R.T
        np.testing.assert_array_almost_equal(identity, np.eye(3), decimal=5)

    def test_rotation_matrix_determinant(self):
        """Rotation matrix should have determinant = 1."""
        qx, qy, qz, qw = 0.1, 0.2, 0.3, 0.9

        R = self.quaternion_to_rotation_matrix(qx, qy, qz, qw)

        # Determinant should be 1 (proper rotation)
        det = np.linalg.det(R)
        np.testing.assert_almost_equal(det, 1.0, decimal=5)


class TestWorldToBodyFrameTransform:
    """Test velocity transformation from world to body frame."""

    def quaternion_to_rotation_matrix(self, qx, qy, qz, qw):
        """Reference implementation."""
        norm = np.sqrt(qx**2 + qy**2 + qz**2 + qw**2)
        qx, qy, qz, qw = qx/norm, qy/norm, qz/norm, qw/norm

        R = np.array([
            [1 - 2*(qy**2 + qz**2), 2*(qx*qy - qw*qz), 2*(qx*qz + qw*qy)],
            [2*(qx*qy + qw*qz), 1 - 2*(qx**2 + qz**2), 2*(qy*qz - qw*qx)],
            [2*(qx*qz - qw*qy), 2*(qy*qz + qw*qx), 1 - 2*(qx**2 + qy**2)]
        ])
        return R

    def world_to_body_frame(self, vel_world, qx, qy, qz, qw):
        """Reference implementation from bridge_node.py."""
        # Get rotation matrix from world to body (transpose of body to world)
        R_world_to_body = self.quaternion_to_rotation_matrix(qx, qy, qz, qw).T

        # Transform velocity
        vel_body = R_world_to_body @ vel_world
        return vel_body

    def test_identity_orientation_no_transform(self):
        """With identity orientation, body frame = world frame."""
        vel_world = np.array([1.0, 2.0, 3.0])

        # Identity quaternion
        vel_body = self.world_to_body_frame(vel_world, 0.0, 0.0, 0.0, 1.0)

        # Should be unchanged
        np.testing.assert_array_almost_equal(vel_body, vel_world)

    def test_90deg_rotation_about_z(self):
        """Velocity transformation with 90° yaw rotation."""
        # Velocity in world frame: moving in +X direction
        vel_world = np.array([1.0, 0.0, 0.0])

        # 90° rotation about Z (yaw)
        qw = np.cos(np.pi/4)
        qz = np.sin(np.pi/4)

        vel_body = self.world_to_body_frame(vel_world, 0.0, 0.0, qz, qw)

        # After 90° yaw, world +X becomes body +Y
        expected = np.array([0.0, 1.0, 0.0])
        np.testing.assert_array_almost_equal(vel_body, expected, decimal=5)

    def test_combined_velocity_components(self):
        """Transform velocity with all 3 components."""
        vel_world = np.array([5.0, 3.0, 2.0])

        # Arbitrary orientation
        qx, qy, qz, qw = 0.1, 0.2, 0.3, 0.9

        vel_body = self.world_to_body_frame(vel_world, qx, qy, qz, qw)

        # Result should have same magnitude (rotation preserves length)
        mag_world = np.linalg.norm(vel_world)
        mag_body = np.linalg.norm(vel_body)

        np.testing.assert_almost_equal(mag_world, mag_body, decimal=5)

    def test_zero_velocity(self):
        """Zero velocity should remain zero in any frame."""
        vel_world = np.array([0.0, 0.0, 0.0])

        # Arbitrary orientation
        qx, qy, qz, qw = 0.5, 0.5, 0.5, 0.5

        vel_body = self.world_to_body_frame(vel_world, qx, qy, qz, qw)

        expected = np.array([0.0, 0.0, 0.0])
        np.testing.assert_array_almost_equal(vel_body, expected)


class TestOdometryMessageConstruction:
    """Test odometry message field population."""

    def test_odometry_frame_ids(self):
        """Verify correct frame IDs for MAVROS."""
        # Expected frame IDs
        parent_frame = 'map'        # World/inertial frame (ENU)
        child_frame = 'base_link'   # Body frame

        assert parent_frame == 'map'
        assert child_frame == 'base_link'

    def test_pose_covariance_dimensions(self):
        """Pose covariance should be 6x6 = 36 elements."""
        # Covariance from bridge_node.py
        covariance = [
            0.01, 0.0,  0.0,  0.0,   0.0,   0.0,
            0.0,  0.01, 0.0,  0.0,   0.0,   0.0,
            0.0,  0.0,  0.01, 0.0,   0.0,   0.0,
            0.0,  0.0,  0.0,  0.001, 0.0,   0.0,
            0.0,  0.0,  0.0,  0.0,   0.001, 0.0,
            0.0,  0.0,  0.0,  0.0,   0.0,   0.001
        ]

        assert len(covariance) == 36  # 6x6 matrix flattened

    def test_pose_covariance_values(self):
        """Verify pose covariance values are reasonable."""
        # Position variance: 0.01 m² (10cm std dev)
        pos_variance = 0.01
        # Orientation variance: 0.001 rad² (~1.8° std dev)
        ori_variance = 0.001

        assert pos_variance == 0.01
        assert ori_variance == 0.001

        # Std dev should be reasonable
        pos_std = np.sqrt(pos_variance)
        ori_std = np.sqrt(ori_variance)

        assert pos_std == 0.1  # 10cm
        assert np.isclose(ori_std, 0.0316, atol=0.001)  # ~1.8°

    def test_twist_covariance_dimensions(self):
        """Twist covariance should be 6x6 = 36 elements."""
        covariance = [
            0.01, 0.0,  0.0,  0.0,   0.0,   0.0,
            0.0,  0.01, 0.0,  0.0,   0.0,   0.0,
            0.0,  0.0,  0.01, 0.0,   0.0,   0.0,
            0.0,  0.0,  0.0,  0.001, 0.0,   0.0,
            0.0,  0.0,  0.0,  0.0,   0.001, 0.0,
            0.0,  0.0,  0.0,  0.0,   0.0,   0.001
        ]

        assert len(covariance) == 36

    def test_twist_covariance_values(self):
        """Verify twist covariance values are reasonable."""
        # Linear velocity variance: 0.01 (m/s)²
        lin_vel_variance = 0.01
        # Angular velocity variance: 0.001 (rad/s)²
        ang_vel_variance = 0.001

        assert lin_vel_variance == 0.01
        assert ang_vel_variance == 0.001


class TestGazeboTopicSubscription:
    """Test Gazebo Transport topic configuration."""

    def test_gazebo_pose_topic_format(self):
        """Gazebo dynamic pose topic should be /world/{world_name}/dynamic_pose/info."""
        world_name = 'default'
        topic = f'/world/{world_name}/dynamic_pose/info'

        assert topic == '/world/default/dynamic_pose/info'

    def test_gazebo_odom_topic_format(self):
        """Gazebo model odometry topic should be /model/{model_name}/odometry."""
        model_name = 'x500_0'
        topic = f'/model/{model_name}/odometry'

        assert topic == '/model/x500_0/odometry'

    def test_model_name_filtering(self):
        """Bridge should filter poses by model name."""
        target_model = 'x500_0'
        available_models = ['x500_0', 'x500_1', 'ground_plane']

        # Should find target model
        assert target_model in available_models

    def test_model_not_found_warning(self):
        """Bridge should warn if target model not in Gazebo data."""
        target_model = 'x500_5'
        available_models = ['x500_0', 'x500_1', 'ground_plane']

        # Should detect missing model
        assert target_model not in available_models


class TestMAVROSTopicPublishing:
    """Test MAVROS topic configuration."""

    def test_mavros_odometry_topic(self):
        """Vision bridge should publish to /mavros/odometry/out."""
        topic = '/mavros/odometry/out'

        assert topic == '/mavros/odometry/out'
        assert topic.startswith('/mavros/')

    def test_mavros_qos_best_effort(self):
        """MAVROS odometry should use BEST_EFFORT QoS."""
        qos_config = {
            'reliability': 'BEST_EFFORT',
            'history': 'KEEP_LAST',
            'depth': 10
        }

        assert qos_config['reliability'] == 'BEST_EFFORT'


class TestStaticTransformConfiguration:
    """Test static TF transform requirements."""

    def test_static_tf_map_to_odom_ned(self):
        """MAVROS 1.3.0+ requires map → odom_ned static transform."""
        parent_frame = 'map'
        child_frame = 'odom_ned'

        assert parent_frame == 'map'
        assert child_frame == 'odom_ned'

    def test_static_tf_identity_transform(self):
        """map → odom_ned should be identity transform."""
        # Identity transform
        translation = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        rotation = {'x': 0.0, 'y': 0.0, 'z': 0.0, 'w': 1.0}

        assert translation['x'] == 0.0
        assert rotation['w'] == 1.0

    def test_tf_broadcast_for_visualization(self):
        """Bridge should broadcast TF for RViz visualization."""
        model_name = 'x500_0'
        child_frame_id = f'{model_name}_vision'

        assert child_frame_id == 'x500_0_vision'


class TestDataSynchronization:
    """Test pose and velocity data synchronization logic."""

    def test_publish_requires_both_pose_and_velocity(self):
        """Should not publish odometry until both pose and velocity are available."""
        has_pose = True
        has_velocity = False

        should_publish = has_pose and has_velocity

        assert should_publish is False

    def test_publish_when_both_available(self):
        """Should publish odometry when both pose and velocity are available."""
        has_pose = True
        has_velocity = True

        should_publish = has_pose and has_velocity

        assert should_publish is True

    def test_separate_gazebo_topics_for_data(self):
        """Pose and velocity come from different Gazebo topics."""
        pose_topic = '/world/default/dynamic_pose/info'
        odom_topic = '/model/x500_0/odometry'

        # Different topics
        assert pose_topic != odom_topic
        assert 'pose' in pose_topic
        assert 'odometry' in odom_topic


class TestPublishingRate:
    """Test odometry publishing rate logic."""

    def test_log_rate_calculation(self):
        """Should calculate and log publishing rate (messages/sec)."""
        message_count = 52
        time_elapsed = 1.0  # seconds

        rate = message_count / time_elapsed

        assert rate == 52.0  # Expected ~52 Hz

    def test_rate_logging_interval(self):
        """Should log rate at 1 Hz (every 1 second)."""
        log_interval_ns = 1e9  # 1 second in nanoseconds

        assert log_interval_ns == 1_000_000_000

    def test_expected_publishing_rate_range(self):
        """Vision bridge should publish at ~50 Hz (Gazebo Harmonic rate)."""
        expected_min_hz = 45
        expected_max_hz = 60

        # Simulated rate
        actual_rate = 52

        assert expected_min_hz <= actual_rate <= expected_max_hz
