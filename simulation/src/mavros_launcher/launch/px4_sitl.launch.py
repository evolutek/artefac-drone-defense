"""Launch file to connect MAVROS to PX4 SITL."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """Generate launch description for MAVROS connection to PX4 SITL."""
    # Declare launch arguments
    fcu_url_arg = DeclareLaunchArgument(
        'fcu_url',
        default_value='udp://:14540@127.0.0.1:14580',
        description='FCU connection URL (MAVLink UDP protocol - local:14540@remote:14580)'
    )

    gcs_url_arg = DeclareLaunchArgument(
        'gcs_url',
        default_value='',
        description='GCS connection URL (optional)'
    )

    tgt_system_arg = DeclareLaunchArgument(
        'tgt_system',
        default_value='1',
        description='Target system ID'
    )

    tgt_component_arg = DeclareLaunchArgument(
        'tgt_component',
        default_value='1',
        description='Target component ID'
    )

    namespace_arg = DeclareLaunchArgument(
        'namespace',
        default_value='',
        description='Namespace for MAVROS topics'
    )

    # MAVROS node
    mavros_node = Node(
        package='mavros',
        executable='mavros_node',
        name='mavros_node',
        namespace=LaunchConfiguration('namespace'),
        output='screen',
        parameters=[{
            'fcu_url': LaunchConfiguration('fcu_url'),
            'gcs_url': LaunchConfiguration('gcs_url'),
            'tgt_system': LaunchConfiguration('tgt_system'),
            'tgt_component': LaunchConfiguration('tgt_component'),
            'fcu_protocol': 'v2.0',
            'system_id': 1,
            'component_id': 240,
            # Plugin allowlist - ONLY these plugins will be loaded
            # All other plugins are disabled by default
            'plugin_allowlist': [
                'sys_status',           # Drone state (armed, mode, connected)
                'sys_time',             # Time synchronization with FCU
                'imu',                  # IMU data (accelerometer, gyroscope)
                'local_position',       # Local position (x, y, z in map frame)
                'global_position',      # GPS position (lat, lon, alt)
                'vision_pose',          # Vision/mocap pose input for GPS-free operation
                # All setpoint plugins conflict with local_position on 'local' topic
                # Use velocity control via command plugin or direct MAVLink messages
                'command',              # Send generic commands (arm, takeoff, land, velocity)
                'battery',              # Battery status
                'rc',                   # RC input monitoring
                'param',                # Parameter get/set
                'mission',              # Mission waypoint management
                'home_position'         # Home position for RTL
            ],
            # Connection settings
            'conn': {
                'timeout': 10.0,
                'system_time_rate': 1.0
            },
            # Time sync settings
            'time': {
                'time_ref_source': 'fcu',
                'timesync_rate': 10.0,
                'timesync_avg_alpha': 0.6
            },
            # Local position settings
            'local_position': {
                'frame_id': 'map',
                'tf': {
                    'send': True,
                    'frame_id': 'map',
                    'child_frame_id': 'base_link'
                }
            }
        }]
    )

    return LaunchDescription([
        fcu_url_arg,
        gcs_url_arg,
        tgt_system_arg,
        tgt_component_arg,
        namespace_arg,
        mavros_node
    ])
