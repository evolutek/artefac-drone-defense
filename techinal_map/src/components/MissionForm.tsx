import React, { useEffect, useState } from 'react';
import { useDroneStore, type DroneState } from '../state/store';
import type { MissionCreate, Payload } from '../types';
import ProductCatalog from './ProductCatalog';
import SearchInput from './SearchInput';
import MGRSCoordinateInput from './MGRSCoordinateInput';
import SelectedProductsList from './SelectedProductsList';
import { PRODUCTS, type Product } from '../data/products';
import { useMGRSCoordinates } from '../hooks/useMGRSCoordinates';
import { useETA } from '../hooks/useETA';

export default function MissionForm({
  initialLat,
  initialLon,
  initialPayload,
  initialPayloads,
  onSubmitted
}: {
  initialLat?: number;
  initialLon?: number;
  initialPayload?: Payload;
  initialPayloads?: Payload[];
  onSubmitted?: () => void;
}) {
  const submitMission = useDroneStore((s: DroneState) => s.submitMission);
  const setDraftTarget = useDroneStore((s: DroneState) => s.setDraftTarget);
  const dronesMap = useDroneStore((s: DroneState) => s.drones);
  const [droneId, setDroneId] = useState<string>('');
  const [missionType] = useState('delivery');
  const [priority, setPriority] = useState(3);
  const [waypoints, setWaypoints] = useState<Array<{ lat: number; lon: number; altitude?: number }>>(
    initialLat && initialLon ? [{ lat: initialLat, lon: initialLon, altitude: 120 }] : []
  );
  const [status, setStatus] = useState<string>('');
  const [drones, setDrones] = useState<Array<{ drone_id: string; name?: string }>>([]);
  const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
  const [payload, setPayload] = useState<Payload>(
    initialPayload ?? { item_name: '', weight_kg: 1, quantity: 1 }
  );
  const [showProducts, setShowProducts] = useState<boolean>(true);
  const [productSearch, setProductSearch] = useState<string>('');
  const [selectedProducts, setSelectedProducts] = useState<Array<{ product: Product; quantity: number }>>([]);

  const target = waypoints[0];
  const selectedDroneTelemetry = droneId ? dronesMap[droneId] : undefined;
  const { eta, distanceMeters } = useETA(selectedDroneTelemetry, target?.lat, target?.lon);

  const handleCoordinatesChange = (lat: number, lon: number) => {
    setWaypoints([{ lat, lon, altitude: 120 }]);
    setDraftTarget([lat, lon]);
    setStatus('');
  };

  const mgrsCoords = useMGRSCoordinates(initialLat, initialLon, handleCoordinatesChange);

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

  useEffect(() => {
    if (initialLat != null && initialLon != null) {
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
    if (initialPayloads && initialPayloads.length > 0) {
      const mapped: Array<{ product: Product; quantity: number }> = [];
      for (const item of initialPayloads) {
        const match = PRODUCTS.find((p) => p.name === item.item_name);
        if (match) mapped.push({ product: match, quantity: item.quantity });
      }
      if (mapped.length > 0) setSelectedProducts(mapped);
    }
  }, [initialPayloads]);

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
      onSubmitted?.();
    } catch (err: any) {
      setStatus(`Erreur: ${err.message}`);
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

      <MGRSCoordinateInput
        zone={mgrsCoords.mgrsZone}
        band={mgrsCoords.mgrsBand}
        grid={mgrsCoords.mgrsGrid}
        easting={mgrsCoords.mgrsEasting}
        northing={mgrsCoords.mgrsNorthing}
        onZoneChange={mgrsCoords.setMgrsZone}
        onBandChange={mgrsCoords.setMgrsBand}
        onGridChange={mgrsCoords.setMgrsGrid}
        onEastingChange={mgrsCoords.setMgrsEasting}
        onNorthingChange={mgrsCoords.setMgrsNorthing}
      />

      <SelectedProductsList
        selectedProducts={selectedProducts}
        onQuantityChange={(productId, quantity) => {
          setSelectedProducts((list) => list.map((it) => it.product.id === productId ? { ...it, quantity } : it));
        }}
        onRemove={(productId) => {
          setSelectedProducts((list) => list.filter((x) => x.product.id !== productId));
        }}
      />

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
