import { useWebSocket } from '../hooks/useWebSocket';
import { useState, useEffect } from 'react';

interface DroneTelemetryProps {
  droneId: string;
}

interface TelemetryState {
  connected?: boolean;
  armed?: boolean;
  mode?: string;
  battery?: number;
  position_x?: number;
  position_y?: number;
  position_z?: number;
  latitude?: number;
  longitude?: number;
  altitude?: number;
  velocity_x?: number;
  velocity_y?: number;
  velocity_z?: number;
}

export function DroneTelemetry({ droneId }: DroneTelemetryProps) {
  const { telemetry, isConnected } = useWebSocket(droneId);
  const [aggregatedData, setAggregatedData] = useState<TelemetryState>({});

  // Aggregate all telemetry updates into a single state
  useEffect(() => {
    if (telemetry?.data) {
      setAggregatedData(prev => ({
        ...prev,
        ...telemetry.data
      }));
    }
  }, [telemetry]);

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
          {/* Battery - Always at top */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Battery</h3>
            <div className="relative pt-1">
              <div className="flex mb-2 items-center justify-between">
                <div>
                  <span className="text-xs font-semibold inline-block py-1 px-2 uppercase rounded-full text-blue-600 bg-blue-200">
                    {aggregatedData.battery !== undefined ? aggregatedData.battery.toFixed(0) : 'N/A'}%
                  </span>
                </div>
              </div>
              <div className="overflow-hidden h-2 mb-4 text-xs flex rounded bg-gray-200">
                <div
                  style={{ width: `${aggregatedData.battery || 0}%` }}
                  className={`shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center ${
                    (aggregatedData.battery || 0) > 50
                      ? 'bg-green-500'
                      : (aggregatedData.battery || 0) > 20
                      ? 'bg-yellow-500'
                      : 'bg-red-500'
                  }`}
                ></div>
              </div>
            </div>
          </div>

          {/* State - Always visible */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Status</h3>
            <div className="space-y-2">
              <DataRow label="Connected" value={aggregatedData.connected ? 'Yes' : 'No'} />
              <DataRow label="Armed" value={aggregatedData.armed ? 'Yes' : 'No'} />
              <DataRow label="Mode" value={aggregatedData.mode} />
            </div>
          </div>

          {/* Position (Local) */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Position (Local)</h3>
            <div className="space-y-2">
              <DataRow label="X" value={aggregatedData.position_x} unit="m" />
              <DataRow label="Y" value={aggregatedData.position_y} unit="m" />
              <DataRow label="Z" value={aggregatedData.position_z} unit="m" />
            </div>
          </div>

          {/* Global Position */}
          {(aggregatedData.latitude || aggregatedData.longitude || aggregatedData.altitude) && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Position (Global)</h3>
              <div className="space-y-2">
                <DataRow label="Latitude" value={aggregatedData.latitude} unit="°" />
                <DataRow label="Longitude" value={aggregatedData.longitude} unit="°" />
                <DataRow label="Altitude" value={aggregatedData.altitude} unit="m" />
              </div>
            </div>
          )}

          {/* Velocity */}
          {(aggregatedData.velocity_x || aggregatedData.velocity_y || aggregatedData.velocity_z) && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Velocity</h3>
              <div className="space-y-2">
                <DataRow label="Vx" value={aggregatedData.velocity_x} unit="m/s" />
                <DataRow label="Vy" value={aggregatedData.velocity_y} unit="m/s" />
                <DataRow label="Vz" value={aggregatedData.velocity_z} unit="m/s" />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
