export interface HealthStatus {
  status: string;
  timestamp: string;
  mqtt_connected: boolean;
  database: string;
  drones_connected: number;
}

export interface DroneStatus {
  id: number;
  drone_id: string;
  name: string | null;
  model: string;
  status: string;
  battery_level: number | null;
  latitude: number | null;
  longitude: number | null;
  altitude: number | null;
  position_x: number | null;
  position_y: number | null;
  position_z: number | null;
  is_armed: boolean;
  flight_mode: string | null;
  created_at: string;
  updated_at: string;
  last_heartbeat: string | null;
}

export interface TelemetryData {
  type: 'telemetry' | 'state';
  drone_id: string;
  data: {
    position_x?: number;
    position_y?: number;
    position_z?: number;
    latitude?: number;
    longitude?: number;
    altitude?: number;
    velocity_x?: number;
    velocity_y?: number;
    velocity_z?: number;
    orientation_x?: number;
    orientation_y?: number;
    orientation_z?: number;
    orientation_w?: number;
    battery?: number;
    connected?: boolean;
    armed?: boolean;
    mode?: string;
  };
}
