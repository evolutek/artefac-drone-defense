import React from 'react';
import { Circle, Tooltip } from 'react-leaflet';

type Zone = { id: string; name: string; center: [number, number]; radius: number; color?: string };

export default function ZonesLayer({ zones }: { zones: Zone[] }) {
  return (
    <>
      {zones.map((z) => (
        <Circle key={z.id} center={z.center} radius={z.radius} pathOptions={{ color: z.color ?? '#ff9800', fillOpacity: 0.1 }}>
          <Tooltip>{z.name}</Tooltip>
        </Circle>
      ))}
    </>
  );
}