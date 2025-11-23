import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, OrthographicCamera } from '@react-three/drei';
import { useState } from 'react';

// Simulation bounds (from Gazebo world)
const TERRAIN_WIDTH = 1200;  // meters (X axis)
const TERRAIN_HEIGHT = 1200; // meters (Y axis)

interface SimulationCanvasProps {
  children?: React.ReactNode;
}

export default function SimulationCanvas({ children }: SimulationCanvasProps) {
  const [is3D, setIs3D] = useState(true);

  return (
    <div className="relative w-full h-full">
      {/* Toggle Button */}
      <div className="absolute top-4 right-4 z-10">
        <button
          onClick={() => setIs3D(!is3D)}
          className="px-4 py-2 bg-blue-600 text-white rounded-md shadow-lg hover:bg-blue-700 transition-colors"
        >
          {is3D ? '2D View' : '3D View'}
        </button>
      </div>

      {/* Three.js Canvas - Key prop forces remount on view change */}
      <Canvas key={is3D ? '3d' : '2d'}>
        {/* Lighting */}
        <ambientLight intensity={0.5} />
        <directionalLight position={[100, 100, 50]} intensity={0.8} castShadow />
        <hemisphereLight args={['#87CEEB', '#8B4513', 0.6]} />

        {/* Camera Setup */}
        {is3D ? (
          <>
            <PerspectiveCamera
              makeDefault
              position={[800, 600, 400]}
              fov={60}
            />
            <OrbitControls
              enableDamping
              dampingFactor={0.05}
              minDistance={100}
              maxDistance={2000}
              maxPolarAngle={Math.PI / 2.1} // Prevent camera going below ground
            />
          </>
        ) : (
          <>
            <OrthographicCamera
              makeDefault
              position={[0, 700, -5]} // High above terrain on Y axis
              zoom={0.8}
              near={0.1}
              far={2000}
            />
            <OrbitControls
              enableRotate={false}
              enableDamping
              dampingFactor={0.05}
              minZoom={0.3}
              maxZoom={3}
              target={[0, -300, -5]} // Look at terrain center (Y=-300, Z=-5)
            />
          </>
        )}

        {/* Scene Content */}
        {children}

        {/* Helpers (for development) */}
        <axesHelper args={[500]} />
        <gridHelper args={[TERRAIN_WIDTH, 12, '#444444', '#888888']} rotation={[0, 0, 0]} />
      </Canvas>

      {/* View Mode Indicator */}
      <div className="absolute bottom-4 left-4 bg-black bg-opacity-50 text-white px-3 py-1 rounded text-sm">
        {is3D ? '3D View' : '2D View (Top-down)'} | {TERRAIN_WIDTH}m × {TERRAIN_HEIGHT}m
      </div>
    </div>
  );
}
