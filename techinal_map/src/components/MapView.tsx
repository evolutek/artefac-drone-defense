import React, { useEffect } from 'react';
import { MapContainer, TileLayer, useMapEvents, CircleMarker, Polyline, LayersControl } from 'react-leaflet';
import type { LeafletMouseEvent } from 'leaflet';
import { useDroneStore } from '../state/store';
import { startWebSocket } from '../ws';
import DroneMarker from './DroneMarker';
import TrajectoryLayer from './TrajectoryLayer';
import ZonesLayer from './ZonesLayer';
import * as mgrs from 'mgrs';

function ClickCapture({ onClick }: { onClick: (lat: number, lon: number) => void }) {
  useMapEvents({
    click(e: LeafletMouseEvent) {
      onClick(e.latlng.lat, e.latlng.lng);
    }
  });
  return null;
}

export default function MapView({ setWaypointFromMap }: { setWaypointFromMap: (lat: number, lon: number) => void }) {
  const drones = useDroneStore((s) => s.drones);
  const trajectories = useDroneStore((s) => s.trajectories);
  const zones = useDroneStore((s) => s.zones);
  const draftTarget = useDroneStore((s) => s.draftTarget);
  const selectedDroneId = useDroneStore((s) => s.selectedDroneId);
  // Entrepôts masqués: ne pas stocker ni afficher (sécurité)

  useEffect(() => {
    startWebSocket();
  }, []);

  // Ne pas charger les entrepôts

  return (
    <MapContainer center={[48.8566, 2.3522]} zoom={12} style={{ height: 'calc(100vh - 48px)', width: '100%' }}>
      <LayersControl position="topright">
        <LayersControl.BaseLayer checked name="Topo (OpenTopoMap)">
          <TileLayer
            attribution='&copy; OpenTopoMap contributors'
            url='https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png'
            maxZoom={17}
          />
        </LayersControl.BaseLayer>
        <LayersControl.BaseLayer name="Satellite (Esri)">
          <TileLayer
            attribution='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
            url='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
            maxZoom={19}
          />
        </LayersControl.BaseLayer>
      </LayersControl>
      <ZonesLayer zones={zones} />
      {/* Entrepôts masqués */}
      {Object.values(drones).map((t) => (
        <React.Fragment key={t.drone_id}>
          <DroneMarker t={t} />
          <TrajectoryLayer points={trajectories[t.drone_id] ?? []} />
        </React.Fragment>
      ))}
      {draftTarget && (
        <>
          <CircleMarker center={draftTarget} radius={8} pathOptions={{ color: '#e53935' }} />
          {selectedDroneId && drones[selectedDroneId] && (
            <Polyline
              positions={[
                [drones[selectedDroneId].lat, drones[selectedDroneId].lon],
                draftTarget
              ]}
              pathOptions={{ color: '#e53935', dashArray: '6, 8' }}
            />
          )}
          <div style={{ position: 'absolute', left: 12, bottom: 12, background: 'rgba(0,0,0,0.6)', color: '#fff', padding: '8px 10px', borderRadius: 8, fontSize: 13 }}>
            <div><strong>Coordonnées</strong></div>
            <div>Lat/Lon: {draftTarget[0].toFixed(6)}, {draftTarget[1].toFixed(6)}</div>
            <div>MGRS: {mgrs.forward([draftTarget[1], draftTarget[0]])}</div>
          </div>
        </>
      )}
      <ClickCapture onClick={(lat, lon) => setWaypointFromMap(lat, lon)} />
    </MapContainer>
  );
}
