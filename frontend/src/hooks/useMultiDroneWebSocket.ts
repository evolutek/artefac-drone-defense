import { useState, useRef, useCallback, useEffect } from 'react';
import { TelemetryData } from '../types';

interface DroneConnection {
  telemetry: TelemetryData | null;
  isConnected: boolean;
}

export function useMultiDroneWebSocket() {
  // Map of droneId -> connection data
  const [connections, setConnections] = useState<Map<string, DroneConnection>>(new Map());

  // Map of droneId -> WebSocket instance
  const wsRefs = useRef<Map<string, WebSocket>>(new Map());

  // Map of droneId -> reconnect timeout
  const reconnectTimeouts = useRef<Map<string, NodeJS.Timeout>>(new Map());

  const connect = useCallback((droneId: string) => {
    // Don't reconnect if already connected
    if (wsRefs.current.has(droneId)) {
      console.log(`Already connected to ${droneId}`);
      return;
    }

    const wsUrl = `ws://${window.location.hostname}:8000/ws/drone/${droneId}`;
    const ws = new WebSocket(wsUrl);
    wsRefs.current.set(droneId, ws);

    ws.onopen = () => {
      console.log(`WebSocket connected to ${droneId}`);
      setConnections(prev => {
        const newMap = new Map(prev);
        newMap.set(droneId, {
          telemetry: prev.get(droneId)?.telemetry || null,
          isConnected: true,
        });
        return newMap;
      });
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as TelemetryData;
        setConnections(prev => {
          const newMap = new Map(prev);
          const current = newMap.get(droneId);
          newMap.set(droneId, {
            telemetry: data,
            isConnected: current?.isConnected || false,
          });
          return newMap;
        });
      } catch (error) {
        console.error(`Failed to parse WebSocket message from ${droneId}:`, error);
      }
    };

    ws.onerror = (error) => {
      console.error(`WebSocket error for ${droneId}:`, error);
    };

    ws.onclose = () => {
      console.log(`WebSocket disconnected from ${droneId}`);
      setConnections(prev => {
        const newMap = new Map(prev);
        const current = newMap.get(droneId);
        if (current) {
          newMap.set(droneId, {
            ...current,
            isConnected: false,
          });
        }
        return newMap;
      });

      // Clean up refs
      wsRefs.current.delete(droneId);

      // Auto-reconnect after 3 seconds if still in connections map
      const timeoutId = setTimeout(() => {
        setConnections(prev => {
          // Only reconnect if the drone is still in the connections map
          if (prev.has(droneId)) {
            console.log(`Attempting to reconnect to ${droneId}...`);
            connect(droneId);
          }
          return prev;
        });
      }, 3000);

      reconnectTimeouts.current.set(droneId, timeoutId);
    };
  }, []);

  const disconnect = useCallback((droneId: string) => {
    // Clear reconnect timeout if any
    const timeoutId = reconnectTimeouts.current.get(droneId);
    if (timeoutId) {
      clearTimeout(timeoutId);
      reconnectTimeouts.current.delete(droneId);
    }

    // Close WebSocket connection
    const ws = wsRefs.current.get(droneId);
    if (ws) {
      ws.close();
      wsRefs.current.delete(droneId);
    }

    // Remove from connections map
    setConnections(prev => {
      const newMap = new Map(prev);
      newMap.delete(droneId);
      return newMap;
    });
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Clear all reconnect timeouts
      reconnectTimeouts.current.forEach(timeoutId => clearTimeout(timeoutId));
      reconnectTimeouts.current.clear();

      // Close all WebSocket connections
      wsRefs.current.forEach(ws => ws.close());
      wsRefs.current.clear();
    };
  }, []);

  return {
    connections,
    connect,
    disconnect,
  };
}
