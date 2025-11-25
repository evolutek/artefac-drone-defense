import { useEffect, useRef, useState } from 'react'

export type Telemetry = {
  drone_id: string
  latitude?: number
  longitude?: number
  altitude?: number
  position_x?: number
  position_y?: number
  position_z?: number
  timestamp?: number
}

export type DroneState = {
  latest?: Telemetry
  path: Array<{ lat: number; lon: number; alt: number }>
}

/**
 * Hook to subscribe to backend WebSocket telemetry for all drones.
 * Returns a map of drone_id -> latest telemetry and path history.
 */
export function useTelemetry() {
  const [drones, setDrones] = useState<Record<string, DroneState>>({})
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const wsUrl = (import.meta.env.VITE_BACKEND_WS_URL as string) || (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/ws'
    const url = wsUrl.replace(/\/$/, '') + '/telemetry'
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      // keep alive by sending pings
      const interval = setInterval(() => {
        try { ws.send('ping') } catch {}
      }, 15000)
      ;(wsRef as any).keepAlive = interval
    }

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        if (msg.type === 'telemetry') {
          const droneId: string = msg.drone_id
          const data = msg.data as Telemetry
          setDrones((prev) => {
            const current = prev[droneId] || { path: [] }
            const lat = data.latitude
            const lon = data.longitude
            const alt = data.altitude ?? data.position_z ?? 0
            const path = [...current.path]
            if (typeof lat === 'number' && typeof lon === 'number') {
              const last = path[path.length - 1]
              // Append if movement significant
              if (!last || Math.abs(last.lat - lat) > 1e-6 || Math.abs(last.lon - lon) > 1e-6 || Math.abs((last.alt ?? 0) - (alt ?? 0)) > 1e-3) {
                path.push({ lat, lon, alt })
                if (path.length > 5000) path.shift()
              }
            }
            return {
              ...prev,
              [droneId]: {
                latest: { ...data, drone_id: droneId },
                path,
              },
            }
          })
        }
      } catch (_) {
        // ignore parse errors
      }
    }

    ws.onclose = () => {
      const interval = (wsRef as any).keepAlive
      if (interval) clearInterval(interval)
      wsRef.current = null
    }

    return () => {
      try { ws.close() } catch {}
      const interval = (wsRef as any).keepAlive
      if (interval) clearInterval(interval)
    }
  }, [])

  return drones
}