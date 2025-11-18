import { useState } from 'react';
import { droneApi } from '../utils/api';
import { TelemetryData } from '../types';
import axios from 'axios';

interface DroneControlProps {
  droneId: string;
  telemetry: TelemetryData | null;
  isConnected: boolean;
}

export function DroneControl({ droneId, telemetry }: DroneControlProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [altitude, setAltitude] = useState(5.0);

  // Get current armed state from telemetry
  const isArmed = telemetry?.type === 'state' ? telemetry.data.armed ?? false : false;

  const handleCommand = async (command: string, action: () => Promise<any>) => {
    setLoading(command);
    setMessage(null);

    try {
      const response = await action();
      const successMsg = response.data?.message || `${command} command sent successfully`;
      setMessage({ type: 'success', text: successMsg });
    } catch (error) {
      let errorMsg = `Failed to send ${command} command`;

      if (axios.isAxiosError(error)) {
        // Extract error message from backend response
        errorMsg = error.response?.data?.detail || errorMsg;
      }

      setMessage({ type: 'error', text: errorMsg });
      console.error(`${command} error:`, error);
    } finally {
      setLoading(null);
      // Clear message after 5 seconds
      setTimeout(() => setMessage(null), 5000);
    }
  };

  const CommandButton = ({
    label,
    onClick,
    color,
    disabled = false,
  }: {
    label: string;
    onClick: () => void;
    color: string;
    disabled?: boolean;
  }) => {
    const isLoading = loading === label;
    const baseClasses = 'px-6 py-3 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed';
    const colorClasses = {
      green: 'bg-green-600 hover:bg-green-700 text-white',
      red: 'bg-red-600 hover:bg-red-700 text-white',
      blue: 'bg-blue-600 hover:bg-blue-700 text-white',
      gray: 'bg-gray-600 hover:bg-gray-700 text-white',
    }[color];

    return (
      <button
        onClick={onClick}
        disabled={disabled || loading !== null}
        className={`${baseClasses} ${colorClasses}`}
      >
        {isLoading ? 'Sending...' : label}
      </button>
    );
  };

  const handleArmToggle = async () => {
    if (isArmed) {
      await handleCommand('DISARM', () => droneApi.disarm(droneId));
    } else {
      await handleCommand('ARM', () => droneApi.arm(droneId));
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold mb-6">Drone Control - {droneId}</h2>

      {message && (
        <div
          className={`mb-4 p-4 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-100 text-green-800 border border-green-400'
              : 'bg-red-100 text-red-800 border border-red-400'
          }`}
        >
          {message.text}
        </div>
      )}

      <div className="space-y-4">
        {/* Arming Switch */}
        <div>
          <h3 className="text-lg font-semibold mb-3">Arming</h3>
          <div className="flex items-center gap-4">
            <button
              onClick={handleArmToggle}
              disabled={loading !== null}
              className={`relative inline-flex h-8 w-16 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${
                isArmed
                  ? 'bg-green-600 focus:ring-green-500'
                  : 'bg-gray-300 focus:ring-gray-400'
              }`}
            >
              <span
                className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${
                  isArmed ? 'translate-x-9' : 'translate-x-1'
                }`}
              />
            </button>
            <span className={`font-semibold ${isArmed ? 'text-green-600' : 'text-gray-600'}`}>
              {loading === 'ARM' || loading === 'DISARM'
                ? 'Processing...'
                : isArmed
                  ? 'ARMED'
                  : 'DISARMED'}
            </span>
          </div>
        </div>

        {/* Flight Controls */}
        <div>
          <h3 className="text-lg font-semibold mb-3">Flight</h3>

          {/* Altitude Input */}
          <div className="mb-3">
            <label className="block text-sm font-medium mb-2">
              Takeoff Altitude (meters)
            </label>
            <input
              type="number"
              min="1"
              max="50"
              step="0.5"
              value={altitude}
              onChange={(e) => setAltitude(parseFloat(e.target.value))}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={loading !== null}
            />
          </div>

          <div className="flex gap-3">
            <CommandButton
              label="TAKEOFF"
              onClick={() => handleCommand('TAKEOFF', () => droneApi.takeoff(droneId, altitude))}
              color="blue"
            />
            <CommandButton
              label="LAND"
              onClick={() => handleCommand('LAND', () => droneApi.land(droneId))}
              color="gray"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
