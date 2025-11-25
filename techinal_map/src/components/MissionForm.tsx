import React, { useEffect, useMemo, useState } from 'react';
import { useDroneStore, type DroneState } from '../state/store';
import type { MissionCreate, Payload } from '../types';
import ProductCatalog from './ProductCatalog';
import SearchInput from './SearchInput';
import { PRODUCTS, type Product } from '../data/products';
import * as mgrs from 'mgrs';

// Listes pour menus déroulants MGRS
const ZONES = Array.from({ length: 60 }, (_, i) => String(i + 1));
const BANDS = 'CDEFGHJKLMNPQRSTUVWX'.split(''); // sans I et O

export default function MissionForm({
  initialLat,
  initialLon,
  initialPayload
}: {
  initialLat?: number;
  initialLon?: number;
  initialPayload?: Payload;
}) {
  const submitMission = useDroneStore((s: DroneState) => s.submitMission);
  const setDraftTarget = useDroneStore((s: DroneState) => s.setDraftTarget);
  const setSelectedDroneIdStore = useDroneStore((s: DroneState) => s.setSelectedDroneId);
  const dronesMap = useDroneStore((s: DroneState) => s.drones);
  const [droneId, setDroneId] = useState<string>('');
  const [missionType] = useState('delivery');
  const [priority, setPriority] = useState(3);
  const [waypoints, setWaypoints] = useState<Array<{ lat: number; lon: number; altitude?: number }>>(
    initialLat && initialLon ? [{ lat: initialLat, lon: initialLon, altitude: 120 }] : []
  );
  const [targetMgrs, setTargetMgrs] = useState<string>(() =>
    initialLat != null && initialLon != null ? mgrs.forward([initialLon, initialLat]) : ''
  );
  const [status, setStatus] = useState<string>('');
  const [drones, setDrones] = useState<Array<{ drone_id: string; name?: string }>>([]);
  const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
  const [speed] = useState<number>(12); // m/s (input removed, keep for ETA)
  const target = waypoints[0];
  const selectedDroneTelemetry = droneId ? dronesMap[droneId] : undefined;
  const [eta, setEta] = useState<string>('');
  const [distanceMeters, setDistanceMeters] = useState<number>(0);
  const [payload, setPayload] = useState<Payload>(
    initialPayload ?? { item_name: '', weight_kg: 1, quantity: 1 }
  );
  const [showProducts, setShowProducts] = useState<boolean>(true);
  const [productSearch, setProductSearch] = useState<string>('');
  const [selectedProducts, setSelectedProducts] = useState<Array<{ product: Product; quantity: number }>>([]);
  // MGRS segmented fields
  const [mgrsZone, setMgrsZone] = useState<string>(''); // ex: 30
  const [mgrsBand, setMgrsBand] = useState<string>(''); // ex: T
  const [mgrsGrid, setMgrsGrid] = useState<string>(''); // ex: YT
  const [mgrsEasting, setMgrsEasting] = useState<string>(''); // ex: 26398
  const [mgrsNorthing, setMgrsNorthing] = useState<string>(''); // ex: 28974
  const mgrsCombined = useMemo(() => {
    const z = mgrsZone.trim();
    const b = mgrsBand.trim().toUpperCase();
    const g = mgrsGrid.trim().toUpperCase();
    const e = mgrsEasting.trim();
    const n = mgrsNorthing.trim();
    return [z, b, g, e, n].every(Boolean) ? `${z}${b} ${g} ${e} ${n}` : '';
  }, [mgrsZone, mgrsBand, mgrsGrid, mgrsEasting, mgrsNorthing]);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_URL}/drones`);
        const list = await res.json();
        setDrones(list || []);
        if (list && list.length > 0) setDroneId(list[0].drone_id);
      } catch {}
    })();
  }, [API_URL]);

  // Mettre à jour le champ MGRS segmenté si les props initiales changent (clic carte / replay)
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
      setWaypoints([{ lat: initialLat, lon: initialLon, altitude: 120 }]);
    }
  }, [initialLat, initialLon]);

  useEffect(() => {
    if (initialPayload && initialPayload.item_name) {
      const match = PRODUCTS.find((p) => p.name === initialPayload.item_name);
      if (match) {
        setSelectedProducts((list) => (list.some((x) => x.product.id === match.id) ? list : [...list, { product: match, quantity: initialPayload.quantity || 1 }]));
      }
    }
  }, [initialPayload]);

  useEffect(() => {
    if (selectedProducts.length > 0) {
      const totalQuantity = selectedProducts.reduce((sum, e) => sum + e.quantity, 0);
      const totalWeight = selectedProducts.reduce((sum, e) => sum + (e.product.weight_kg ?? 1) * e.quantity, 0);
      const names = selectedProducts.map((e) => e.product.name);
      const combinedName = names.length <= 2 ? names.join(' + ') : `${names.slice(0, 2).join(' + ')} + ${names.length - 2} autres`;
      setPayload({ item_name: combinedName, weight_kg: totalWeight, quantity: totalQuantity });
    } else {
      setPayload({ item_name: '', weight_kg: 1, quantity: 1 });
    }
  }, [selectedProducts]);


  // Chaque modification des champs MGRS tente de convertir en lat/lon
  useEffect(() => {
    if (mgrsCombined) {
      try {
        const p = mgrs.toPoint(mgrsCombined);
        if (Array.isArray(p) && p.length === 2) {
          const lon = p[0];
          const lat = p[1];
          setTargetMgrs(mgrsCombined);
          setWaypoints([{ lat, lon, altitude: 120 }]);
          setDraftTarget([lat, lon]);
          setStatus('');
        }
      } catch (err) {
        // Ne rien faire tant que les entrées ne sont pas complètes/valides
      }
    }
  }, [mgrsCombined]);

  function addWaypoint(lat = initialLat ?? 48.8566, lon = initialLon ?? 2.3522) {
    setWaypoints((w) => [...w, { lat, lon, altitude: 120 }]);
  }

  // Met à jour ETA à chaque changement
  useEffect(() => {
    if (selectedDroneTelemetry && target?.lat != null && target?.lon != null && speed > 0) {
      const R = 6371000; // m
      const toRad = (v: number) => (v * Math.PI) / 180;
      const dLat = toRad(target.lat - selectedDroneTelemetry.lat);
      const dLon = toRad(target.lon - selectedDroneTelemetry.lon);
      const a = Math.sin(dLat / 2) ** 2 +
        Math.cos(toRad(selectedDroneTelemetry.lat)) * Math.cos(toRad(target.lat)) * Math.sin(dLon / 2) ** 2;
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
  }, [selectedDroneTelemetry, target?.lat, target?.lon, speed]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!payload.item_name || payload.weight_kg <= 0 || payload.quantity <= 0) {
      setStatus('Erreur: charge invalide (nom, poids > 0, quantité > 0)');
      return;
    }
    const mission: MissionCreate = {
      drone_id: droneId,
      mission_type: missionType,
      waypoints,
      priority
    };
    const payloads = selectedProducts.map((e) => ({ item_name: e.product.name, weight_kg: e.product.weight_kg ?? 1, quantity: e.quantity }));
    try {
      await submitMission(mission, {
        item_name: payload.item_name,
        weight_kg: payload.weight_kg,
        quantity: payload.quantity
      }, payloads);
      setStatus('Mission envoyée');
      setDraftTarget(null);
    } catch (err: any) {
      setStatus(`Erreur: ${err.message}`);
    }
  }

  async function registerTestDrone() {
    try {
      const payload = { drone_id: 'drone-1', name: 'Test Drone', model: 'sim' };
      const res = await fetch(`${API_URL}/drones`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(`Register failed: ${res.status}`);
      const created = await res.json();
      setDrones((d) => [...d, created]);
      setDroneId(created.drone_id);
      setStatus('Drone de test enregistré');
    } catch (err: any) {
      setStatus(`Erreur enregistrement: ${err.message}`);
    }
  }

  return (
    <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <label style={{ marginBottom: 8 }}>
        Priorité
        <select
          className="input input-sm"
          value={priority}
          onChange={(e) => setPriority(parseInt(e.target.value))}
          style={{ marginLeft: 8 }}
          aria-label="Priorité (menu)"
        >
          <option value={1}>1</option>
          <option value={2}>2</option>
          <option value={3}>3</option>
          <option value={4}>4</option>
          <option value={5}>5</option>
        </select>
      </label>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ fontWeight: 600 }}>Coordonnées — format MGRS</div>
        <div style={{ display: 'grid', gridTemplateColumns: '150px 150px 100px 1fr 1fr', gap: 8 }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            Zone
            <select className="input input-sm" aria-label="Zone (menu)" value={mgrsZone} onChange={(e) => setMgrsZone(e.target.value)}>
              <option value="" disabled>Choisir</option>
              {ZONES.map((z) => (<option key={z} value={z}>{z}</option>))}
            </select>
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            Bande
            <select className="input input-sm" aria-label="Bande (menu)" value={mgrsBand} onChange={(e) => setMgrsBand(e.target.value)}>
              <option value="" disabled>Choisir</option>
              {BANDS.map((b) => (<option key={b} value={b}>{b}</option>))}
            </select>
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            Grille
            <input
              type="text"
              placeholder="YT"
              value={mgrsGrid}
              onChange={(e) => setMgrsGrid(e.target.value.replace(/[^A-Za-z]/g, '').toUpperCase().slice(0, 2))}
              className="input input-sm"
            />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            Est (m)
            <input
              type="text"
              inputMode="numeric"
              placeholder="26398"
              value={mgrsEasting}
              onChange={(e) => setMgrsEasting(e.target.value.replace(/[^0-9]/g, '').slice(0, 5))}
              className="input input-sm"
            />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            Nord (m)
            <input
              type="text"
              inputMode="numeric"
              placeholder="28974"
              value={mgrsNorthing}
              onChange={(e) => setMgrsNorthing(e.target.value.replace(/[^0-9]/g, '').slice(0, 5))}
              className="input input-sm"
            />
          </label>
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
        Exemple: <code>30T YT 26398 28974</code>
      </div>
      {selectedProducts.length > 0 && (
        <div style={{ marginTop: 12, border: '1px solid var(--border)', borderRadius: 8, padding: 8 }}>
          {selectedProducts.map((entry) => (
            <div key={entry.product.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0' }}>
              <span style={{ fontWeight: 600, fontSize: 13 }}>{entry.product.name}</span>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{entry.product.weight_kg ?? '-'} kg</span>
              <label style={{ marginLeft: 'auto' }}>
                Quantité
                <input
                  className="input input-sm"
                  type="number"
                  min={1}
                  step={1}
                  value={entry.quantity}
                  onChange={(e) => {
                    const q = Math.max(1, parseInt(e.target.value) || 1);
                    setSelectedProducts((list) => list.map((it) => it.product.id === entry.product.id ? { ...it, quantity: q } : it));
                  }}
                  style={{ marginLeft: 8, width: 80 }}
                />
              </label>
              <button
                type="button"
                className="btn btn-sm"
                onClick={() => setSelectedProducts((list) => list.filter((x) => x.product.id !== entry.product.id))}
              >Retirer</button>
            </div>
          ))}
        </div>
      )}
      </div>
      {/* Vitesse supprimée de l'UI, conservée en interne pour ETA */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <button type="button" className="btn btn-sm" onClick={() => setShowProducts((v) => !v)}>
          {showProducts ? 'Masquer catalogue' : 'Afficher catalogue'}
        </button>
        <button type="submit" className="btn" style={{ marginLeft: 'auto' }}>Créer mission</button>
      </div>
      {showProducts && (
        <>
          <div style={{ display: 'block', margin: '8px 0 16px' }}>
            <SearchInput
              value={productSearch}
              onChange={setProductSearch}
              placeholder="Rechercher des produits"
              ariaLabel="Rechercher des produits"
              small
            />
          </div>
          <div style={{ border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden', marginTop: 24 }}>
            <ProductCatalog
              searchTerm={productSearch}
              onSelectProduct={(p: Product) => {
                setSelectedProducts((list) => (list.some((x) => x.product.id === p.id) ? list : [...list, { product: p, quantity: 1 }]));
              }}
            />
          </div>
        </>
      )}
      <div style={{ fontSize: 13, color: 'var(--text)' }}>
        {eta && (
          <>
            Distance: {Math.round(distanceMeters)} m — ETA: {eta}
          </>
        )}
      </div>
      
      <span style={{ color: status.startsWith('Erreur') ? '#f44336' : '#4caf50' }}>{status}</span>
    </form>
  );
}
