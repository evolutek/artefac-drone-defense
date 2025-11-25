import React, { useEffect, useState } from 'react';
import MapView from './components/MapView';
import MissionForm from './components/MissionForm';
import { useDroneStore, type DroneState } from './state/store';
import Modal from './components/Modal';
import type { Payload } from './types';
import ProductCatalog from './components/ProductCatalog';
import SearchInput from './components/SearchInput';
import * as mgrs from 'mgrs';
import IntroSplash from './components/IntroSplash';

export default function App() {
  const [lastClick, setLastClick] = useState<{ lat: number; lon: number } | null>(null);
  // Trajectoires toujours affichées (toggle supprimé)
  const setDraftTarget = useDroneStore((s: DroneState) => s.setDraftTarget);
  const setSelectedDroneId = useDroneStore((s: DroneState) => s.setSelectedDroneId);
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const missions = useDroneStore((s: DroneState) => s.missions);
  const [replayPayload, setReplayPayload] = useState<Payload | undefined>(undefined);
  const [mode, setMode] = useState<'catalogue' | 'carte'>('catalogue');
  const [authenticated, setAuthenticated] = useState<boolean>(false);
  const [pin, setPin] = useState<string>('');
  const DEFAULT_PIN = '123123';
  const [logoClicks, setLogoClicks] = useState<number>(0);
  const [logoTimer, setLogoTimer] = useState<number | null>(null);
  const [inactiveTimer, setInactiveTimer] = useState<number | null>(null);

  useEffect(() => {
    function resetInactivity() {
      if (inactiveTimer) { clearTimeout(inactiveTimer); setInactiveTimer(null); }
      const id = window.setTimeout(() => {
        setAuthenticated(false);
        setPin('');
        setModalOpen(false);
        setMode('catalogue');
        setReplayPayload(undefined);
        setLastClick(null);
        setDraftTarget(null);
      }, 120000);
      setInactiveTimer(id);
    }
    const events = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll', 'wheel'];
    if (authenticated) {
      resetInactivity();
      events.forEach((ev) => window.addEventListener(ev, resetInactivity, { passive: true }));
    }
    return () => {
      if (inactiveTimer) { clearTimeout(inactiveTimer); setInactiveTimer(null); }
      events.forEach((ev) => window.removeEventListener(ev, resetInactivity));
    };
  }, [authenticated]);
  const [catalogSearch, setCatalogSearch] = useState<string>('');
  const [catalogCategory, setCatalogCategory] = useState<string>('');

  return (
    <div style={{ height: '100vh' }}>
      {!authenticated && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 3000, background: 'rgba(0,0,0,0.35)' }}>
          <IntroSplash loop speed={0.05} />
          <div
            style={{
              position: 'absolute', left: '50%', top: 'calc(50% + 8rem)', transform: 'translate(-50%, -50%)',
              width: 'min(360px, 92vw)',
              background: 'var(--glass)', backdropFilter: 'saturate(180%) blur(8px)',
              border: '1px solid var(--border)', borderRadius: 12, boxShadow: '0 10px 30px rgba(0,0,0,0.25)',
              padding: 16,
              zIndex: 3001
            }}
          >
            <div style={{ textAlign: 'center', fontWeight: 600, marginBottom: 6 }}>Entrer le PIN</div>
            <input
              type="password"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={6}
              className="input"
              value={pin}
              onChange={(e) => setPin(e.target.value.replace(/[^0-9]/g, '').slice(0, 6))}
              placeholder="••••••"
              style={{ display: 'block', margin: '0 auto', width: 'min(260px, 100%)', textAlign: 'center', fontSize: 24, letterSpacing: '6px', color: '#fff', border: '1px solid var(--border)' }}
              aria-label="PIN agent"
              onKeyDown={(e) => { if (e.key === 'Enter' && pin === DEFAULT_PIN) setAuthenticated(true); }}
            />
            <div style={{ display: 'flex', marginTop: 12 }}>
              <button
                type="button"
                className="btn"
                style={{ marginLeft: 'auto' }}
                onClick={() => { if (pin === DEFAULT_PIN) setAuthenticated(true); }}
              >Accéder</button>
            </div>
          </div>
        </div>
      )}
      <header style={{
        position: 'fixed', top: 0, left: 0, right: 0, height: 48,
        display: 'flex', alignItems: 'center', paddingBottom: '3rem 3rem', gap: 16,
        background: 'var(--glass)',
        backdropFilter: 'saturate(180%) blur(8px)',
        fontFamily: 'apple-system, sans-serif',
        zIndex: 1000
      }}>
        <img
          src="/assets/logo-artifact-ago-white.png"
          alt="Logo"
          style={{ height: 40, marginRight: 12, cursor: 'pointer' }}
          onClick={() => {
            if (!authenticated) return;
            const next = logoClicks + 1;
            setLogoClicks(next);
            if (next >= 3) {
              if (logoTimer) { clearTimeout(logoTimer); setLogoTimer(null); }
              setLogoClicks(0);
              setAuthenticated(false);
              setPin('');
              setModalOpen(false);
              setMode('catalogue');
              setReplayPayload(undefined);
              setLastClick(null);
              setDraftTarget(null);
              return;
            }
            if (!logoTimer) {
              const id = window.setTimeout(() => { setLogoClicks(0); setLogoTimer(null); }, 600);
              setLogoTimer(id);
            }
          }}
        />
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center', paddingLeft: 12 }}>
          <button
            type="button"
            className="btn"
            onClick={() => setMode(mode === 'catalogue' ? 'carte' : 'catalogue')}
          >{mode === 'catalogue' ? 'Mode Carte' : 'Mode Catalogue'}</button>
          <button
            type="button"
            className="btn"
            onClick={() => { setMode('carte'); setReplayPayload(undefined); setModalOpen(true); }}
            style={{ margin: 15.8 }}
          >Créer mission</button>
        </div>
      </header>
      <main style={{ height: '100vh', paddingTop: mode === 'carte' ? 48 : 80 }}>
        {mode === 'catalogue' ? (
          <>
            <div className="catalog-toolbar" style={{ padding: 12 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <SearchInput
                  value={catalogSearch}
                  onChange={setCatalogSearch}
                  placeholder="Rechercher des produits"
                  ariaLabel="Rechercher des produits"
                  small
                />
                <select
                  className="input input-sm"
                  value={catalogCategory}
                  onChange={(e) => setCatalogCategory(e.target.value)}
                  aria-label="Filtrer par catégorie"
                  style={{ minWidth: 180 }}
                >
                  <option value="">Toutes les catégories</option>
                  <option value="munitions">Munitions</option>
                  <option value="attachments">Accessoires</option>
                  <option value="medicaments">Médicaments</option>
                  <option value="communication">Communication</option>
                  <option value="logistique">Logistique</option>
                  <option value="autre">Autre</option>
                </select>
              </div>
            </div>
            <ProductCatalog onSelectProduct={(p) => {
              setReplayPayload({ item_name: p.name, weight_kg: p.weight_kg ?? 1, quantity: 1 });
              setMode('carte');
              setModalOpen(true);
            }} searchTerm={catalogSearch} category={catalogCategory} />
          </>
        ) : (
        <MapView setWaypointFromMap={(lat, lon) => {
          setLastClick({ lat, lon });
          setDraftTarget([lat, lon]);
          // si aucun drone sélectionné, choisir le premier disponible
          const drones = Object.values(useDroneStore.getState().drones);
          if (!useDroneStore.getState().selectedDroneId && drones.length > 0) {
            setSelectedDroneId(drones[0].drone_id);
          }
          setReplayPayload(undefined);
          setModalOpen(true);
        }} />
        )}
        {missions.length > 0 && (
          <div style={{
            position: 'fixed', top: 80, left: 12, display: 'flex', flexDirection: 'column', gap: 8,
            zIndex: 1000
          }}>
            {missions.map((m) => (
              <button key={m.id}
                onClick={() => {
                  const first = m.waypoints?.[0];
                  if (first) {
                    setLastClick({ lat: first[0], lon: first[1] });
                    setDraftTarget([first[0], first[1]]);
                  }
                  setSelectedDroneId(m.drone_id);
                  setReplayPayload(m.payload);
                  setModalOpen(true);
                }}
                className="btn"
                style={{
                  padding: '6px 10px', textAlign: 'left', minWidth: 220, justifyContent: 'flex-start'
                }}>
                #{m.id} • {m.drone_id}
                {Array.isArray((m as any).payloads) && m.payloads && m.payloads.length > 0
                  ? ` — ${m.payloads.map((p) => `${p.item_name} x${p.quantity}`).join(', ')}`
                  : (m.payload ? ` — ${m.payload.item_name} x${m.payload.quantity} (${m.payload.weight_kg}kg)` : '')}
                {m.status ? ` — ${m.status}` : ''}
              </button>
            ))}
          </div>
        )}
        {lastClick && (
          <div style={{
            position: 'fixed', bottom: 16, left: 16,
            background: 'rgba(0,0,0,0.6)', color: '#fff', padding: '8px 10px',
            borderRadius: 8, fontSize: 13, zIndex: 1000,
            fontFamily: 'apple-system, sans-serif',
          }}>
            MGRS: {mgrs.forward([lastClick.lon, lastClick.lat])}
          </div>
        )}
      </main>
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        header={<h3 style={{ margin: 0, flex: '1 1 0%' }}>Créer une mission</h3>}
      >
        <MissionForm
          initialLat={lastClick?.lat}
          initialLon={lastClick?.lon}
          initialPayload={replayPayload}
        />
      </Modal>
    </div>
  );
}
