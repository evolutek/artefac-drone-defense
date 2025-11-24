import { useEffect, useMemo, useState } from 'react';
import { useLoader } from '@react-three/fiber';
import * as THREE from 'three';

// Simulation terrain configuration (from CLAUDE.md)
const TERRAIN_WIDTH = 1200;  // meters (X axis)
const TERRAIN_DEPTH = 1200;  // meters (Y axis)
const TERRAIN_MAX_HEIGHT = 201.66; // meters (actual max elevation)
const TERRAIN_OFFSET_Y = -300; // meters (Y offset)
const TERRAIN_OFFSET_Z = -5;  // meters (Z offset)

interface HeightmapData {
  width: number;
  height: number;
  minHeight: number;
  maxHeight: number;
  heights: number[];
}

export default function Terrain() {
  const [heightmapData, setHeightmapData] = useState<HeightmapData | null>(null);
  const world = useMemo(() => new URL(window.location.href).searchParams.get('world') || 'model', []);

  // Load heightmap data
  useEffect(() => {
    fetch('/terrain/heightmap_data.json')
      .then(res => res.json())
      .then(data => setHeightmapData(data))
      .catch(err => console.error('Failed to load heightmap:', err));
  }, []);

  // Load texture depending on world
  const texturePath = world === 'harmonic_heightmap'
    ? '/terrain/terrain_rgb.png'
    : '/terrain/topographic_map.png';
  const texture = useLoader(THREE.TextureLoader, texturePath);

  if (!heightmapData) {
    return null; // Loading...
  }

  // Create terrain geometry from heightmap
  const geometry = createTerrainGeometry(heightmapData);

  return (
    <mesh
      geometry={geometry}
      position={[0, TERRAIN_OFFSET_Y, TERRAIN_OFFSET_Z]}
      rotation={[-Math.PI / 2, 0, 0]} // Rotate to horizontal plane
      receiveShadow
    >
      <meshStandardMaterial
        map={texture}
        side={THREE.DoubleSide}
        roughness={0.8}
        metalness={0.2}
      />
    </mesh>
  );
}

function createTerrainGeometry(data: HeightmapData): THREE.BufferGeometry {
  const { width, height, heights, maxHeight: dataMaxHeight } = data;

  // Scale factor: heightmap max is ~67m, actual terrain max is 201.66m
  const heightScale = TERRAIN_MAX_HEIGHT / (dataMaxHeight || 1);

  // Create plane geometry with heightmap resolution
  const geometry = new THREE.PlaneGeometry(
    TERRAIN_WIDTH,
    TERRAIN_DEPTH,
    width - 1,  // segments in X
    height - 1  // segments in Y
  );

  // Apply heightmap to vertices
  const vertices = geometry.attributes.position.array as Float32Array;

  for (let i = 0; i < heights.length; i++) {
    const vertexIndex = i * 3 + 2; // Z coordinate (height)
    vertices[vertexIndex] = heights[i] * heightScale;
  }

  // Recompute normals for proper lighting
  geometry.computeVertexNormals();

  return geometry;
}
