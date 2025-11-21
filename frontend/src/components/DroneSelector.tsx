import { useState, useEffect } from 'react';
import { droneApi } from '../utils/api';
import { DroneStatus } from '../types';
import axios from 'axios';

interface DroneSelectorProps {
  connectedDroneIds: Set<string>;
  onConnect: (droneId: string) => void;
  onDisconnect: (droneId: string) => void;
}

export function DroneSelector({ connectedDroneIds, onConnect, onDisconnect }: DroneSelectorProps) {
  const [availableDrones, setAvailableDrones] = useState<DroneStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchDrones = async () => {
    try {
      setError(null);
      const response = await droneApi.getAll();
      setAvailableDrones(response.data);
    } catch (err) {
      console.error('Failed to fetch drones:', err);
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail || 'Failed to fetch available drones');
      } else {
        setError('Failed to fetch available drones');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDrones();

    // Refresh drone list every 10 seconds
    const interval = setInterval(fetchDrones, 10000);

    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchDrones();
  };

  const handleToggleConnection = (droneId: string) => {
    if (connectedDroneIds.has(droneId)) {
      onDisconnect(droneId);
    } else {
      onConnect(droneId);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-bold mb-4">Available Drones</h2>
        <p className="text-gray-600">Loading drones...</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold">Available Drones</h2>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-100 text-red-800 border border-red-400 rounded-lg">
          {error}
        </div>
      )}

      {availableDrones.length === 0 ? (
        <div className="text-center py-8 text-gray-600">
          <p className="text-lg mb-2">No drones available</p>
          <p className="text-sm">Make sure the simulation is running and drones are publishing telemetry</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {availableDrones.map((drone) => {
            const isConnected = connectedDroneIds.has(drone.drone_id);

            return (
              <div
                key={drone.drone_id}
                className={`border-2 rounded-lg p-4 transition-all ${
                  isConnected
                    ? 'border-green-500 bg-green-50'
                    : 'border-gray-300 bg-white'
                }`}
              >
                {/* Drone Header */}
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="font-bold text-lg">{drone.drone_id}</h3>
                    {drone.name && (
                      <p className="text-sm text-gray-600">{drone.name}</p>
                    )}
                  </div>
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-semibold ${
                      isConnected
                        ? 'bg-green-600 text-white'
                        : 'bg-gray-300 text-gray-700'
                    }`}
                  >
                    {isConnected ? '● Connected' : '○ Disconnected'}
                  </span>
                </div>

                {/* Drone Info */}
                <div className="space-y-2 mb-4 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Model:</span>
                    <span className="font-medium">{drone.model}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Status:</span>
                    <span className={`font-medium ${
                      drone.status === 'active' ? 'text-green-600' :
                      drone.status === 'idle' ? 'text-blue-600' :
                      'text-gray-600'
                    }`}>
                      {drone.status}
                    </span>
                  </div>
                  {drone.battery_level !== null && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Battery:</span>
                      <span className={`font-medium ${
                        drone.battery_level > 50 ? 'text-green-600' :
                        drone.battery_level > 20 ? 'text-yellow-600' :
                        'text-red-600'
                      }`}>
                        {drone.battery_level.toFixed(0)}%
                      </span>
                    </div>
                  )}
                  {drone.is_armed !== null && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Armed:</span>
                      <span className={`font-medium ${drone.is_armed ? 'text-red-600' : 'text-gray-600'}`}>
                        {drone.is_armed ? 'Yes' : 'No'}
                      </span>
                    </div>
                  )}
                  {drone.flight_mode && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Mode:</span>
                      <span className="font-medium">{drone.flight_mode}</span>
                    </div>
                  )}
                </div>

                {/* Connect/Disconnect Button */}
                <button
                  onClick={() => handleToggleConnection(drone.drone_id)}
                  className={`w-full px-4 py-2 rounded-lg font-semibold transition-all ${
                    isConnected
                      ? 'bg-red-600 hover:bg-red-700 text-white'
                      : 'bg-green-600 hover:bg-green-700 text-white'
                  }`}
                >
                  {isConnected ? 'Disconnect' : 'Connect'}
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Connection Summary */}
      {availableDrones.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <p className="text-sm text-gray-600">
            Connected: <span className="font-semibold text-green-600">{connectedDroneIds.size}</span>
            {' / '}
            Total: <span className="font-semibold">{availableDrones.length}</span>
          </p>
        </div>
      )}
    </div>
  );
}
