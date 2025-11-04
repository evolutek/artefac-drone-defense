import { HealthDashboard } from './components/HealthDashboard';
import { DroneControl } from './components/DroneControl';
import { DroneTelemetry } from './components/DroneTelemetry';

function App() {
  const droneId = 'drone_1'; // MVP: hardcoded for single drone

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-blue-600 text-white shadow-lg">
        <div className="container mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold">Artefac Drone Defense - MVP</h1>
          <p className="text-blue-100 mt-2">Real-time Drone Control & Monitoring</p>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 gap-6">
          {/* Health Dashboard */}
          <HealthDashboard />

          {/* Drone Control and Telemetry */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <DroneControl droneId={droneId} />
            <DroneTelemetry droneId={droneId} />
          </div>

          {/* Info Section */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-blue-900 mb-2">Usage Instructions</h3>
            <ol className="list-decimal list-inside space-y-2 text-blue-800">
              <li>Check that all systems are <strong>Online</strong> in the Health dashboard</li>
              <li>Click <strong>ARM</strong> to activate the drone motors</li>
              <li>Set takeoff altitude (default: 5m) and click <strong>TAKEOFF</strong></li>
              <li>Monitor real-time telemetry on the right panel</li>
              <li>Click <strong>LAND</strong> to bring the drone down</li>
              <li>Click <strong>DISARM</strong> to deactivate motors after landing</li>
            </ol>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 text-white mt-12">
        <div className="container mx-auto px-4 py-6 text-center">
          <p className="text-gray-400">Artefac Drone Defense © 2025 Evolutek</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
