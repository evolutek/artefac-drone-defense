import { Position } from "./types";
import { Payload } from "./payload";

export type Delivery = {
    id: number;
    Position: Position;
    priority: number;
    user_priority: number;
    quantity: number;
    payload: Payload;
}