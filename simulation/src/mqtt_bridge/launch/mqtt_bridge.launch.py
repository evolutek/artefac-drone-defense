#!/usr/bin/env python3
"""
Launch file for MQTT Bridge Node
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        # Declare launch arguments
        DeclareLaunchArgument(
            'drone_id',
            default_value='drone_1',
            description='Drone ID for this bridge instance'
        ),
        DeclareLaunchArgument(
            'mqtt_broker',
            default_value='mqtt',
            description='MQTT broker hostname'
        ),
        DeclareLaunchArgument(
            'mqtt_port',
            default_value='1883',
            description='MQTT broker port'
        ),
        DeclareLaunchArgument(
            'namespace',
            default_value='drone_1',
            description='ROS2 namespace for MAVROS topics (e.g., drone_1, drone_2)'
        ),
        DeclareLaunchArgument(
            'model_name',
            default_value='x500_0',
            description='Gazebo model name (e.g., x500_0, x500_1)'
        ),

        # ROS-Gazebo Bridge (Gazebo Transport → ROS2)
        # TODO: Fix this bridge - currently disabled due to message type incompatibility
        # Gazebo publishes gz.msgs.Pose_V which has no direct ROS2 equivalent
        # For now, vision_pose_bridge uses static test data
        # Node(
        #     package='ros_gz_bridge',
        #     executable='parameter_bridge',
        #     name='gz_pose_bridge',
        #     output='screen',
        #     arguments=[
        #         '/world/default/pose/info@ros_gz_interfaces/msg/EntityWrench[gz.msgs.Pose_V'
        #     ],
        # ),

        # Vision Pose Bridge Node (Gazebo Transport → MAVROS)
        # Subscribes to Gazebo ground truth, publishes to /{namespace}/mavros/odometry/out
        Node(
            package='mqtt_bridge',
            executable='vision_pose_bridge',
            name='vision_pose_bridge',
            output='screen',
            parameters=[{
                'drone_id': LaunchConfiguration('drone_id'),
                'model_name': LaunchConfiguration('model_name'),
                'namespace': LaunchConfiguration('namespace'),
            }],
        ),

        # MQTT Bridge Node (ROS2 MAVROS → MQTT)
        # Subscribes to /{namespace}/mavros/*, publishes to MQTT drone/{drone_id}/*
        Node(
            package='mqtt_bridge',
            executable='bridge_node',
            name='mqtt_bridge',
            output='screen',
            parameters=[{
                'drone_id': LaunchConfiguration('drone_id'),
                'namespace': LaunchConfiguration('namespace'),
                'mqtt_broker': LaunchConfiguration('mqtt_broker'),
                'mqtt_port': LaunchConfiguration('mqtt_port'),
            }],
        ),
    ])
