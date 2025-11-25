import type { WSMessage, TelemetryMessage } from './types';
import { useDroneStore } from './state/store';

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000/ws/telemetry';

let socket: WebSocket | null = null;
let reconnectTimer: number | null = null;

export function startWebSocket() {
  if (socket) return;
  try {
    socket = new WebSocket(WS_URL);
  } catch (e) {
    scheduleReconnect();
    return;
  }

  socket.onopen = () => {
    // Keep-alive message every 30s (backend expects receive_text loop)
    setInterval(() => {
      try { socket?.send('ping'); } catch {}
    }, 30000);
    // send an initial ping to keep the server loop happy
    try { socket?.send('ping'); } catch {}
  };

  socket.onmessage = (event) => {
    try {
      const msg: WSMessage = JSON.parse(event.data);
      if (msg.type === 'telemetry') {
        const t = (msg as TelemetryMessage).data;
        useDroneStore.getState().upsertTelemetry(t);
      }
      // other message types can be handled here
    } catch (e) {
      // Some servers may send non-JSON keep-alives; ignore
    }
  };

  socket.onerror = () => {
    scheduleReconnect();
  };

  socket.onclose = () => {
    socket = null;
    scheduleReconnect();
  };

  function scheduleReconnect() {
    if (reconnectTimer) return;
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null;
      startWebSocket();
    }, 2000);
  }
}