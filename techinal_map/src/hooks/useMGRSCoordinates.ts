import { useEffect, useMemo, useState } from 'react';
import * as mgrs from 'mgrs';

export type MGRSCoordinates = {
  zone: string;
  band: string;
  grid: string;
  easting: string;
  northing: string;
};

export function useMGRSCoordinates(
  initialLat?: number,
  initialLon?: number,
  onCoordinatesChange?: (lat: number, lon: number) => void
) {
  const [mgrsZone, setMgrsZone] = useState<string>('');
  const [mgrsBand, setMgrsBand] = useState<string>('');
  const [mgrsGrid, setMgrsGrid] = useState<string>('');
  const [mgrsEasting, setMgrsEasting] = useState<string>('');
  const [mgrsNorthing, setMgrsNorthing] = useState<string>('');
  const [targetMgrs, setTargetMgrs] = useState<string>('');

  const mgrsCombined = useMemo(() => {
    const z = mgrsZone.trim();
    const b = mgrsBand.trim().toUpperCase();
    const g = mgrsGrid.trim().toUpperCase();
    const e = mgrsEasting.trim();
    const n = mgrsNorthing.trim();
    return [z, b, g, e, n].every(Boolean) ? `${z}${b} ${g} ${e} ${n}` : '';
  }, [mgrsZone, mgrsBand, mgrsGrid, mgrsEasting, mgrsNorthing]);

  // Update MGRS fields when initial coordinates change
  useEffect(() => {
    if (initialLat != null && initialLon != null) {
      const code = mgrs.forward([initialLon, initialLat]);
      setTargetMgrs(code);
      const match = code.match(/^(\d{1,2})([A-HJ-NP-Z])\s*([A-HJ-NP-Z]{2})\s*(\d{1,5})\s*(\d{1,5})$/i);
      if (match) {
        setMgrsZone(match[1]);
        setMgrsBand(match[2].toUpperCase());
        setMgrsGrid(match[3].toUpperCase());
        setMgrsEasting(match[4]);
        setMgrsNorthing(match[5]);
      }
    }
  }, [initialLat, initialLon]);

  // Convert MGRS to lat/lon when fields change
  useEffect(() => {
    if (mgrsCombined) {
      try {
        const p = mgrs.toPoint(mgrsCombined);
        if (Array.isArray(p) && p.length === 2) {
          const lon = p[0];
          const lat = p[1];
          setTargetMgrs(mgrsCombined);
          onCoordinatesChange?.(lat, lon);
        }
      } catch (err) {
        // Invalid MGRS, ignore
      }
    }
  }, [mgrsCombined, onCoordinatesChange]);

  return {
    mgrsZone,
    mgrsBand,
    mgrsGrid,
    mgrsEasting,
    mgrsNorthing,
    targetMgrs,
    setMgrsZone,
    setMgrsBand,
    setMgrsGrid,
    setMgrsEasting,
    setMgrsNorthing,
    mgrsCombined,
  };
}
