#!/usr/bin/env python3
"""
Vision Odometry Bridge for PX4 GPS-Free Operation
Bridges Gazebo ground truth pose + odometry → MAVROS odometry for EKF2 fusion

Uses Gazebo Transport directly to subscribe to pose and odometry data from Gazebo Harmonic,
then publishes to MAVROS odometry topic for EKF2 fusion.

Architecture:
  Gazebo (/world/default/dynamic_pose/info + /model/x500_0/odometry)
    → gz.transport subscriber
    → Filter by model_name
    → Convert to ROS2 Odometry with velocities in body frame
    → Publish to /mavros/odometry/out
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster
from geometry_msgs.msg import TransformStamped
import numpy as np
import threading
import time

# Gazebo Transport imports
try:
    from gz.transport13 import Node as GzNode
    from gz.msgs10.pose_v_pb2 import Pose_V
    from gz.msgs10.odometry_pb2 import Odometry as GzOdometry
except ImportError as e:
    print(f"ERROR: Failed to import Gazebo Transport: {e}")
    print("Make sure python3-gz-transport13 is installed in the container")
    raise


class VisionPoseBridge(Node):
    def __init__(self):
        super().__init__('vision_pose_bridge')

        # Parameters
        self.declare_parameter('drone_id', 'drone_1')
        self.declare_parameter('model_name', 'x500_0')
        self.declare_parameter('namespace', 'drone_1')

        self.drone_id = self.get_parameter('drone_id').value
        self.model_name = self.get_parameter('model_name').value
        self.namespace = self.get_parameter('namespace').value

        self.get_logger().info(f'Initializing Vision Odometry Bridge for {self.drone_id}')
        self.get_logger().info(f'Subscribing to Gazebo model: {self.model_name}')
        self.get_logger().info(f'Publishing to namespace: {self.namespace}')

        # QoS profile for MAVROS odometry (BEST_EFFORT to match MAVROS)
        vision_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # ROS2 Publisher to MAVROS odometry topic
        # MAVROS expects odometry data in ENU (East-North-Up) frame
        # Topic is namespaceed for multi-drone support: /{namespace}/mavros/odometry/out
        self.mavros_odom_topic = f'/{self.namespace}/mavros/odometry/out'
        self.odom_pub = self.create_publisher(
            Odometry,
            self.mavros_odom_topic,
            vision_qos
        )

        # TF broadcasters
        self.tf_broadcaster = TransformBroadcaster(self)
        self.static_tf_broadcaster = StaticTransformBroadcaster(self)

        # Publish required static TF: map → odom_ned
        # This is required by MAVROS 1.3.0+
        self.publish_static_transforms()

        # State
        self.last_publish_time = self.get_clock().now()
        self.message_count = 0
        self.pose_received = False
        self.odom_received = False

        # Storage for latest data
        self.latest_pose = None
        self.latest_velocity = None
        self.latest_angular_velocity = None
        self.latest_orientation = None
        self.lock = threading.Lock()

        # Gazebo Transport Node
        self.gz_node = GzNode()

        # Subscribe to Gazebo dynamic pose topic
        self.gz_pose_topic = '/world/default/dynamic_pose/info'
        self.get_logger().info(f'Subscribing to Gazebo pose topic: {self.gz_pose_topic}')

        if not self.gz_node.subscribe(Pose_V, self.gz_pose_topic, self.gazebo_pose_callback):
            self.get_logger().error(f'Failed to subscribe to Gazebo topic: {self.gz_pose_topic}')
            raise RuntimeError(f'Could not subscribe to {self.gz_pose_topic}')

        # Subscribe to Gazebo model odometry topic for velocities
        self.gz_odom_topic = f'/model/{self.model_name}/odometry'
        self.get_logger().info(f'Subscribing to Gazebo odom topic: {self.gz_odom_topic}')

        if not self.gz_node.subscribe(GzOdometry, self.gz_odom_topic, self.gazebo_odom_callback):
            self.get_logger().error(f'Failed to subscribe to Gazebo topic: {self.gz_odom_topic}')
            raise RuntimeError(f'Could not subscribe to {self.gz_odom_topic}')

        self.get_logger().info(f'Vision Odometry Bridge initialized successfully')
        self.get_logger().info(f'  Gazebo pose topic: {self.gz_pose_topic}')
        self.get_logger().info(f'  Gazebo odom topic: {self.gz_odom_topic}')
        self.get_logger().info(f'  Filtering for model: {self.model_name}')
        self.get_logger().info(f'  Publishing to: {self.mavros_odom_topic}')

    def publish_static_transforms(self):
        """
        Publish required static TF transforms for MAVROS
        MAVROS 1.3.0+ requires map → odom_ned transform
        """
        # map → odom_ned (identity transform)
        static_tf = TransformStamped()
        static_tf.header.stamp = self.get_clock().now().to_msg()
        static_tf.header.frame_id = 'map'
        static_tf.child_frame_id = 'odom_ned'

        # Identity transform (no rotation/translation)
        static_tf.transform.translation.x = 0.0
        static_tf.transform.translation.y = 0.0
        static_tf.transform.translation.z = 0.0
        static_tf.transform.rotation.w = 1.0
        static_tf.transform.rotation.x = 0.0
        static_tf.transform.rotation.y = 0.0
        static_tf.transform.rotation.z = 0.0

        self.static_tf_broadcaster.sendTransform(static_tf)
        self.get_logger().info('Published static TF: map → odom_ned')

    def quaternion_to_rotation_matrix(self, qx, qy, qz, qw):
        """Convert quaternion to 3x3 rotation matrix"""
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

    def world_to_body_frame(self, vel_world, qx, qy, qz, qw):
        """
        Transform velocity from world frame (ENU) to body frame (FRD)

        Args:
            vel_world: Velocity vector in world frame [vx, vy, vz]
            qx, qy, qz, qw: Quaternion representing body orientation

        Returns:
            Velocity vector in body frame [vx_body, vy_body, vz_body]
        """
        # Get rotation matrix from world to body (inverse/transpose of body to world)
        R_world_to_body = self.quaternion_to_rotation_matrix(qx, qy, qz, qw).T

        # Transform velocity
        vel_body = R_world_to_body @ vel_world
        return vel_body

    def gazebo_pose_callback(self, msg: Pose_V):
        """
        Callback for Gazebo Pose_V message
        Stores position and orientation for publishing

        Args:
            msg: Pose_V message containing all model poses in the world
        """
        # Find our drone in the pose vector
        drone_pose = None
        for pose in msg.pose:
            if pose.name == self.model_name:
                drone_pose = pose
                break

        if drone_pose is None:
            if not self.pose_received:
                self.get_logger().warn(
                    f'Model {self.model_name} not found in Gazebo pose data. '
                    f'Available models: {[p.name for p in msg.pose]}'
                )
            return

        self.pose_received = True

        # Store pose data
        with self.lock:
            self.latest_pose = (
                drone_pose.position.x,
                drone_pose.position.y,
                drone_pose.position.z
            )
            self.latest_orientation = (
                drone_pose.orientation.x,
                drone_pose.orientation.y,
                drone_pose.orientation.z,
                drone_pose.orientation.w
            )

        # Publish odometry if we have both pose and velocity
        if self.latest_velocity is not None:
            self.publish_odometry()

    def gazebo_odom_callback(self, msg: GzOdometry):
        """
        Callback for Gazebo Odometry message
        Stores velocities for publishing

        Args:
            msg: GzOdometry message containing velocity data
        """
        self.odom_received = True

        # Store velocity data (in world frame from Gazebo)
        with self.lock:
            self.latest_velocity = np.array([
                msg.twist.linear.x,
                msg.twist.linear.y,
                msg.twist.linear.z
            ])
            self.latest_angular_velocity = np.array([
                msg.twist.angular.x,
                msg.twist.angular.y,
                msg.twist.angular.z
            ])

        # Publish odometry if we have both pose and velocity
        if self.latest_pose is not None:
            self.publish_odometry()

    def publish_odometry(self):
        """
        Publish combined odometry message to MAVROS
        Combines latest pose and velocity data
        """
        with self.lock:
            if self.latest_pose is None or self.latest_velocity is None:
                return

            # Get current data
            pos = self.latest_pose
            ori = self.latest_orientation
            vel_world = self.latest_velocity
            ang_vel_world = self.latest_angular_velocity

        # Transform velocities to body frame
        # PX4 requires twist in body frame for odometry messages
        vel_body = self.world_to_body_frame(vel_world, ori[0], ori[1], ori[2], ori[3])
        ang_vel_body = self.world_to_body_frame(ang_vel_world, ori[0], ori[1], ori[2], ori[3])

        # Create Odometry message
        odom_msg = Odometry()

        # Header
        odom_msg.header.stamp = self.get_clock().now().to_msg()
        odom_msg.header.frame_id = 'map'  # Inertial frame (ENU)
        odom_msg.child_frame_id = 'base_link'  # Body frame

        # Pose
        odom_msg.pose.pose.position.x = pos[0]
        odom_msg.pose.pose.position.y = pos[1]
        odom_msg.pose.pose.position.z = pos[2]

        odom_msg.pose.pose.orientation.x = ori[0]
        odom_msg.pose.pose.orientation.y = ori[1]
        odom_msg.pose.pose.orientation.z = ori[2]
        odom_msg.pose.pose.orientation.w = ori[3]

        # Pose covariance (6x6 = 36 elements)
        # Position variance: 0.01 m² (10cm std dev)
        # Orientation variance: 0.001 rad² (~1.8 deg std dev)
        odom_msg.pose.covariance = [
            0.01, 0.0,  0.0,  0.0,   0.0,   0.0,    # x
            0.0,  0.01, 0.0,  0.0,   0.0,   0.0,    # y
            0.0,  0.0,  0.01, 0.0,   0.0,   0.0,    # z
            0.0,  0.0,  0.0,  0.001, 0.0,   0.0,    # roll
            0.0,  0.0,  0.0,  0.0,   0.001, 0.0,    # pitch
            0.0,  0.0,  0.0,  0.0,   0.0,   0.001   # yaw
        ]

        # Twist (velocities in body frame)
        odom_msg.twist.twist.linear.x = vel_body[0]
        odom_msg.twist.twist.linear.y = vel_body[1]
        odom_msg.twist.twist.linear.z = vel_body[2]

        odom_msg.twist.twist.angular.x = ang_vel_body[0]
        odom_msg.twist.twist.angular.y = ang_vel_body[1]
        odom_msg.twist.twist.angular.z = ang_vel_body[2]

        # Twist covariance (6x6 = 36 elements)
        # Linear velocity variance: 0.01 (m/s)²
        # Angular velocity variance: 0.001 (rad/s)²
        odom_msg.twist.covariance = [
            0.01, 0.0,  0.0,  0.0,   0.0,   0.0,    # vx
            0.0,  0.01, 0.0,  0.0,   0.0,   0.0,    # vy
            0.0,  0.0,  0.01, 0.0,   0.0,   0.0,    # vz
            0.0,  0.0,  0.0,  0.001, 0.0,   0.0,    # wx
            0.0,  0.0,  0.0,  0.0,   0.001, 0.0,    # wy
            0.0,  0.0,  0.0,  0.0,   0.0,   0.001   # wz
        ]

        # Publish to MAVROS
        self.odom_pub.publish(odom_msg)

        # Log at 1 Hz for debugging
        self.message_count += 1
        now = self.get_clock().now()
        if (now - self.last_publish_time).nanoseconds > 1e9:  # 1 second
            self.get_logger().info(
                f'Odometry published: pos=[{pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f}] '
                f'vel_body=[{vel_body[0]:.2f}, {vel_body[1]:.2f}, {vel_body[2]:.2f}] m/s '
                f'({self.message_count} msgs/sec)'
            )
            self.last_publish_time = now
            self.message_count = 0

        # Broadcast TF for visualization
        self.broadcast_tf(odom_msg)

    def broadcast_tf(self, odom_msg: Odometry):
        """Broadcast TF transform for RViz visualization"""
        t = TransformStamped()

        t.header.stamp = odom_msg.header.stamp
        t.header.frame_id = 'map'
        t.child_frame_id = f'{self.model_name}_vision'

        t.transform.translation.x = odom_msg.pose.pose.position.x
        t.transform.translation.y = odom_msg.pose.pose.position.y
        t.transform.translation.z = odom_msg.pose.pose.position.z

        t.transform.rotation.x = odom_msg.pose.pose.orientation.x
        t.transform.rotation.y = odom_msg.pose.pose.orientation.y
        t.transform.rotation.z = odom_msg.pose.pose.orientation.z
        t.transform.rotation.w = odom_msg.pose.pose.orientation.w

        self.tf_broadcaster.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = VisionPoseBridge()

    # CRITICAL FIX: Run rclpy.spin() in a separate thread
    # gz.transport13 (C++) needs the main thread available for its internal callback threads
    # If rclpy.spin() blocks the main thread, gz.transport callbacks never execute
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    node.get_logger().info('ROS2 node spinning in separate thread, main thread available for gz.transport')

    try:
        # Keep main thread alive for gz.transport internal threads
        # This allows gz.transport callbacks to execute properly
        while rclpy.ok():
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()
        node.destroy_node()


if __name__ == '__main__':
    main()
