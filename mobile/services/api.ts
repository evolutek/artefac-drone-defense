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

export interface SpawnDroneRequest {
  x?: number;
  y?: number;
  z?: number;
}

export interface CreateZoneRequest {
  name: string;
  type: 'jamming' | 'no-fly' | 'restricted';
  center: { x: number; y: number; z: number };
  radius: number;
}

export interface ApiResponse {
  success: boolean;
  message: string;
  drone_id?: string;
  drone_num?: number;
  zone_id?: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  active_drones_count: number;
  active_zones_count: number;
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
}

// Export singleton instance
export const api = new SimulationControlApi();
export default api;
