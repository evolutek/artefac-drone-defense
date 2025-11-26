import { Payload } from "./payload";
import { Position } from "./types";

export type Mission = {
    id: number;
    drone_id: number;
    waypoints: Array<[Position, mode: number]>;
    payload: Payload;
}