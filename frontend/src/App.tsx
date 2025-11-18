import { HealthDashboard } from './components/HealthDashboard';
import { DroneControl } from './components/DroneControl';
import { DroneTelemetry } from './components/DroneTelemetry';
import { DroneSelector } from './components/DroneSelector';
import { useMultiDroneWebSocket } from './hooks/useMultiDroneWebSocket';

function App() {
  const { connections, connect, disconnect } = useMultiDroneWebSocket();

  // Get array of connected drone IDs for easier iteration
  const connectedDroneIds = Array.from(connections.keys());

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-blue-600 text-white shadow-lg">
        <div className="container mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold">Artefac Drone Defense - Multi-Drone Control</h1>
          <p className="text-blue-100 mt-2">Real-time Multi-Drone Control & Monitoring</p>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 gap-6">
          {/* Health Dashboard */}
          <HealthDashboard />

          {/* Drone Selector */}
          <DroneSelector
            connectedDroneIds={new Set(connectedDroneIds)}
            onConnect={connect}
            onDisconnect={disconnect}
          />

          {/* Info Section - Show only if no drones connected */}
          {connectedDroneIds.length === 0 && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-blue-900 mb-2">Getting Started</h3>
              <ol className="list-decimal list-inside space-y-2 text-blue-800">
                <li>Check that all systems are <strong>Online</strong> in the Health dashboard</li>
                <li>Click <strong>Connect</strong> on one or more drones above</li>
                <li>Use the drone control panels below to command your drones</li>
                <li>Monitor real-time telemetry for each connected drone</li>
              </ol>
            </div>
          )}

          {/* Connected Drones - Control and Telemetry */}
          {connectedDroneIds.map(droneId => {
            const connection = connections.get(droneId);
            if (!connection) return null;

            return (
              <div key={droneId} className="border-2 border-green-500 rounded-lg p-4 bg-green-50">
                <h3 className="text-xl font-bold mb-4 text-green-900">
                  Connected: {droneId}
                </h3>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <DroneControl
                    droneId={droneId}
                    telemetry={connection.telemetry}
                    isConnected={connection.isConnected}
                  />
                  <DroneTelemetry
                    droneId={droneId}
                    telemetry={connection.telemetry}
                    isConnected={connection.isConnected}
                  />
                </div>
              </div>
            );
          })}

          {/* Usage Instructions - Show only if drones are connected */}
          {connectedDroneIds.length > 0 && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-blue-900 mb-2">Usage Instructions</h3>
              <ol className="list-decimal list-inside space-y-2 text-blue-800">
                <li>Click <strong>ARM</strong> to activate the drone motors</li>
                <li>Set takeoff altitude (default: 5m) and click <strong>TAKEOFF</strong></li>
                <li>Monitor real-time telemetry on the right panel</li>
                <li>Click <strong>LAND</strong> to bring the drone down</li>
                <li>Click <strong>DISARM</strong> to deactivate motors after landing</li>
                <li>Use <strong>Disconnect</strong> in the drone selector to stop monitoring a drone</li>
              </ol>
            </div>
          )}
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
