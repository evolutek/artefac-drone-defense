import { useEffect, useState } from 'react';
import { healthApi } from '../utils/api';
import { HealthStatus } from '../types';

export function HealthDashboard() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const response = await healthApi.getStatus();
        setHealth(response.data);
        setError(null);
      } catch (err) {
        setError('Failed to fetch health status');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    // Initial fetch
    fetchHealth();

    // Poll every 5 seconds
    const interval = setInterval(fetchHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-bold mb-4">System Health</h2>
        <p className="text-gray-600">Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-bold mb-4">System Health</h2>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      </div>
    );
  }

  const StatusBadge = ({ status }: { status: boolean | string }) => {
    const isHealthy = status === true || status === 'healthy' || status === 'operational';
    return (
      <span
        className={`px-3 py-1 rounded-full text-sm font-semibold ${
          isHealthy
            ? 'bg-green-100 text-green-800'
            : 'bg-red-100 text-red-800'
        }`}
      >
        {isHealthy ? '✓ Online' : '✗ Offline'}
      </span>
    );
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold mb-6">System Health</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="flex justify-between items-center p-4 bg-gray-50 rounded-lg">
          <span className="font-semibold">Backend</span>
          <StatusBadge status={health?.status || 'unknown'} />
        </div>

        <div className="flex justify-between items-center p-4 bg-gray-50 rounded-lg">
          <span className="font-semibold">MQTT Broker</span>
          <StatusBadge status={health?.mqtt_connected || false} />
        </div>

        <div className="flex justify-between items-center p-4 bg-gray-50 rounded-lg">
          <span className="font-semibold">Database</span>
          <StatusBadge status={health?.database || 'unknown'} />
        </div>

        <div className="flex justify-between items-center p-4 bg-gray-50 rounded-lg">
          <span className="font-semibold">Active Drones</span>
          <span className="px-3 py-1 rounded-full text-sm font-semibold bg-blue-100 text-blue-800">
            {health?.drones_connected || 0}
          </span>
        </div>
      </div>

      <div className="mt-4 text-sm text-gray-500">
        Last updated: {health?.timestamp ? new Date(health.timestamp).toLocaleTimeString() : 'N/A'}
      </div>
    </div>
  );
}
