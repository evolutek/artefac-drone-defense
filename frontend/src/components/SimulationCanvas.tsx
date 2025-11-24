import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, OrthographicCamera } from '@react-three/drei';
import { useState, useRef, forwardRef, useImperativeHandle, Ref } from 'react';
import * as THREE from 'three';

// Simulation bounds (from Gazebo world)
const TERRAIN_WIDTH = 1200;  // meters (X axis)
const TERRAIN_HEIGHT = 1200; // meters (Y axis)

interface SimulationCanvasProps {
  children?: React.ReactNode;
}

type ZoomControllerHandle = { applyZoom: (delta: number, is3D: boolean) => void };

function CameraZoomController(_: {}, ref: Ref<ZoomControllerHandle>) {
  const { camera, invalidate } = useThree();
  useImperativeHandle(ref, () => ({
    applyZoom(delta: number, is3D: boolean) {
      const dir = Math.sign(delta);
      if (!dir) return;
      if (is3D && (camera as THREE.Camera).type === 'PerspectiveCamera') {
        const target = new THREE.Vector3(0, 0, 0);
        const step = dir * 20;
        const vec = new THREE.Vector3().subVectors(target, (camera as THREE.PerspectiveCamera).position).normalize();
        (camera as THREE.PerspectiveCamera).position.addScaledVector(vec, step);
        (camera as THREE.PerspectiveCamera).updateProjectionMatrix();
      } else if ((camera as THREE.Camera).type === 'OrthographicCamera') {
        const ortho = camera as THREE.OrthographicCamera;
        const step = dir * 0.05;
        ortho.zoom = Math.min(Math.max(ortho.zoom + step, 0.3), 3);
        ortho.updateProjectionMatrix();
      }
      invalidate();
    }
  }), [camera, invalidate]);
  return null as any;
}

const CameraZoomControllerWithRef = forwardRef<ZoomControllerHandle, {}>(CameraZoomController);

export default function SimulationCanvas({ children }: SimulationCanvasProps) {
  const [is3D, setIs3D] = useState(true);
  const scrollState = useRef<{ acc: number; dir: number }>({ acc: 0, dir: 0 });
  const lastSwitchRef = useRef(0);
  const SCROLL_THRESHOLD = 150;
  const SWITCH_COOLDOWN_MS = 250;
  const zoomCtrlRef = useRef<ZoomControllerHandle | null>(null);

  return (
    <div
      className="relative w-full h-full"
      onWheelCapture={(e) => {
        if (Date.now() - lastSwitchRef.current < SWITCH_COOLDOWN_MS) return;
        const raw = e.deltaY || 0;
        const delta = e.deltaMode === 1 ? raw * 16 : raw;
        zoomCtrlRef.current?.applyZoom(delta, is3D);
        const dir = delta > 0 ? 1 : delta < 0 ? -1 : 0;
        if (!dir) return;
        if (scrollState.current.dir !== dir) {
          scrollState.current.acc = 0;
          scrollState.current.dir = dir;
        }
        scrollState.current.acc += delta;
        if (is3D && scrollState.current.acc >= SCROLL_THRESHOLD && dir === 1) {
          scrollState.current.acc = 0;
          lastSwitchRef.current = Date.now();
          setIs3D(false);
        } else if (!is3D && scrollState.current.acc <= -SCROLL_THRESHOLD && dir === -1) {
          scrollState.current.acc = 0;
          lastSwitchRef.current = Date.now();
          setIs3D(true);
        }
      }}
    >
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
              enableZoom={false}
              enableDamping
              dampingFactor={0.05}
              minDistance={100}
              maxDistance={2000}
              maxPolarAngle={Math.PI / 2.1}
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
              enableZoom={false}
              enableRotate={false}
              enableDamping
              dampingFactor={0.05}
              minZoom={0.3}
              maxZoom={3}
              target={[0, -300, -5]}
            />
          </>
        )}

        <CameraZoomControllerWithRef ref={zoomCtrlRef} />
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
