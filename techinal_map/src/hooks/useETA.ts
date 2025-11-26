import { useEffect, useState } from 'react';
import type { DroneTelemetry } from '../types';

export function useETA(
  droneTelemetry?: DroneTelemetry,
  targetLat?: number,
  targetLon?: number,
  speed: number = 12
) {
  const [eta, setEta] = useState<string>('');
  const [distanceMeters, setDistanceMeters] = useState<number>(0);

  useEffect(() => {
    if (droneTelemetry && targetLat != null && targetLon != null && speed > 0) {
      const R = 6371000; // meters
      const toRad = (v: number) => (v * Math.PI) / 180;
      const dLat = toRad(targetLat - droneTelemetry.lat);
      const dLon = toRad(targetLon - droneTelemetry.lon);
      const a =
        Math.sin(dLat / 2) ** 2 +
        Math.cos(toRad(droneTelemetry.lat)) *
          Math.cos(toRad(targetLat)) *
          Math.sin(dLon / 2) ** 2;
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
      const dist = R * c; // meters
      setDistanceMeters(dist);

      const sec = Math.max(1, Math.round(dist / speed));
      const minutes = Math.floor(sec / 60);
      const seconds = sec % 60;
      setEta(`${minutes} min ${seconds}s`);
    } else {
      setEta('');
      setDistanceMeters(0);
    }
  }, [droneTelemetry, targetLat, targetLon, speed]);

  return { eta, distanceMeters };
}
