import { useWebSocket } from '../hooks/useWebSocket';

interface DroneTelemetryProps {
  droneId: string;
}

export function DroneTelemetry({ droneId }: DroneTelemetryProps) {
  const { telemetry, isConnected } = useWebSocket(droneId);

  const DataRow = ({ label, value, unit = '' }: { label: string; value: any; unit?: string }) => (
    <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
      <span className="font-medium text-gray-700">{label}</span>
      <span className="font-mono text-gray-900">
        {value !== null && value !== undefined ? `${typeof value === 'number' ? value.toFixed(2) : value} ${unit}` : 'N/A'}
      </span>
    </div>
  );

  const ConnectionStatus = () => (
    <div className="mb-4">
      <span
        className={`px-3 py-1 rounded-full text-sm font-semibold ${
          isConnected
            ? 'bg-green-100 text-green-800'
            : 'bg-red-100 text-red-800'
        }`}
      >
        {isConnected ? '● Connected' : '● Disconnected'}
      </span>
    </div>
  );

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold mb-4">Telemetry - {droneId}</h2>

      <ConnectionStatus />

      {!telemetry && (
        <p className="text-gray-600">Waiting for telemetry data...</p>
      )}

      {telemetry && (
        <div className="space-y-6">
          {/* Position */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Position (Local)</h3>
            <div className="space-y-2">
              <DataRow label="X" value={telemetry.data.position_x} unit="m" />
              <DataRow label="Y" value={telemetry.data.position_y} unit="m" />
              <DataRow label="Z" value={telemetry.data.position_z} unit="m" />
            </div>
          </div>

          {/* Global Position */}
          {(telemetry.data.latitude || telemetry.data.longitude || telemetry.data.altitude) && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Position (Global)</h3>
              <div className="space-y-2">
                <DataRow label="Latitude" value={telemetry.data.latitude} unit="°" />
                <DataRow label="Longitude" value={telemetry.data.longitude} unit="°" />
                <DataRow label="Altitude" value={telemetry.data.altitude} unit="m" />
              </div>
            </div>
          )}

          {/* Velocity */}
          {(telemetry.data.velocity_x || telemetry.data.velocity_y || telemetry.data.velocity_z) && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Velocity</h3>
              <div className="space-y-2">
                <DataRow label="Vx" value={telemetry.data.velocity_x} unit="m/s" />
                <DataRow label="Vy" value={telemetry.data.velocity_y} unit="m/s" />
                <DataRow label="Vz" value={telemetry.data.velocity_z} unit="m/s" />
              </div>
            </div>
          )}

          {/* State */}
          {telemetry.type === 'state' && (
            <div>
              <h3 className="text-lg font-semibold mb-3">State</h3>
              <div className="space-y-2">
                <DataRow label="Connected" value={telemetry.data.connected ? 'Yes' : 'No'} />
                <DataRow label="Armed" value={telemetry.data.armed ? 'Yes' : 'No'} />
                <DataRow label="Mode" value={telemetry.data.mode} />
              </div>
            </div>
          )}

          {/* Battery */}
          {telemetry.data.battery !== undefined && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Battery</h3>
              <div className="relative pt-1">
                <div className="flex mb-2 items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold inline-block py-1 px-2 uppercase rounded-full text-blue-600 bg-blue-200">
                      {telemetry.data.battery?.toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div className="overflow-hidden h-2 mb-4 text-xs flex rounded bg-gray-200">
                  <div
                    style={{ width: `${telemetry.data.battery}%` }}
                    className={`shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center ${
                      (telemetry.data.battery || 0) > 50
                        ? 'bg-green-500'
                        : (telemetry.data.battery || 0) > 20
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                    }`}
                  ></div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
