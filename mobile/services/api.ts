/**
 * API Client for Simulation Control Server
 * Communicates with Flask server running on ros2_integration container (port 8080)
 */

import axios, { AxiosInstance } from 'axios';
import { Platform } from 'react-native';

// ============================================================================
// Types
// ============================================================================

export interface Drone {
  drone_num: number;
  drone_id: string;
  model_name: string;
  position?: { x: number; y: number; z: number };
  spawned_at?: string;
}

export interface Zone {
  zone_id: string;
  name: string;
  type: 'jamming' | 'no-fly' | 'restricted';
  center: { x: number; y: number; z: number };
  radius: number;
  created_at?: string;
}

export interface Entrepot {
  entrepot_id: string;
  name: string;
  type: 'medicaments' | 'munitions' | 'equipements' | 'nourritures' | string; // Allow custom types
  position: { x: number; y: number; z: number };
  created_at?: string;
}

export interface Livraison {
  livraison_id: string;
  name: string;
  type: 'medicaments' | 'munitions' | 'equipements' | 'nourritures' | string; // Allow custom types
  position: { x: number; y: number; z: number };
  created_at?: string;
}

export interface DroneModel {
  id: string;
  description: string;
  details: string;
  type: string;
}

export interface ModelsResponse {
  models: DroneModel[];
  default_model: string;
}

export interface SpawnDroneRequest {
  x?: number;
  y?: number;
  z?: number;
  model?: string;
}

export interface CreateZoneRequest {
  name: string;
  type: 'jamming' | 'no-fly' | 'restricted';
  center: { x: number; y: number; z: number };
  radius: number;
}

export interface CreateEntrepotRequest {
  name: string;
  type: string; // medicaments, munitions, equipements, nourritures, or custom
  position: { x: number; y: number; z: number };
}

export interface CreateLivraisonRequest {
  name: string;
  type: string; // medicaments, munitions, equipements, nourritures, or custom
  position: { x: number; y: number; z: number };
}

export interface ApiResponse {
  success: boolean;
  message: string;
  drone_id?: string;
  drone_num?: number;
  zone_id?: string;
  entrepot_id?: string;
  entrepot_num?: number;
  livraison_id?: string;
  livraison_num?: number;
}

export interface HealthResponse {
  status: string;
  service: string;
  active_drones_count: number;
  active_zones_count: number;
  active_entrepots_count?: number;
  active_livraisons_count?: number;
  max_drones: number;
}

// ============================================================================
// Configuration
// ============================================================================

// Default to localhost for web, configurable for mobile
// In production, set environment variable EXPO_PUBLIC_API_URL
const getBaseURL = (): string => {
  // Check for environment variable first
  const envUrl = process.env.EXPO_PUBLIC_API_URL;
  if (envUrl) {
    return envUrl;
  }

  // Default URLs based on platform
  if (Platform.OS === 'web') {
    // Web: assume running on same host as Docker
    return 'http://localhost:8080';
  } else {
    // Mobile real device: use mDNS for auto-discovery
    // Mobile emulator: use platform-specific localhost
    // Try mDNS first (works on real devices on same network)
    return 'http://artefac-sim.local:8080';
  }
};

// ============================================================================
// API Client
// ============================================================================

class SimulationControlApi {
  private client: AxiosInstance;

  constructor() {
    const baseURL = getBaseURL();

    this.client = axios.create({
      baseURL,
      timeout: 30000, // 30s timeout (spawn can take ~15s)
      headers: {
        'Content-Type': 'application/json',
      },
    });

    console.log(`[API] Initialized with base URL: ${baseURL}`);
  }

  /**
   * Change base URL at runtime (useful for mobile when user configures server IP)
   */
  setBaseURL(url: string) {
    this.client.defaults.baseURL = url;
    console.log(`[API] Base URL changed to: ${url}`);
  }

  getBaseURL(): string {
    return this.client.defaults.baseURL || '';
  }

  // --------------------------------------------------------------------------
  // Health & Status
  // --------------------------------------------------------------------------

  async health(): Promise<HealthResponse> {
    const response = await this.client.get<HealthResponse>('/health');
    return response.data;
  }

  async getAvailableModels(): Promise<ModelsResponse> {
    const response = await this.client.get<ModelsResponse>('/models');
    return response.data;
  }

  // --------------------------------------------------------------------------
  // Drones
  // --------------------------------------------------------------------------

