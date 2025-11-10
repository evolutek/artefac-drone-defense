#!/usr/bin/env python3
"""
MQTT Bridge Node for Artefac Drone Defense
Bridges ROS2 MAVROS topics ↔ MQTT for backend communication
"""
import os
import json
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
import paho.mqtt.client as mqtt

# MAVROS messages
from mavros_msgs.msg import State
from mavros_msgs.srv import CommandBool, SetMode, CommandTOL
from sensor_msgs.msg import BatteryState, NavSatFix
from geometry_msgs.msg import PoseStamped, TwistStamped


class MQTTBridgeNode(Node):
    def __init__(self):
        super().__init__('mqtt_bridge')

        # Parameters
        self.declare_parameter('drone_id', 'drone_1')
        self.declare_parameter('mqtt_broker', 'mqtt')
        self.declare_parameter('mqtt_port', 1883)

        self.drone_id = self.get_parameter('drone_id').value
        self.mqtt_broker = self.get_parameter('mqtt_broker').value
        self.mqtt_port = self.get_parameter('mqtt_port').value

        self.get_logger().info(f'Initializing MQTT Bridge for {self.drone_id}')
        self.get_logger().info(f'MQTT Broker: {self.mqtt_broker}:{self.mqtt_port}')

        # QoS profiles for subscriptions
        # State topic requires RELIABLE + TRANSIENT_LOCAL to match MAVROS publisher
        state_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # Other topics use BEST_EFFORT
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # ROS2 Subscribers (MAVROS topics)
        # Note: MAVROS publishes on /mavros/state
        self.state_sub = self.create_subscription(
            State,
            '/mavros/state',
            self.state_callback,
            state_qos
        )

        # Note: MAVROS publishes with 'mavros' namespace for these topics
        self.local_position_sub = self.create_subscription(
            PoseStamped,
            '/mavros/local_position/pose',
            self.local_position_callback,
            qos_profile
        )

        self.global_position_sub = self.create_subscription(
            NavSatFix,
            '/mavros/global_position/global',
            self.global_position_callback,
            qos_profile
        )

        self.battery_sub = self.create_subscription(
            BatteryState,
            '/mavros/battery',
            self.battery_callback,
            qos_profile
        )

        self.velocity_sub = self.create_subscription(
            TwistStamped,
            '/mavros/local_position/velocity_local',
            self.velocity_callback,
            qos_profile
        )

        # ROS2 Service Clients (MAVROS services)
        # Note: MAVROS is launched without namespace, services are directly under /mavros_node
        self.arming_client = self.create_client(
            CommandBool,
            '/mavros_node/arming'
        )

        self.set_mode_client = self.create_client(
            SetMode,
            '/mavros_node/set_mode'
        )

        self.takeoff_client = self.create_client(
            CommandTOL,
            '/mavros_node/cmd/takeoff'
        )

        self.land_client = self.create_client(
            CommandTOL,
            '/mavros_node/cmd/land'
        )

        # State cache
        self.current_state = None
        self.current_position = None
        self.current_global_position = None
        self.current_battery = None
        self.current_velocity = None

        # Wait for MAVROS services to be available
        self.get_logger().info('Waiting for MAVROS services to become available...')
        self.wait_for_mavros_services(timeout_sec=30.0)

        # MQTT Client
        self.mqtt_client = mqtt.Client(client_id=f'ros2_bridge_{self.drone_id}')
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message

        # Connect to MQTT broker
        try:
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            self.get_logger().info('MQTT client connected and loop started')
        except Exception as e:
            self.get_logger().error(f'Failed to connect to MQTT broker: {e}')

        # Timer for periodic telemetry publishing
        self.telemetry_timer = self.create_timer(0.5, self.publish_telemetry)  # 2 Hz

    def wait_for_mavros_services(self, timeout_sec=30.0):
        """Wait for all MAVROS services to become available"""
        services = [
            (self.arming_client, 'arming'),
            (self.set_mode_client, 'set_mode'),
            (self.takeoff_client, 'takeoff'),
            (self.land_client, 'land')
        ]

        all_ready = True
        for client, name in services:
            self.get_logger().info(f'Waiting for {name} service...')
            if not client.wait_for_service(timeout_sec=timeout_sec):
                self.get_logger().error(f'{name} service not available after {timeout_sec}s')
                all_ready = False
            else:
                self.get_logger().info(f'{name} service ready!')

        if all_ready:
            self.get_logger().info('All MAVROS services are ready!')
        else:
            self.get_logger().warn('Some MAVROS services are not ready, commands may fail')

        return all_ready

    def on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            self.get_logger().info(f'Connected to MQTT broker')
            # Subscribe to command topic
            command_topic = f'drone/{self.drone_id}/command'
            client.subscribe(command_topic)
            self.get_logger().info(f'Subscribed to {command_topic}')
        else:
            self.get_logger().error(f'Failed to connect to MQTT broker, rc: {rc}')

    def on_mqtt_message(self, client, userdata, msg):
        """Callback when MQTT message received"""
        try:
            payload = json.loads(msg.payload.decode())
            command = payload.get('command')
            params = payload.get('params', {})

            self.get_logger().info(f'Received command: {command} with params: {params}')

            # Handle command
            if command == 'ARM':
                self.handle_arm_command(True)
            elif command == 'DISARM':
                self.handle_arm_command(False)
            elif command == 'TAKEOFF':
                altitude = params.get('altitude', 5.0)
                self.handle_takeoff_command(altitude)
            elif command == 'LAND':
                self.handle_land_command()
            else:
                self.get_logger().warning(f'Unknown command: {command}')

        except json.JSONDecodeError as e:
            self.get_logger().error(f'Failed to decode MQTT message: {e}')
        except Exception as e:
            self.get_logger().error(f'Error processing MQTT message: {e}')

    # ==================== ROS2 Callbacks ====================

    def state_callback(self, msg):
        """MAVROS state callback"""
        self.current_state = msg
        self.get_logger().info(f'State received: connected={msg.connected}, armed={msg.armed}, mode={msg.mode}')
        self.publish_state()

    def local_position_callback(self, msg):
        """Local position callback"""
        self.current_position = msg
        self.get_logger().debug(f'Position received: x={msg.pose.position.x}, y={msg.pose.position.y}, z={msg.pose.position.z}')

    def global_position_callback(self, msg):
        """Global position callback"""
        self.current_global_position = msg

    def battery_callback(self, msg):
        """Battery state callback"""
        self.current_battery = msg

    def velocity_callback(self, msg):
        """Velocity callback"""
        self.current_velocity = msg

    # ==================== MQTT Publishing ====================

    def publish_telemetry(self):
        """Publish telemetry to MQTT - publishes available data even if some sensors are missing"""
        # Build telemetry with available data
        telemetry = {}

        # Add state information if available
        if self.current_state:
            telemetry['connected'] = self.current_state.connected
            telemetry['armed'] = self.current_state.armed
            telemetry['mode'] = self.current_state.mode

        # Add position data if available
        if self.current_position:
            telemetry['position_x'] = self.current_position.pose.position.x
            telemetry['position_y'] = self.current_position.pose.position.y
            telemetry['position_z'] = self.current_position.pose.position.z
            telemetry['orientation_x'] = self.current_position.pose.orientation.x
            telemetry['orientation_y'] = self.current_position.pose.orientation.y
            telemetry['orientation_z'] = self.current_position.pose.orientation.z
            telemetry['orientation_w'] = self.current_position.pose.orientation.w

        # Add global position if available
        if self.current_global_position:
            telemetry['latitude'] = self.current_global_position.latitude
            telemetry['longitude'] = self.current_global_position.longitude
            telemetry['altitude'] = self.current_global_position.altitude

        # Add velocity if available
        if self.current_velocity:
            telemetry['velocity_x'] = self.current_velocity.twist.linear.x
            telemetry['velocity_y'] = self.current_velocity.twist.linear.y
            telemetry['velocity_z'] = self.current_velocity.twist.linear.z

        # Add battery if available
        if self.current_battery:
            telemetry['battery'] = self.current_battery.percentage * 100

        # Only publish if we have at least state or position data
        if telemetry:
            topic = f'drone/{self.drone_id}/telemetry'
            self.mqtt_client.publish(topic, json.dumps(telemetry), qos=1)
            self.get_logger().debug(f'Published telemetry: {len(telemetry)} fields')
        else:
            self.get_logger().warn('No telemetry data available to publish', throttle_duration_sec=5.0)

    def publish_state(self):
        """Publish state to MQTT"""
        if not self.current_state:
            return

        state = {
            'connected': self.current_state.connected,
            'armed': self.current_state.armed,
            'mode': self.current_state.mode,
        }

        topic = f'drone/{self.drone_id}/state'
        self.mqtt_client.publish(topic, json.dumps(state), qos=1, retain=True)

    def publish_command_result(self, command: str, success: bool, message: str):
        """Publish command execution result to MQTT"""
        result = {
            'command': command,
            'success': success,
            'message': message,
            'timestamp': self.get_clock().now().to_msg().sec
        }

        topic = f'drone/{self.drone_id}/command_result'
        self.mqtt_client.publish(topic, json.dumps(result), qos=1)
        self.get_logger().info(f'Published command result: {result}')

    # ==================== Command Handlers ====================

    def handle_arm_command(self, arm: bool):
        """Handle ARM/DISARM command"""
        command_name = 'ARM' if arm else 'DISARM'

        if not self.arming_client.wait_for_service(timeout_sec=5.0):
            error_msg = 'Arming service not available'
            self.get_logger().error(error_msg)
            self.publish_command_result(command_name, False, error_msg)
            return

        request = CommandBool.Request()
        request.value = arm

        future = self.arming_client.call_async(request)
        future.add_done_callback(lambda f: self.arm_callback(f, arm))

    def arm_callback(self, future, arm: bool):
        """Callback for arming service"""
        command_name = 'ARM' if arm else 'DISARM'
        action = 'armed' if arm else 'disarmed'

        try:
            response = future.result()
            if response.success:
                success_msg = f'Drone {action} successfully'
                self.get_logger().info(success_msg)
                self.publish_command_result(command_name, True, success_msg)
                self.publish_state()
            else:
                error_msg = f'Failed to {action.lower()} drone - PX4 rejected command (check GPS fix, flight mode, or safety checks)'
                self.get_logger().error(error_msg)
                self.publish_command_result(command_name, False, error_msg)
        except Exception as e:
            error_msg = f'Arming service call failed: {str(e)}'
            self.get_logger().error(error_msg)
            self.publish_command_result(command_name, False, error_msg)

    def handle_takeoff_command(self, altitude: float):
        """Handle TAKEOFF command"""
        # First, ensure drone is armed
        if not self.current_state or not self.current_state.armed:
            error_msg = 'Cannot takeoff: drone must be armed first'
            self.get_logger().warning(error_msg)
            self.publish_command_result('TAKEOFF', False, error_msg)
            return

        if not self.takeoff_client.wait_for_service(timeout_sec=5.0):
            error_msg = 'Takeoff service not available'
            self.get_logger().error(error_msg)
            self.publish_command_result('TAKEOFF', False, error_msg)
            return

        request = CommandTOL.Request()
        request.altitude = altitude

        future = self.takeoff_client.call_async(request)
        future.add_done_callback(lambda f: self.takeoff_callback(f, altitude))

    def takeoff_callback(self, future, altitude: float):
        """Callback for takeoff service"""
        try:
            response = future.result()
            if response.success:
                success_msg = f'Takeoff command sent (altitude: {altitude}m)'
                self.get_logger().info(success_msg)
                self.publish_command_result('TAKEOFF', True, success_msg)
            else:
                error_msg = f'Takeoff command failed - PX4 rejected command'
                self.get_logger().error(error_msg)
                self.publish_command_result('TAKEOFF', False, error_msg)
        except Exception as e:
            error_msg = f'Takeoff service call failed: {str(e)}'
            self.get_logger().error(error_msg)
            self.publish_command_result('TAKEOFF', False, error_msg)

    def handle_land_command(self):
        """Handle LAND command"""
        if not self.land_client.wait_for_service(timeout_sec=5.0):
            error_msg = 'Land service not available'
            self.get_logger().error(error_msg)
            self.publish_command_result('LAND', False, error_msg)
            return

        request = CommandTOL.Request()
        future = self.land_client.call_async(request)
        future.add_done_callback(self.land_callback)

    def land_callback(self, future):
        """Callback for land service"""
        try:
            response = future.result()
            if response.success:
                success_msg = 'Land command sent'
                self.get_logger().info(success_msg)
                self.publish_command_result('LAND', True, success_msg)
            else:
                error_msg = 'Land command failed - PX4 rejected command'
                self.get_logger().error(error_msg)
                self.publish_command_result('LAND', False, error_msg)
        except Exception as e:
            error_msg = f'Land service call failed: {str(e)}'
            self.get_logger().error(error_msg)
            self.publish_command_result('LAND', False, error_msg)

    def destroy_node(self):
        """Cleanup on node shutdown"""
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MQTTBridgeNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
