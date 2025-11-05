#!/usr/bin/env python3
"""
Vision Pose Bridge for PX4 GPS-Free Operation
Bridges Gazebo ground truth pose → MAVROS vision_pose for EKF2 fusion
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import PoseStamped
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped
import math


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

        # QoS profile for Gazebo topics (typically RELIABLE)
        gazebo_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # QoS profile for MAVROS vision_pose (BEST_EFFORT to match MAVROS)
        vision_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # Subscribe to Gazebo model pose
        # Topic format: /model/{model_name}/pose or /gz/model/{model_name}/pose
        # We'll try both common formats
        self.gazebo_pose_topic = f'/model/{self.model_name}/pose'

        self.gazebo_sub = self.create_subscription(
            PoseStamped,
            self.gazebo_pose_topic,
            self.gazebo_pose_callback,
            gazebo_qos
        )

        # Publish to MAVROS vision_pose topic
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

        self.get_logger().info(f'Vision Pose Bridge initialized')
        self.get_logger().info(f'  Gazebo topic: {self.gazebo_pose_topic}')
        self.get_logger().info(f'  MAVROS topic: /mavros/vision_pose/pose')

    def gazebo_pose_callback(self, msg: PoseStamped):
        """
        Callback for Gazebo ground truth pose
        Transforms from Gazebo frame to MAVROS vision frame (ENU)
        """
        # Gazebo Harmonic uses ENU frame by default (same as MAVROS)
        # So we can pass through the pose directly
        vision_msg = PoseStamped()

        # Use current ROS time for stamping
        vision_msg.header.stamp = self.get_clock().now().to_msg()
        vision_msg.header.frame_id = 'map'  # MAVROS vision pose frame

        # Copy position (ENU frame)
        vision_msg.pose.position.x = msg.pose.position.x
        vision_msg.pose.position.y = msg.pose.position.y
        vision_msg.pose.position.z = msg.pose.position.z

        # Copy orientation (quaternion)
        vision_msg.pose.orientation.x = msg.pose.orientation.x
        vision_msg.pose.orientation.y = msg.pose.orientation.y
        vision_msg.pose.orientation.z = msg.pose.orientation.z
        vision_msg.pose.orientation.w = msg.pose.orientation.w

        # Publish to MAVROS
        self.vision_pub.publish(vision_msg)

        # Log at 1 Hz for debugging
        self.message_count += 1
        now = self.get_clock().now()
        if (now - self.last_publish_time).nanoseconds > 1e9:  # 1 second
            self.get_logger().info(
                f'Vision pose published: pos=[{vision_msg.pose.position.x:.2f}, '
                f'{vision_msg.pose.position.y:.2f}, {vision_msg.pose.position.z:.2f}] '
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
