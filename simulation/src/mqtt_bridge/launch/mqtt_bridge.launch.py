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
            'mavros_namespace',
            default_value='/mavros',
            description='MAVROS namespace'
        ),
        DeclareLaunchArgument(
            'model_name',
            default_value='x500_0',
            description='Gazebo model name'
        ),

        # Vision Pose Bridge Node (Gazebo → MAVROS)
        Node(
            package='mqtt_bridge',
            executable='vision_pose_bridge',
            name='vision_pose_bridge',
            output='screen',
            parameters=[{
                'drone_id': LaunchConfiguration('drone_id'),
                'model_name': LaunchConfiguration('model_name'),
            }],
        ),

        # MQTT Bridge Node
        Node(
            package='mqtt_bridge',
            executable='bridge_node',
            name='mqtt_bridge',
            output='screen',
            parameters=[{
                'drone_id': LaunchConfiguration('drone_id'),
                'mqtt_broker': LaunchConfiguration('mqtt_broker'),
                'mqtt_port': LaunchConfiguration('mqtt_port'),
                'mavros_namespace': LaunchConfiguration('mavros_namespace'),
            }],
        ),
    ])
