import { useEffect, useState } from 'react';
import * as THREE from 'three';

interface Zone {
  zone_id: string;
  name: string;
  type: 'jamming' | 'no-fly' | 'restricted';
  center: {
    x: number;
    y: number;
    z: number;
  };
  radius: number;
}

const ZONE_COLORS: Record<string, string> = {
  jamming: '#FF0000',    // Red
  'no-fly': '#FF8800',   // Orange
  restricted: '#FFFF00', // Yellow
};

const ZONE_HEIGHT = 50; // meters (cylinder height)
const TERRAIN_OFFSET_Y = -300;

export default function ExclusionZones() {
  const [zones, setZones] = useState<Zone[]>([]);

  useEffect(() => {
    // Fetch active zones from simulation control API
    const fetchZones = async () => {
      try {
        const response = await fetch('http://localhost:8080/zones');
        if (response.ok) {
          const data = await response.json();
          setZones(data.zones || []);
        }
      } catch (error) {
        console.error('Failed to fetch exclusion zones:', error);
      }
    };

    fetchZones();

    // Poll every 5 seconds for updates
    const interval = setInterval(fetchZones, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <group>
      {zones.map((zone) => (
        <ZoneCylinder key={zone.zone_id} zone={zone} />
      ))}
    </group>
  );
}

function ZoneCylinder({ zone }: { zone: Zone }) {
  const color = ZONE_COLORS[zone.type] || '#888888';

  return (
    <mesh
      position={[
        zone.center.x,
        zone.center.y + TERRAIN_OFFSET_Y,
        zone.center.z + ZONE_HEIGHT / 2
      ]}
    >
      <cylinderGeometry args={[zone.radius, zone.radius, ZONE_HEIGHT, 32]} />
      <meshStandardMaterial
        color={color}
        transparent
        opacity={0.3}
        side={THREE.DoubleSide}
      />

      {/* Zone label */}
      <mesh position={[0, 0, ZONE_HEIGHT / 2 + 10]}>
        <boxGeometry args={[0.1, 0.1, 0.1]} />
        <meshBasicMaterial color={color} />
      </mesh>
    </mesh>
  );
}
