import { Position } from "./types";

export type Drone = {
    id: number;
    position: Position;
    max_weight: number;
    max_time_flight: number;
    speed: number;
    acceleration: number;
    total_battery_capacity: number;
}