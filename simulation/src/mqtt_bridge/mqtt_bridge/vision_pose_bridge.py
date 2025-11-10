#!/usr/bin/env python3
"""
Vision Pose Bridge for PX4 GPS-Free Operation
Bridges Gazebo ground truth pose → MAVROS vision_pose for EKF2 fusion

Uses Gazebo Transport directly to subscribe to pose data from Gazebo Harmonic,
then publishes to MAVROS vision_pose topic for EKF2 fusion.

Architecture:
  Gazebo (/world/default/dynamic_pose/info)
    → gz.transport subscriber
    → Filter by model_name
    → Convert to ROS2 PoseStamped
    → Publish to /mavros/vision_pose/pose
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import PoseStamped
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped
import threading

# Gazebo Transport imports
try:
    from gz.transport13 import Node as GzNode
    from gz.msgs10.pose_v_pb2 import Pose_V
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

        self.drone_id = self.get_parameter('drone_id').value
        self.model_name = self.get_parameter('model_name').value

        self.get_logger().info(f'Initializing Vision Pose Bridge for {self.drone_id}')
        self.get_logger().info(f'Subscribing to Gazebo model: {self.model_name}')

        # QoS profile for MAVROS vision_pose (BEST_EFFORT to match MAVROS)
        vision_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # ROS2 Publisher to MAVROS vision_pose topic
        # MAVROS expects vision data in ENU (East-North-Up) frame
        self.vision_pub = self.create_publisher(
            PoseStamped,
            '/mavros/vision_pose/pose',
            vision_qos
        )

        # TF broadcaster for debugging
        self.tf_broadcaster = TransformBroadcaster(self)

        # State
        self.last_publish_time = self.get_clock().now()
        self.message_count = 0
        self.pose_received = False

        # Gazebo Transport Node
        self.gz_node = GzNode()

        # Subscribe to Gazebo dynamic pose topic
        # This topic publishes all model poses in the world
        self.gz_topic = '/world/default/dynamic_pose/info'

        self.get_logger().info(f'Subscribing to Gazebo topic: {self.gz_topic}')

        # Subscribe with callback
        if not self.gz_node.subscribe(Pose_V, self.gz_topic, self.gazebo_pose_callback):
            self.get_logger().error(f'Failed to subscribe to Gazebo topic: {self.gz_topic}')
            raise RuntimeError(f'Could not subscribe to {self.gz_topic}')

        self.get_logger().info(f'Vision Pose Bridge initialized successfully')
        self.get_logger().info(f'  Gazebo topic: {self.gz_topic}')
        self.get_logger().info(f'  Filtering for model: {self.model_name}')
        self.get_logger().info(f'  Publishing to: /mavros/vision_pose/pose')

    def gazebo_pose_callback(self, msg: Pose_V):
        """
        Callback for Gazebo Pose_V message
        Extracts pose for our specific drone model and publishes to MAVROS

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
            # Model not found in this message, skip
            if not self.pose_received:
                self.get_logger().warn(
                    f'Model {self.model_name} not found in Gazebo pose data. '
                    f'Available models: {[p.name for p in msg.pose]}'
                )
            return

        self.pose_received = True

        # Convert Gazebo pose to ROS2 PoseStamped
        vision_msg = PoseStamped()

        # Use current ROS time for stamping
        vision_msg.header.stamp = self.get_clock().now().to_msg()
        vision_msg.header.frame_id = 'map'  # MAVROS vision pose frame

        # Copy position (Gazebo Harmonic uses ENU frame, same as MAVROS)
        vision_msg.pose.position.x = drone_pose.position.x
        vision_msg.pose.position.y = drone_pose.position.y
        vision_msg.pose.position.z = drone_pose.position.z

        # Copy orientation (quaternion)
        vision_msg.pose.orientation.x = drone_pose.orientation.x
        vision_msg.pose.orientation.y = drone_pose.orientation.y
        vision_msg.pose.orientation.z = drone_pose.orientation.z
        vision_msg.pose.orientation.w = drone_pose.orientation.w

        # Publish to MAVROS
        self.vision_pub.publish(vision_msg)

        # Log at 1 Hz for debugging
        self.message_count += 1
        now = self.get_clock().now()
        if (now - self.last_publish_time).nanoseconds > 1e9:  # 1 second
            self.get_logger().info(
                f'Vision pose published: pos=[{vision_msg.pose.position.x:.3f}, '
                f'{vision_msg.pose.position.y:.3f}, {vision_msg.pose.position.z:.3f}] '
                f'({self.message_count} msgs/sec)'
            )
            self.last_publish_time = now
            self.message_count = 0

        # Broadcast TF for visualization (optional)
        self.broadcast_tf(vision_msg)

    def broadcast_tf(self, pose_msg: PoseStamped):
        """Broadcast TF transform for RViz visualization"""
        t = TransformStamped()

        t.header.stamp = pose_msg.header.stamp
        t.header.frame_id = 'map'
        t.child_frame_id = f'{self.model_name}_vision'

        t.transform.translation.x = pose_msg.pose.position.x
        t.transform.translation.y = pose_msg.pose.position.y
        t.transform.translation.z = pose_msg.pose.position.z

        t.transform.rotation.x = pose_msg.pose.orientation.x
        t.transform.rotation.y = pose_msg.pose.orientation.y
        t.transform.rotation.z = pose_msg.pose.orientation.z
        t.transform.rotation.w = pose_msg.pose.orientation.w

        self.tf_broadcaster.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = VisionPoseBridge()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
