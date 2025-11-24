import { Link } from 'react-router-dom';
import SimulationCanvas from '../components/SimulationCanvas';
import Terrain from '../components/Terrain';
import CoordinateGrid from '../components/CoordinateGrid';
import ExclusionZones from '../components/ExclusionZones';
import DroneMarkers from '../components/DroneMarkers';

export function MapView() {
  const world = new URL(window.location.href).searchParams.get('world') || 'model';
  return (
    <div className="h-screen w-screen flex flex-col">
      {/* Header */}
      <header className="bg-blue-600 text-white shadow-lg z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Artefac Drone Defense - Local Simulation Map</h1>
              <p className="text-blue-100 text-sm mt-1">World: {world}</p>
              <p className="text-blue-100 text-sm mt-1">1200m × 1200m simulation area with local coordinates</p>
            </div>
            <div className="flex items-center gap-4">
              <Link
                to="/debug"
                className="bg-white text-blue-600 px-4 py-2 rounded-lg font-semibold hover:bg-blue-50 transition-colors"
              >
                Debug Dashboard →
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Three.js Canvas */}
      <main className="flex-1 relative">
        <SimulationCanvas>
          {/* Terrain with heightmap and texture */}
          <Terrain />

          {/* Coordinate grid (100m spacing) */}
          <CoordinateGrid />

          {/* Exclusion zones (cylinders) */}
          <ExclusionZones />

          {/* Drone markers */}
          <DroneMarkers />
        </SimulationCanvas>

        {/* Info Overlay */}
        <div className="absolute top-4 left-4 bg-black bg-opacity-70 text-white rounded-lg shadow-lg p-4 max-w-sm z-10">
          <h3 className="font-bold mb-2">Simulation Info</h3>
          <div className="text-sm space-y-1">
            <div>
              <span className="font-semibold">Area:</span> 1200m × 1200m
            </div>
            <div>
              <span className="font-semibold">Max Height:</span> 201.66m
            </div>
            <div>
              <span className="font-semibold">Coordinates:</span> Local (X, Y, Z in meters)
            </div>
            <div>
              <span className="font-semibold">Engine:</span> Three.js + React Three Fiber
            </div>
            <div className="text-xs text-gray-300 mt-2 pt-2 border-t border-gray-600">
              Toggle 2D/3D with button in top-right corner of canvas
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
