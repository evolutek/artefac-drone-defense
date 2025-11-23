import { useEffect, useState } from 'react';
import { Text, Cone } from '@react-three/drei';

interface Drone {
  drone_id: string;
  position_x?: number;
  position_y?: number;
  position_z?: number;
  orientation_x?: number;
  orientation_y?: number;
  orientation_z?: number;
  orientation_w?: number;
  is_armed?: boolean;
  mavros_connected?: boolean;
}

// Convert quaternion to yaw angle (heading)
function quaternionToYaw(x: number, y: number, z: number, w: number): number {
  // Extract yaw from quaternion
  const siny_cosp = 2 * (w * z + x * y);
  const cosy_cosp = 1 - 2 * (y * y + z * z);
  return Math.atan2(siny_cosp, cosy_cosp);
}

const TERRAIN_OFFSET_Y = -300;

export default function DroneMarkers() {
  const [drones, setDrones] = useState<Drone[]>([]);

  useEffect(() => {
    // Fetch active drones from backend
    const fetchDrones = async () => {
      try {
        const response = await fetch('http://localhost:8000/drones');
        if (response.ok) {
          const data = await response.json();
          // API returns array directly (not wrapped in {drones: []})
          setDrones(Array.isArray(data) ? data : []);
        }
      } catch (error) {
        // Silently fail if backend is not running - this is normal when viewing simulation without backend
        setDrones([]);
      }
    };

    fetchDrones();

    // Poll every 500ms for real-time updates
    const interval = setInterval(fetchDrones, 500);
    return () => clearInterval(interval);
  }, []);

  return (
    <group>
      {drones.map((drone) => (
        <DroneMarker key={drone.drone_id} drone={drone} />
      ))}
    </group>
  );
}

function DroneMarker({ drone }: { drone: Drone }) {
  // Use default values if position not available
  const x = drone.position_x ?? 0;
  const y = drone.position_y ?? 0;
  const z = drone.position_z ?? 0;

  // Calculate heading from quaternion orientation
  let heading = 0;
  if (drone.orientation_x !== undefined && drone.orientation_y !== undefined &&
      drone.orientation_z !== undefined && drone.orientation_w !== undefined) {
    heading = quaternionToYaw(
      drone.orientation_x,
      drone.orientation_y,
      drone.orientation_z,
      drone.orientation_w
    );
  }

  const color = drone.is_armed ? '#00FF00' : '#FFA500'; // Green if armed, orange if disarmed
  const opacity = drone.mavros_connected ? 1.0 : 0.5;

  return (
    <group
      position={[x, y + TERRAIN_OFFSET_Y, z]}
      rotation={[0, 0, -heading]} // Rotate to show heading direction
    >
      {/* Drone body (sphere) */}
      <mesh>
        <sphereGeometry args={[3, 16, 16]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={0.5}
          transparent
          opacity={opacity}
        />
      </mesh>

      {/* Direction arrow (cone) */}
      <Cone
        args={[2, 8, 4]}
        position={[8, 0, 0]}
        rotation={[0, 0, -Math.PI / 2]}
      >
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={0.3}
          transparent
          opacity={opacity}
        />
      </Cone>

      {/* Drone ID label */}
      <Text
        position={[0, 0, 8]}
        fontSize={5}
        color="#FFFFFF"
        anchorX="center"
        anchorY="middle"
        outlineWidth={0.5}
        outlineColor="#000000"
      >
        {drone.drone_id}
      </Text>

      {/* Altitude label */}
      <Text
        position={[0, 0, -6]}
        fontSize={4}
        color="#AAAAAA"
        anchorX="center"
        anchorY="middle"
      >
        {z.toFixed(1)}m
      </Text>
    </group>
  );
}
