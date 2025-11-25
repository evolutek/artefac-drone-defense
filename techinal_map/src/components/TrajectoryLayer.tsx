import React from 'react';
import { Polyline } from 'react-leaflet';

export default function TrajectoryLayer({ points }: { points: Array<[number, number]> }) {
  if (!points || points.length < 2) return null;
  return <Polyline positions={points} color="#2196f3" weight={2} opacity={0.8} />;
}