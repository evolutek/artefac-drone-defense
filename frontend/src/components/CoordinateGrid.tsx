import { Text } from '@react-three/drei';

const TERRAIN_WIDTH = 1200;
const TERRAIN_HEIGHT = 1200;
const GRID_SPACING = 100; // meters
const TERRAIN_OFFSET_Y = -300;

export default function CoordinateGrid() {
  const gridLines: JSX.Element[] = [];
  const labels: JSX.Element[] = [];

  // Generate grid lines and labels
  for (let x = -TERRAIN_WIDTH / 2; x <= TERRAIN_WIDTH / 2; x += GRID_SPACING) {
    // Vertical lines (along Y axis)
    gridLines.push(
      <line key={`v-${x}`}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={2}
            array={new Float32Array([
              x, -TERRAIN_HEIGHT / 2 + TERRAIN_OFFSET_Y, 0,
              x, TERRAIN_HEIGHT / 2 + TERRAIN_OFFSET_Y, 0
            ])}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial color="#666666" opacity={0.3} transparent />
      </line>
    );

    // X axis labels (every 200m to avoid clutter)
    if (x % 200 === 0) {
      labels.push(
        <Text
          key={`label-x-${x}`}
          position={[x, -TERRAIN_HEIGHT / 2 + TERRAIN_OFFSET_Y - 50, 5]}
          fontSize={30}
          color="#FFFFFF"
          anchorX="center"
          anchorY="middle"
        >
          {x}m
        </Text>
      );
    }
  }

  for (let y = -TERRAIN_HEIGHT / 2; y <= TERRAIN_HEIGHT / 2; y += GRID_SPACING) {
    // Horizontal lines (along X axis)
    gridLines.push(
      <line key={`h-${y}`}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={2}
            array={new Float32Array([
              -TERRAIN_WIDTH / 2, y + TERRAIN_OFFSET_Y, 0,
              TERRAIN_WIDTH / 2, y + TERRAIN_OFFSET_Y, 0
            ])}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial color="#666666" opacity={0.3} transparent />
      </line>
    );

    // Y axis labels (every 200m)
    if (y % 200 === 0) {
      labels.push(
        <Text
          key={`label-y-${y}`}
          position={[-TERRAIN_WIDTH / 2 - 50, y + TERRAIN_OFFSET_Y, 5]}
          fontSize={30}
          color="#FFFFFF"
          anchorX="center"
          anchorY="middle"
        >
          {y}m
        </Text>
      );
    }
  }

  // Main axes (thicker, colored lines)
  const mainAxes = (
    <group>
      {/* X axis (red) */}
      <line>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={2}
            array={new Float32Array([
              -TERRAIN_WIDTH / 2, TERRAIN_OFFSET_Y, 1,
              TERRAIN_WIDTH / 2, TERRAIN_OFFSET_Y, 1
            ])}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial color="#FF0000" linewidth={2} />
      </line>

      {/* Y axis (green) */}
      <line>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={2}
            array={new Float32Array([
              0, -TERRAIN_HEIGHT / 2 + TERRAIN_OFFSET_Y, 1,
              0, TERRAIN_HEIGHT / 2 + TERRAIN_OFFSET_Y, 1
            ])}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial color="#00FF00" linewidth={2} />
      </line>
    </group>
  );

  return (
    <group>
      {gridLines}
      {labels}
      {mainAxes}
    </group>
  );
}
