import { Payload } from "./payload";
import { Position } from "./types";

export type Warehouse = {
    id: number;
    position: Position;
    payload: Payload;
}