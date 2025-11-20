import { useState, useRef, useEffect, useCallback } from 'react';
import { WebSocketMessage, DroneLifecycleEvent } from '../types';

export interface InitializingDrone {
  drone_id: string;
  status: 'initializing';
  reason?: string;
  timestamp: number;
}

export function useGlobalDroneEvents() {
  const [initializingDrones, setInitializingDrones] = useState<Map<string, InitializingDrone>>(new Map());
  const [latestEvent, setLatestEvent] = useState<DroneLifecycleEvent | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    // Don't reconnect if already connected
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('[useGlobalDroneEvents] Already connected, skipping');
      return;
    }

    const wsUrl = `ws://${window.location.hostname}:8000/ws/telemetry`;
    console.log('[useGlobalDroneEvents] Connecting to:', wsUrl);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[useGlobalDroneEvents] ✅ WebSocket connected successfully');
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage;
        console.log('[useGlobalDroneEvents] Received message:', message);

        // Only handle lifecycle events
        if (message.type === 'drone_spawning' ||
            message.type === 'drone_ready' ||
            message.type === 'drone_removed') {

          const lifecycleEvent = message as DroneLifecycleEvent;
          console.log('[useGlobalDroneEvents] 🎯 Lifecycle event:', lifecycleEvent.type, lifecycleEvent.drone_id);
          setLatestEvent(lifecycleEvent);

          if (lifecycleEvent.type === 'drone_spawning') {
            // Add drone to initializing list
            console.log('[useGlobalDroneEvents] Adding drone to initializing list:', lifecycleEvent.drone_id);
            setInitializingDrones(prev => {
              const newMap = new Map(prev);
              newMap.set(lifecycleEvent.drone_id, {
                drone_id: lifecycleEvent.drone_id,
                status: 'initializing',
                reason: lifecycleEvent.data.reason,
                timestamp: Date.now(),
              });
              console.log('[useGlobalDroneEvents] Initializing drones count:', newMap.size);
              return newMap;
            });
          } else if (lifecycleEvent.type === 'drone_ready') {
            // Remove from initializing list
            console.log('[useGlobalDroneEvents] Drone ready, removing from initializing list:', lifecycleEvent.drone_id);
            setInitializingDrones(prev => {
              const newMap = new Map(prev);
              newMap.delete(lifecycleEvent.drone_id);
              console.log('[useGlobalDroneEvents] Initializing drones count:', newMap.size);
              return newMap;
            });
          } else if (lifecycleEvent.type === 'drone_removed') {
            // Remove from initializing list (in case it was still initializing)
            console.log('[useGlobalDroneEvents] Drone removed:', lifecycleEvent.drone_id);
            setInitializingDrones(prev => {
              const newMap = new Map(prev);
              newMap.delete(lifecycleEvent.drone_id);
              console.log('[useGlobalDroneEvents] Initializing drones count:', newMap.size);
              return newMap;
            });
          }
        }
      } catch (error) {
        console.error('Failed to parse global WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('[useGlobalDroneEvents] ❌ WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('[useGlobalDroneEvents] WebSocket disconnected, reconnecting in 3s...');
      wsRef.current = null;

      // Auto-reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log('[useGlobalDroneEvents] Attempting reconnection...');
        connect();
      }, 3000);
    };
  }, []);

  useEffect(() => {
    console.log('[useGlobalDroneEvents] 🚀 Hook initialized, connecting...');
    // Connect on mount
    connect();

    // Cleanup on unmount
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    initializingDrones,
    latestEvent,
  };
}
