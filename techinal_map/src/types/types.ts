export type DroneTelemetry = {
  drone_id: string;
  timestamp: string;
  lat: number;
  lon: number;
  altitude?: number;
  speed?: number;
  heading?: number;
  battery_level?: number;
  status?: 'idle' | 'armed' | 'mission' | 'returning' | 'error';
};

export type TelemetryMessage = {
  type: 'telemetry';
  data: DroneTelemetry;
};

export type StateUpdateMessage = {
  type: 'state_update';
  data: any;
};

export type WSMessage = TelemetryMessage | StateUpdateMessage | { type: string; data?: any };

export type MissionWaypoint = { lat: number; lon: number; altitude?: number };
export type MissionCreate = {
  drone_id: string;
  mission_type: string;
  waypoints: MissionWaypoint[];
  priority?: number;
  note?: string;
};

export type Position = {
    latitude: number;
    longitude: number;
    altitude: number;
}