  async getActiveDrones(): Promise<Drone[]> {
    const response = await this.client.get<{ drones: Drone[]; count: number }>('/drones/active');
    return response.data.drones;
  }

  async spawnDrone(position?: SpawnDroneRequest): Promise<ApiResponse> {
    const response = await this.client.post<ApiResponse>('/drones/spawn', position || {});
    return response.data;
  }

  async despawnDrone(droneNum: number): Promise<ApiResponse> {
    const response = await this.client.delete<ApiResponse>(`/drones/${droneNum}`);
    return response.data;
  }

  async batchDespawnDrones(droneNums: number[]): Promise<{
    success: boolean;
    message: string;
    results: Array<{ drone_num: number; success: boolean; message: string }>;
    succeeded_count: number;
    failed_count: number;
  }> {
    const response = await this.client.post('/drones/batch-delete', { drone_nums: droneNums });
    return response.data;
  }

  // --------------------------------------------------------------------------
  // Zones
  // --------------------------------------------------------------------------

  async getZones(): Promise<Zone[]> {
    const response = await this.client.get<{ zones: Zone[]; count: number }>('/zones');
    return response.data.zones;
  }

  async createZone(zone: CreateZoneRequest): Promise<ApiResponse> {
    const response = await this.client.post<ApiResponse>('/zones', zone);
    return response.data;
  }

  async deleteZone(zoneId: string): Promise<ApiResponse> {
    const response = await this.client.delete<ApiResponse>(`/zones/${zoneId}`);
    return response.data;
  }

  async batchDeleteZones(zoneIds: string[]): Promise<{
    success: boolean;
    message: string;
    results: Array<{ zone_id: string; success: boolean; message: string }>;
    succeeded_count: number;
    failed_count: number;
  }> {
    const response = await this.client.post('/zones/batch-delete', { zone_ids: zoneIds });
    return response.data;
  }

  // Alias for backward compatibility
  async getActiveZones(): Promise<Zone[]> {
    return this.getZones();
  }

  // --------------------------------------------------------------------------
  // Entrepôts (Warehouses)
  // --------------------------------------------------------------------------

  async getEntrepots(): Promise<Entrepot[]> {
    const response = await this.client.get<{ entrepots: Entrepot[]; count: number }>('/entrepots');
    return response.data.entrepots;
  }

  async createEntrepot(entrepot: CreateEntrepotRequest): Promise<ApiResponse> {
    const response = await this.client.post<ApiResponse>('/entrepots', entrepot);
    return response.data;
  }

  async deleteEntrepot(entrepotId: string): Promise<ApiResponse> {
    const response = await this.client.delete<ApiResponse>(`/entrepots/${entrepotId}`);
    return response.data;
  }

  async batchDeleteEntrepots(entrepotIds: string[]): Promise<{
    success: boolean;
    message: string;
    results: Array<{ entrepot_id: string; success: boolean; message: string }>;
    succeeded_count: number;
    failed_count: number;
  }> {
    const response = await this.client.post('/entrepots/batch-delete', { entrepot_ids: entrepotIds });
    return response.data;
  }

  // Alias for consistency
  async getActiveEntrepots(): Promise<Entrepot[]> {
    return this.getEntrepots();
  }

  // --------------------------------------------------------------------------
  // Livraisons (Deliveries)
  // --------------------------------------------------------------------------

  async getLivraisons(): Promise<Livraison[]> {
    const response = await this.client.get<{ livraisons: Livraison[]; count: number }>('/livraisons');
    return response.data.livraisons;
  }

  async createLivraison(livraison: CreateLivraisonRequest): Promise<ApiResponse> {
    const response = await this.client.post<ApiResponse>('/livraisons', livraison);
    return response.data;
  }

  async deleteLivraison(livraisonId: string): Promise<ApiResponse> {
    const response = await this.client.delete<ApiResponse>(`/livraisons/${livraisonId}`);
    return response.data;
  }

  async batchDeleteLivraisons(livraisonIds: string[]): Promise<{
    success: boolean;
    message: string;
    results: Array<{ livraison_id: string; success: boolean; message: string }>;
    succeeded_count: number;
    failed_count: number;
  }> {
    const response = await this.client.post('/livraisons/batch-delete', { livraison_ids: livraisonIds });
    return response.data;
  }

  // Alias for consistency
  async getActiveLivraisons(): Promise<Livraison[]> {
    return this.getLivraisons();
  }
}

// Export singleton instance
export const api = new SimulationControlApi();
export default api;
