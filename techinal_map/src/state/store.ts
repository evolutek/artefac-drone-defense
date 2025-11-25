import { create, type StateCreator } from 'zustand';
import type { DroneTelemetry, MissionCreate, Payload, PayloadItem } from '../types';

export type DroneState = {
  drones: Record<string, DroneTelemetry>;
  trajectories: Record<string, Array<[number, number]>>; // [lat, lon]
  zones: Array<{ id: string; name: string; center: [number, number]; radius: number; color?: string }>;
  missions: Array<{ id: number; drone_id: string; waypoints: Array<[number, number]>; status?: string; payload?: Payload; payloads?: PayloadItem[]; progress?: number; eta?: string; started_at?: number; delivered_at?: number }>;
  showTrajectories: boolean;
  draftTarget?: [number, number] | null;
  selectedDroneId?: string | null;
  setShowTrajectories: (show: boolean) => void;
  upsertTelemetry: (t: DroneTelemetry) => void;
  addMission: (m: { id: number; drone_id: string; waypoints: Array<[number, number]>; status?: string; payload?: Payload; payloads?: PayloadItem[]; progress?: number; eta?: string; started_at?: number; delivered_at?: number }) => void;
  submitMission: (m: MissionCreate, payload?: Payload, payloads?: PayloadItem[]) => Promise<void>;
  setDraftTarget: (pt: [number, number] | null) => void;
  setSelectedDroneId: (id: string | null) => void;
};

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
function loadPersistedMissions(): DroneState['missions'] {
  try {
    const raw = localStorage.getItem('missions');
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed as DroneState['missions'];
    }
  } catch {}
  return [];
}

const createStore: StateCreator<DroneState> = (set, get) => ({
  drones: {},
  trajectories: {},
  zones: [
    { id: 'z1', name: 'Zone Sûre', center: [48.8566, 2.3522], radius: 2000, color: '#4caf50' },
    { id: 'z2', name: 'Zone Restreinte', center: [48.85, 2.28], radius: 1200, color: '#f44336' }
  ],
  missions: loadPersistedMissions(),
  showTrajectories: true,
  draftTarget: null,
  selectedDroneId: null,
  setShowTrajectories: (show: boolean) => set({ showTrajectories: show }),
  upsertTelemetry: (t: DroneTelemetry) => set((state: DroneState) => {
    const prev: [number, number][] = state.trajectories[t.drone_id] ?? [];
    const point: [number, number] = [t.lat, t.lon];
    // Concat préserve le type tuple, évitant l'élargissement en number[][]
    const nextTraj: [number, number][] = prev.concat([point]).slice(-500);
    return {
      drones: { ...state.drones, [t.drone_id]: t },
      trajectories: { ...state.trajectories, [t.drone_id]: nextTraj }
    };
  }),
  addMission: (m: { id: number; drone_id: string; waypoints: Array<[number, number]>; status?: string; payload?: Payload; payloads?: PayloadItem[]; progress?: number; eta?: string; started_at?: number }) =>
    set((state: DroneState) => {
      const next = [...state.missions, m];
      try { localStorage.setItem('missions', JSON.stringify(next)); } catch {}
      return { missions: next };
    }),
  setDraftTarget: (pt: [number, number] | null) => set({ draftTarget: pt }),
  setSelectedDroneId: (id: string | null) => set({ selectedDroneId: id }),
  submitMission: async (m: MissionCreate, payload?: Payload, payloads?: PayloadItem[]) => {
    const useMock = import.meta.env.DEV && (import.meta.env.VITE_USE_MOCK ?? 'true') !== 'false';
    const waypoints: [number, number][] = m.waypoints.map(
      (w: { lat: number; lon: number }) => [w.lat, w.lon] as [number, number]
    );
    if (useMock) {
      const id = Date.now();
      const start = Date.now();
      const etaDate = new Date(start + 20 * 60 * 1000);
      const eta = `${etaDate.getHours().toString().padStart(2, '0')}:${etaDate.getMinutes().toString().padStart(2, '0')}`;
      set((state: DroneState) => ({
        missions: (() => {
          const next = [
            ...state.missions,
            { id, drone_id: m.drone_id, waypoints, status: 'préparation', payload, payloads, progress: 0, eta, started_at: start }
          ];
          try { localStorage.setItem('missions', JSON.stringify(next)); } catch {}
          return next;
        })()
      }));
      const steps: Array<{ after: number; status: string; progress: number }> = [
        { after: 2000, status: 'chargement', progress: 20 },
        { after: 6000, status: 'en vol', progress: 50 },
        { after: 12000, status: 'près de la destination', progress: 80 },
        { after: 16000, status: 'livré', progress: 100 }
      ];
      steps.forEach((s) => {
        window.setTimeout(() => {
          set((state: DroneState) => ({
            missions: (() => {
              const next = state.missions.map((mm) => mm.id === id ? { ...mm, status: s.status, progress: s.progress, delivered_at: s.status === 'livré' ? Date.now() : mm.delivered_at } : mm);
              try { localStorage.setItem('missions', JSON.stringify(next)); } catch {}
              return next;
            })()
          }));
        }, s.after);
      });
      return;
    }
    const res = await fetch(`${API_URL}/missions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...m, payload, payloads })
    });
    if (!res.ok) throw new Error(`Échec création mission: ${res.status}`);
    const created = await res.json();
    set((state: DroneState) => ({
      missions: [
        ...state.missions,
        { id: created.id ?? Date.now(), drone_id: m.drone_id, waypoints, status: created.status, payload, payloads }
      ]
    }));
  }
});

export const useDroneStore = create<DroneState>(createStore);
