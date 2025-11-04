import axios from 'axios';
import { HealthStatus, DroneStatus } from '../types';

const API_BASE_URL = `/api`;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const healthApi = {
  getStatus: () => api.get<HealthStatus>('/health'),
};

export const droneApi = {
  getAll: () => api.get<DroneStatus[]>('/drones'),
  getById: (droneId: string) => api.get<DroneStatus>(`/drones/${droneId}`),
  arm: (droneId: string) => api.post(`/drones/${droneId}/arm`),
  disarm: (droneId: string) => api.post(`/drones/${droneId}/disarm`),
  takeoff: (droneId: string, altitude: number = 5.0) =>
    api.post(`/drones/${droneId}/takeoff?altitude=${altitude}`),
  land: (droneId: string) => api.post(`/drones/${droneId}/land`),
};
