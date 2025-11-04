#!/usr/bin/env python3
"""
MQTT Bridge Node for Artefac Drone Defense
Bridges ROS2 MAVROS topics ↔ MQTT for backend communication
"""
import os
import json
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
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
        # Note: MAVROS publishes on /state (no namespace prefix for core topics)
        self.state_sub = self.create_subscription(
            State,
            '/state',
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
        # Note: MAVROS services are published under /mavros_node namespace
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
        """Publish telemetry to MQTT"""
        if not self.current_position:
            return

        telemetry = {
            'position_x': self.current_position.pose.position.x,
            'position_y': self.current_position.pose.position.y,
            'position_z': self.current_position.pose.position.z,
            'orientation_x': self.current_position.pose.orientation.x,
            'orientation_y': self.current_position.pose.orientation.y,
            'orientation_z': self.current_position.pose.orientation.z,
            'orientation_w': self.current_position.pose.orientation.w,
        }

        if self.current_global_position:
            telemetry['latitude'] = self.current_global_position.latitude
            telemetry['longitude'] = self.current_global_position.longitude
            telemetry['altitude'] = self.current_global_position.altitude

        if self.current_velocity:
            telemetry['velocity_x'] = self.current_velocity.twist.linear.x
            telemetry['velocity_y'] = self.current_velocity.twist.linear.y
            telemetry['velocity_z'] = self.current_velocity.twist.linear.z

        if self.current_battery:
            telemetry['battery'] = self.current_battery.percentage * 100

        topic = f'drone/{self.drone_id}/telemetry'
        self.mqtt_client.publish(topic, json.dumps(telemetry), qos=1)

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

    # ==================== Command Handlers ====================

    def handle_arm_command(self, arm: bool):
        """Handle ARM/DISARM command"""
        if not self.arming_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().error('Arming service not available')
            return

        request = CommandBool.Request()
        request.value = arm

        future = self.arming_client.call_async(request)
        future.add_done_callback(lambda f: self.arm_callback(f, arm))

    def arm_callback(self, future, arm: bool):
        """Callback for arming service"""
        try:
            response = future.result()
            if response.success:
                action = 'armed' if arm else 'disarmed'
                self.get_logger().info(f'Drone {action} successfully')
                self.publish_state()
            else:
                self.get_logger().error(f'Failed to arm/disarm drone')
        except Exception as e:
            self.get_logger().error(f'Arming service call failed: {e}')

    def handle_takeoff_command(self, altitude: float):
        """Handle TAKEOFF command"""
        # First, ensure drone is armed
        if not self.current_state or not self.current_state.armed:
            self.get_logger().info('Arming drone before takeoff...')
            self.handle_arm_command(True)
            # Wait a bit for arming
            import time
            time.sleep(2)

        if not self.takeoff_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().error('Takeoff service not available')
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
                self.get_logger().info(f'Takeoff command sent (altitude: {altitude}m)')
            else:
                self.get_logger().error('Takeoff command failed')
        except Exception as e:
            self.get_logger().error(f'Takeoff service call failed: {e}')

    def handle_land_command(self):
        """Handle LAND command"""
        if not self.land_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().error('Land service not available')
            return

        request = CommandTOL.Request()
        future = self.land_client.call_async(request)
        future.add_done_callback(self.land_callback)

    def land_callback(self, future):
        """Callback for land service"""
        try:
            response = future.result()
            if response.success:
                self.get_logger().info('Land command sent')
            else:
                self.get_logger().error('Land command failed')
        except Exception as e:
            self.get_logger().error(f'Land service call failed: {e}')

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
