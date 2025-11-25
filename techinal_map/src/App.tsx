import React, { useEffect, useState, useRef } from 'react';
import MapView from './components/MapView';
import MissionForm from './components/MissionForm';
import { onStateEvent, offStateEvent, startWebSocket } from './ws';
import { useDroneStore, type DroneState } from './state/store';
import Modal from './components/Modal';
import type { Payload, PayloadItem } from './types';
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
  const [selectedMissionId, setSelectedMissionId] = useState<number | null>(null);
  const [replayPayload, setReplayPayload] = useState<Payload | undefined>(undefined);
  const [replayPayloads, setReplayPayloads] = useState<PayloadItem[] | undefined>(undefined);
  const [mode, setMode] = useState<'catalogue' | 'carte' | 'historique'>('catalogue');
  const [authenticated, setAuthenticated] = useState<boolean>(() => {
    try { return localStorage.getItem('session_auth') === '1'; } catch { return false; }
  });
  const [pin, setPin] = useState<string>('');
  const DEFAULT_PIN = (import.meta.env.VITE_PIN as string) ?? '123123123';
  const PIN_LENGTH = DEFAULT_PIN.length;
  const [logoClicks, setLogoClicks] = useState<number>(0);
  const [logoTimer, setLogoTimer] = useState<number | null>(null);
  const [inactiveTimer, setInactiveTimer] = useState<number | null>(null);
  const [wrongAttempts, setWrongAttempts] = useState<number>(() => {
    try {
      const v = parseInt(localStorage.getItem('pin_fail_count') || '0');
      return (import.meta.env.DEV ? 0 : v);
    } catch { return 0; }
  });
  const [pinError, setPinError] = useState<string>('');
  const [locked, setLocked] = useState<boolean>(false);

  function wipeAll() {
    try { localStorage.clear(); } catch {}
    try { sessionStorage.clear(); } catch {}
    try { useDroneStore.setState({ missions: [], drones: {}, trajectories: {}, draftTarget: null, selectedDroneId: null }); } catch {}
    setAuthenticated(false);
    try { localStorage.setItem('session_auth', '0'); } catch {}
    setPin('');
    setModalOpen(false);
    setMode('catalogue');
    setReplayPayload(undefined);
    setLastClick(null);
    setDraftTarget(null);
    setWrongAttempts(0);
    try { localStorage.setItem('pin_fail_count', '0'); } catch {}
    window.location.reload();
  }

  function handleAccess() {
    if (pin === DEFAULT_PIN) {
      setAuthenticated(true);
      try { localStorage.setItem('session_auth', '1'); } catch {}
      setPin('');
      setPinError('');
      setWrongAttempts(0);
      try { localStorage.setItem('pin_fail_count', '0'); } catch {}
      return;
    }
    const next = wrongAttempts + 1;
    setWrongAttempts(next);
    try { localStorage.setItem('pin_fail_count', String(next)); } catch {}
    setPinError(`PIN incorrect — tentative ${next}/3`);
    if (next >= 3) {
      setLocked(true);
    }
  }

  useEffect(() => {
    setLocked(wrongAttempts >= 3);
  }, [wrongAttempts]);

  const enableIdleLock = (import.meta.env.VITE_IDLE_LOCK as string) === 'true';
  useEffect(() => {
    if (!enableIdleLock) return;
    function resetInactivity() {
      if (inactiveTimer) { clearTimeout(inactiveTimer); setInactiveTimer(null); }
      const id = window.setTimeout(() => {
        setAuthenticated(false);
        try { localStorage.setItem('session_auth', '0'); } catch {}
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
  }, [authenticated, enableIdleLock]);
  const [catalogSearch, setCatalogSearch] = useState<string>('');
  const [catalogCategory, setCatalogCategory] = useState<string>('');
  const [tick, setTick] = useState<number>(0);
  useEffect(() => {
    const id = window.setInterval(() => setTick((t) => t + 1), 1000);
    return () => { window.clearInterval(id); };
  }, []);
  const [missionsPanelPos, setMissionsPanelPos] = useState<{ x: number; y: number }>({ x: 12, y: 80 });
  const panelRef = useRef<HTMLDivElement | null>(null);
  const dragOffsetRef = useRef<{ dx: number; dy: number } | null>(null);
  const draggingRef = useRef<boolean>(false);
  const dragMovedRef = useRef<boolean>(false);
  function startDrag(clientX: number, clientY: number) {
    const rect = panelRef.current?.getBoundingClientRect();
    const dx = rect ? clientX - rect.left : 0;
    const dy = rect ? clientY - rect.top : 0;
    dragOffsetRef.current = { dx, dy };
    draggingRef.current = true;
    dragMovedRef.current = false;
    function onMove(ev: MouseEvent) {
      if (!draggingRef.current || !dragOffsetRef.current) return;
      const nx = ev.clientX - dragOffsetRef.current.dx;
      const ny = ev.clientY - dragOffsetRef.current.dy;
      const rect2 = panelRef.current?.getBoundingClientRect();
      const moved = rect2 && (Math.abs(rect2.left - nx) > 3 || Math.abs(rect2.top - ny) > 3);
      if (moved) dragMovedRef.current = true;
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      setMissionsPanelPos({ x: Math.max(0, Math.min(vw - 200, nx)), y: Math.max(48, Math.min(vh - 100, ny)) });
    }
    function onUp() {
      draggingRef.current = false;
      dragOffsetRef.current = null;
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    }
    window.addEventListener('mousemove', onMove, { passive: true });
    window.addEventListener('mouseup', onUp, { passive: true });
  }

  // Charger les missions depuis le backend au démarrage
  useEffect(() => {
    if (!authenticated) return;
    // Assurer la connexion WebSocket pour recevoir les mises à jour en temps réel
    startWebSocket();
    const fn = useDroneStore.getState().loadMissions;
    if (typeof fn === 'function') {
      fn().catch(() => {});
    }
  }, [authenticated]);

  // Écoute temps réel des missions: création, statut, note, suppression
  useEffect(() => {
    if (!authenticated) return;
    const handler = (msg: any) => {
      if (msg?.type !== 'state') return;
      const t = msg?.data?.type;
      if (t === 'mission_status_update') {
        const mission_id = msg?.data?.mission_id;
        const status = msg?.data?.status;
        if (typeof mission_id === 'number' && typeof status === 'string') {
          const setStatus = useDroneStore.getState().setMissionStatus;
          if (typeof setStatus === 'function') {
            setStatus(mission_id, status);
          }
          return; // éviter rechargement complet pour simple mise à jour de statut
        }
      }
      if (t === 'mission_upsert' || t === 'mission_note_update' || t === 'mission_delete') {
        const fn = useDroneStore.getState().loadMissions;
        if (typeof fn === 'function') {
          fn().catch(() => {});
        }
      }
    };
    onStateEvent(handler);
    return () => offStateEvent(handler);
  }, [authenticated]);

  // Afficher les statuts en français et en majuscules pour l'UI
  function toDisplayStatus(s?: string): string {
    if (!s) return '';
    const raw = String(s);
    const k = raw.trim().toLowerCase().replace(/[_-]+/g, ' ');
    const map: Record<string, string> = {
      'assigned': 'ASSIGNÉ',
      'en cours': 'EN COURS',
      'in progress': 'EN COURS',
      'en route': 'EN ROUTE',
      'in transit': 'EN ROUTE',
      'completed': 'TERMINÉ',
      'delivered': 'LIVRÉ',
      'livré': 'LIVRÉ',
      'cancelled': 'ANNULÉ',
      'canceled': 'ANNULÉ',
      'failed': 'ÉCHOUÉ',
      'error': 'ERREUR',
      'queued': 'EN FILE',
      'scheduled': 'PLANIFIÉ',
      'pending': 'EN ATTENTE',
      'en attente': 'EN ATTENTE',
      'mission': 'EN MISSION',
      'returning': 'RETOUR',
      'armed': 'ARMÉ',
      'idle': 'INACTIF',
    };
    if (map[k]) return map[k];
    return raw.replace(/[_-]+/g, ' ').toUpperCase();
  }

  // Couleur d'affichage par statut (clé normalisée)
  function toStatusColor(s?: string): string {
    if (!s) return '#b0b0b8';
    const k = String(s).trim().toLowerCase().replace(/[_-]+/g, ' ');
    const colors: Record<string, string> = {
      'assigned': '#64b5f6',
      'en cours': '#ffca28',
      'in progress': '#ffca28',
      'en route': '#4fc3f7',
      'in transit': '#4fc3f7',
      'completed': '#4caf50',
      'delivered': '#4caf50',
      'livré': '#4caf50',
      'cancelled': '#e57373',
      'canceled': '#e57373',
      'failed': '#f44336',
      'error': '#e53935',
      'queued': '#90a4ae',
      'scheduled': '#9575cd',
      'pending': '#ff9800',
      'en attente': '#ff9800',
      'mission': '#ff7043',
      'returning': '#29b6f6',
      'armed': '#81c784',
      'idle': '#9e9e9e',
    };
    return colors[k] ?? '#b0b0b8';
  }

  return (
    <div style={{ height: '100vh' }}>
      {!authenticated && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 3000, background: 'rgba(0,0,0,0.35)' }}>
          <IntroSplash loop speed={0.05} />
          {!locked && (
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
                maxLength={PIN_LENGTH}
                className="input"
                value={pin}
                onChange={(e) => setPin(e.target.value.replace(/[^0-9]/g, '').slice(0, PIN_LENGTH))}
                placeholder={"•".repeat(PIN_LENGTH)}
                style={{ display: 'block', margin: '0 auto', width: 'min(260px, 100%)', textAlign: 'center', fontSize: 24, letterSpacing: '6px', color: '#fff', border: '1px solid var(--border)' }}
                aria-label="PIN agent"
                onKeyDown={(e) => { if (e.key === 'Enter') handleAccess(); }}
              />
              {pinError && (<div style={{ color: '#f44336', textAlign: 'center', marginTop: 8, fontSize: 13 }}>{pinError}</div>)}
              <div style={{ display: 'flex', marginTop: 12 }}>
                <button
                  type="button"
                  className="btn"
                  style={{ marginLeft: 'auto' }}
                  onClick={() => { handleAccess(); }}
                >Accéder</button>
              </div>
            </div>
          )}
        </div>
      )}
      {authenticated && (
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
              try { localStorage.setItem('session_auth', '0'); } catch {}
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
            aria-label="Historique des commandes"
            onClick={() => setMode('historique')}
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: 6 }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <rect x="4" y="6" width="16" height="2" fill="#fff"/>
              <rect x="4" y="11" width="16" height="2" fill="#fff"/>
              <rect x="4" y="16" width="16" height="2" fill="#fff"/>
            </svg>
          </button>

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
      )}
      {authenticated && (
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
              setReplayPayloads(undefined);
              setMode('carte');
              setModalOpen(true);
            }} searchTerm={catalogSearch} category={catalogCategory} />
          </>
        ) : mode === 'carte' ? (
        <MapView setWaypointFromMap={(lat, lon) => {
          setLastClick({ lat, lon });
          setDraftTarget([lat, lon]);
          // si aucun drone sélectionné, choisir le premier disponible
          const drones = Object.values(useDroneStore.getState().drones);
          if (!useDroneStore.getState().selectedDroneId && drones.length > 0) {
            setSelectedDroneId(drones[0].drone_id);
          }
          setReplayPayload(undefined);
          setReplayPayloads(undefined);
          setModalOpen(true);
        }} />
        ) : (
          <div style={{ padding: 16 }}>
            <h3 style={{ marginTop: 0 }}>Historique des commandes</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[...missions].sort((a, b) => (b.started_at ?? b.id) - (a.started_at ?? a.id)).map((m, idx, arr) => (
                <div key={m.id} style={{ display: 'inline-block' }}>
                  <button
                    onClick={() => {
                      const first = m.waypoints?.[0];
                      if (first) {
                        setLastClick({ lat: first[0], lon: first[1] });
                        setDraftTarget([first[0], first[1]]);
                      }
                      setSelectedMissionId(m.id);
                      setSelectedDroneId(m.drone_id);
                      setReplayPayload(m.payload);
                      setReplayPayloads(m.payloads);
                      setMode('carte');
                      setModalOpen(true);
                    }}
                    className="btn"
                    style={{ padding: '6px 10px', textAlign: 'left', justifyContent: 'flex-start' }}
                  >
                    <>#{m.id} • {m.drone_id}</>
                    {Array.isArray((m as any).payloads) && m.payloads && m.payloads.length > 0
                      ? ` — ${m.payloads.map((p) => `${p.item_name} x${p.quantity}`).join(', ')}`
                      : (m.payload ? ` — ${m.payload.item_name} x${m.payload.quantity} (${m.payload.weight_kg}kg)` : '')}
                    {m.status && (<>
                      {' '}-{' '}<span style={{ color: toStatusColor(m.status), marginLeft: 4 }}>{toDisplayStatus(m.status)}</span>
                    </>)}
                    {m.eta && (<> • ETA {m.eta}</>)}
                    {(m as any).note && (<> • Note: {(m as any).note}</>)}
                  </button>
                  {typeof m.progress === 'number' && (
                    <div style={{ marginTop: 4, height: 6, background: 'rgba(255,255,255,0.12)', borderRadius: 6, overflow: 'hidden', width: '100%' }}>
                      <div style={{ height: '100%', width: `${Math.max(0, Math.min(100, m.progress))}%`, background: '#4caf50' }} />
                    </div>
                  )}
                  {idx < arr.length - 1 && (
                    <hr style={{
                      border: 'none',
                      borderTop: '1px solid var(--border-soft)',
                      margin: '8px 0'
                    }} />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        {mode === 'carte' && missions.length > 0 && (
          <div
            ref={panelRef}
            style={{
              position: 'fixed', top: missionsPanelPos.y, left: missionsPanelPos.x,
              display: 'flex', flexDirection: 'column', gap: 8, zIndex: 1000,
              maxWidth: 'min(540px, 94vw)'
            }}
          >
            <div
              style={{ height: 10, background: 'rgba(255,255,255,0.12)', borderRadius: 6, cursor: 'move' }}
              onMouseDown={(e) => startDrag(e.clientX, e.clientY)}
              onTouchStart={(e) => {
                const t = e.touches[0];
                startDrag(t.clientX, t.clientY);
              }}
            />
            {missions.filter((m) => {
              if (m.status !== 'livré') return true;
              const d = (m as any).delivered_at as number | undefined;
              return typeof d === 'number' && (Date.now() - d) < 3 * 60 * 1000;
            }).map((m) => (
              <div key={m.id} style={{ display: 'inline-block' }}>
                <button
                  onClick={() => {
                    if (draggingRef.current || dragMovedRef.current) { draggingRef.current = false; dragMovedRef.current = false; return; }
                    const first = m.waypoints?.[0];
                    if (first) {
                      setLastClick({ lat: first[0], lon: first[1] });
                      setDraftTarget([first[0], first[1]]);
                    }
                    setSelectedMissionId(m.id);
                    setSelectedDroneId(m.drone_id);
                    setReplayPayload(m.payload);
                    setReplayPayloads(m.payloads);
                    setModalOpen(true);
                  }}
                  className="btn"
                  style={{ padding: '6px 10px', textAlign: 'left', justifyContent: 'flex-start', cursor: 'move' }}
                  onMouseDown={(e) => startDrag(e.clientX, e.clientY)}
                  onTouchStart={(e) => { const t = e.touches[0]; startDrag(t.clientX, t.clientY); }}
                >
                  <>#{m.id} • {m.drone_id}</>
                  {Array.isArray((m as any).payloads) && m.payloads && m.payloads.length > 0
                    ? ` — ${m.payloads.map((p) => `${p.item_name} x${p.quantity}`).join(', ')}`
                    : (m.payload ? ` — ${m.payload.item_name} x${m.payload.quantity} (${m.payload.weight_kg}kg)` : '')}
                  {m.status && (<>
                    {' '}-{' '}<span style={{ color: toStatusColor(m.status), marginLeft: 4 }}>{toDisplayStatus(m.status)}</span>
                  </>)}
                  {m.status && m.status !== 'livré' && m.eta && (<> • ETA {m.eta}</>)}
                  {(m as any).note && (<> • Note: {(m as any).note}</>)}
                </button>
                {typeof m.progress === 'number' && (
                  <div style={{ marginTop: 4, height: 6, background: 'rgba(255,255,255,0.12)', borderRadius: 6, overflow: 'hidden', width: '100%' }}>
                    <div style={{ height: '100%', width: `${Math.max(0, Math.min(100, m.progress))}%`, background: '#4caf50' }} />
                  </div>
                )}
              </div>
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
            {/* Coordonnées du point cliqué */}
            <div>MGRS: {mgrs.forward([lastClick.lon, lastClick.lat])}</div>
            {/* Texte de mission: base items + statut + note, sans écraser la base */}
            {(() => {
              const m = missions.find((mm) => mm.id === selectedMissionId);
              if (!m) return null;
              const items = Array.isArray((m as any).payloads) && m.payloads && m.payloads.length > 0
                ? m.payloads.map((p) => `${p.item_name} x${p.quantity}`).join(', ')
                : (m.payload ? `${m.payload.item_name} x${m.payload.quantity}` : '');
              const statusEl = m.status ? (<>
                {' '}-{' '}<span style={{ color: toStatusColor(m.status), marginLeft: 4 }}>{toDisplayStatus(m.status)}</span>
              </>) : null;
              const noteEl = (m as any)?.note ? (<> • Note: {(m as any).note}</>) : null;
              return (
                <div style={{ marginTop: 4, color: 'rgba(255,255,255,0.90)' }}>
                  {items}{statusEl}{noteEl}
                </div>
              );
            })()}
          </div>
        )}
      </main>
      )}
      {authenticated && (
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        header={<h3 style={{ margin: 0, flex: '1 1 0%' }}>Créer une mission</h3>}
      >
        <MissionForm
          initialLat={lastClick?.lat}
          initialLon={lastClick?.lon}
          initialPayload={replayPayload}
          initialPayloads={replayPayloads}
          onSubmitted={() => setModalOpen(false)}
        />
      </Modal>
      )}
    </div>
  );
}
