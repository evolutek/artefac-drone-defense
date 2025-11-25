import React, { useMemo } from 'react';
import { Marker, Tooltip } from 'react-leaflet';
import L from 'leaflet';
import type { DroneTelemetry } from '../types';

const statusColor = (s?: DroneTelemetry['status']) => {
  switch (s) {
    case 'armed': return '#ffc107';
    case 'mission': return '#2196f3';
    case 'returning': return '#9c27b0';
    case 'error': return '#f44336';
    case 'idle':
    default: return '#4caf50';
  }
};

function makeIcon(color: string) {
  const svg = encodeURIComponent(
    `<svg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 32 32'>
      <g>
        <circle cx='16' cy='16' r='9' fill='${color}' stroke='white' stroke-width='2'/>
        <path d='M16 3 L18 10 L16 8 L14 10 Z' fill='${color}' stroke='white' stroke-width='1'/>
      </g>
    </svg>`
  );
  return L.icon({
    iconUrl: `data:image/svg+xml;charset=UTF-8,${svg}`,
    iconSize: [24, 24],
    iconAnchor: [12, 12]
  });
}

export default function DroneMarker({ t }: { t: DroneTelemetry }) {
  const icon = useMemo(() => makeIcon(statusColor(t.status)), [t.status]);
  return (
    <Marker position={[t.lat, t.lon]} icon={icon}>
      <Tooltip direction="top" offset={[0, -8]}>
        <div style={{ fontSize: 12 }}>
          <div><strong>Drone:</strong> {t.drone_id}</div>
          {t.altitude !== undefined && (<div>Alt: {Math.round(t.altitude)} m</div>)}
          {t.speed !== undefined && (<div>Vitesse: {Math.round(t.speed)} m/s</div>)}
          {t.battery_level !== undefined && (<div>Battery: {Math.round(t.battery_level)}%</div>)}
          {t.status && (<div>Statut: {t.status}</div>)}
          <div>{new Date(t.timestamp).toLocaleTimeString()}</div>
        </div>
      </Tooltip>
    </Marker>
  );
}