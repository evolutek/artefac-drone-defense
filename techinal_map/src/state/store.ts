import { create, type StateCreator } from 'zustand';
import type { DroneTelemetry, MissionCreate, Payload, PayloadItem } from '../types';

export type DroneState = {
  drones: Record<string, DroneTelemetry>;
  trajectories: Record<string, Array<[number, number]>>; // [lat, lon]
  zones: Array<{ id: string; name: string; center: [number, number]; radius: number; color?: string }>;
  missions: Array<{ id: number; drone_id: string; waypoints: Array<[number, number]>; status?: string; payload?: Payload; payloads?: PayloadItem[] }>;
  showTrajectories: boolean;
  draftTarget?: [number, number] | null;
  selectedDroneId?: string | null;
  setShowTrajectories: (show: boolean) => void;
  upsertTelemetry: (t: DroneTelemetry) => void;
  addMission: (m: { id: number; drone_id: string; waypoints: Array<[number, number]>; status?: string; payload?: Payload; payloads?: PayloadItem[] }) => void;
  submitMission: (m: MissionCreate, payload?: Payload, payloads?: PayloadItem[]) => Promise<void>;
  setDraftTarget: (pt: [number, number] | null) => void;
  setSelectedDroneId: (id: string | null) => void;
};

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

const createStore: StateCreator<DroneState> = (set, get) => ({
  drones: {},
  trajectories: {},
  zones: [
    { id: 'z1', name: 'Zone Sûre', center: [48.8566, 2.3522], radius: 2000, color: '#4caf50' },
    { id: 'z2', name: 'Zone Restreinte', center: [48.85, 2.28], radius: 1200, color: '#f44336' }
  ],
  missions: [],
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
  addMission: (m: { id: number; drone_id: string; waypoints: Array<[number, number]>; status?: string; payload?: Payload; payloads?: PayloadItem[] }) =>
    set((state: DroneState) => ({ missions: [...state.missions, m] })),
  setDraftTarget: (pt: [number, number] | null) => set({ draftTarget: pt }),
  setSelectedDroneId: (id: string | null) => set({ selectedDroneId: id }),
  submitMission: async (m: MissionCreate, payload?: Payload, payloads?: PayloadItem[]) => {
    const res = await fetch(`${API_URL}/missions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...m, payload, payloads })
    });
    if (!res.ok) throw new Error(`Échec création mission: ${res.status}`);
    const created = await res.json();
    const waypoints: [number, number][] = m.waypoints.map(
      (w: { lat: number; lon: number }) => [w.lat, w.lon] as [number, number]
    );
    set((state: DroneState) => ({
      missions: [
        ...state.missions,
        { id: created.id ?? Date.now(), drone_id: m.drone_id, waypoints, status: created.status, payload, payloads }
      ]
    }));
  }
});

export const useDroneStore = create<DroneState>(createStore);