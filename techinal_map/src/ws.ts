import type { WSMessage, TelemetryMessage } from './types/types';
import { useDroneStore } from './state/store';

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000/ws/telemetry';

let socket: WebSocket | null = null;
let reconnectTimer: number | null = null;
const stateCallbacks: Array<(msg: WSMessage) => void> = [];

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
      // Debug: trace incoming state events
      if (msg.type === 'state') {
        console.debug('[WS] state event', msg);
      }
      if (msg.type === 'telemetry') {
        const t = (msg as TelemetryMessage).data;
        useDroneStore.getState().upsertTelemetry(t);
      } else if (msg.type === 'state') {
        for (const cb of stateCallbacks) {
          try { cb(msg); } catch {}
        }
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

export function onStateEvent(cb: (msg: WSMessage) => void) {
  stateCallbacks.push(cb);
}

export function offStateEvent(cb: (msg: WSMessage) => void) {
  const i = stateCallbacks.indexOf(cb);
  if (i >= 0) stateCallbacks.splice(i, 1);
}
