import React from 'react';

const ZONES = Array.from({ length: 60 }, (_, i) => String(i + 1));
const BANDS = 'CDEFGHJKLMNPQRSTUVWX'.split('');

type MGRSCoordinateInputProps = {
  zone: string;
  band: string;
  grid: string;
  easting: string;
  northing: string;
  onZoneChange: (zone: string) => void;
  onBandChange: (band: string) => void;
  onGridChange: (grid: string) => void;
  onEastingChange: (easting: string) => void;
  onNorthingChange: (northing: string) => void;
};

export default function MGRSCoordinateInput({
  zone,
  band,
  grid,
  easting,
  northing,
  onZoneChange,
  onBandChange,
  onGridChange,
  onEastingChange,
  onNorthingChange,
}: MGRSCoordinateInputProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ fontWeight: 600 }}>Coordonnées — format MGRS</div>
      <div style={{ display: 'grid', gridTemplateColumns: '150px 150px 100px 1fr 1fr', gap: 8 }}>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          Zone
          <select
            className="input input-sm"
            aria-label="Zone (menu)"
            value={zone}
            onChange={(e) => onZoneChange(e.target.value)}
          >
            <option value="" disabled>
              Choisir
            </option>
            {ZONES.map((z) => (
              <option key={z} value={z}>
                {z}
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          Bande
          <select
            className="input input-sm"
            aria-label="Bande (menu)"
            value={band}
            onChange={(e) => onBandChange(e.target.value)}
          >
            <option value="" disabled>
              Choisir
            </option>
            {BANDS.map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          Grille
          <input
            type="text"
            placeholder="YT"
            value={grid}
            onChange={(e) =>
              onGridChange(e.target.value.replace(/[^A-Za-z]/g, '').toUpperCase().slice(0, 2))
            }
            className="input input-sm"
          />
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          Est (m)
          <input
            type="text"
            inputMode="numeric"
            placeholder="26398"
            value={easting}
            onChange={(e) => onEastingChange(e.target.value.replace(/[^0-9]/g, '').slice(0, 5))}
            className="input input-sm"
          />
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          Nord (m)
          <input
            type="text"
            inputMode="numeric"
            placeholder="28974"
            value={northing}
            onChange={(e) => onNorthingChange(e.target.value.replace(/[^0-9]/g, '').slice(0, 5))}
            className="input input-sm"
          />
        </label>
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
        <code>30T YT 26398 28974</code>
      </div>
    </div>
  );
}
