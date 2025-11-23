#pragma once

#include <stdint.h>

// Structures

typedef struct Position {
	int32_t x;
	int32_t y;
	//int32_t z;
} Position;

typedef struct Item {
    uint64_t id;
	char *name;
	uint32_t mass;	// In grams
} Item;

typedef struct Delivery {
    uint64_t id;
	Item *item;
	uint16_t quantity;
	uint8_t priority;	// 0 -> Max priority | 5 -> Min priority : priority of the delivery
	uint8_t user; // 0 -> Max precedence | 5 -> Min precedence : if a delevery must be delivered before another one in the same trip
	Position position;
	uint32_t mass;		// In grams
} Delivery;

typedef struct Drone {
    uint64_t id;
	// Technical specifications
	uint32_t max_capacity;	// In grams
	uint8_t max_speed;		// In m/s
	uint8_t acceleration;	// In m/s²
	// Battery
	float energy;					// In Wh
	uint16_t max_flight_time;		// In s
	uint8_t max_flight_time_speed;	// In m/s

	// Operating characteristics
	uint32_t payload;	// In grams
	float autonomy;		// In Wh
	Position position;
	Delivery *targets;
	uint8_t nb_targets;

	// Algorithm internal attributes
	float cost;
} Drone;

typedef struct Route_constraint {
	Position center;
	uint32_t radius;
} Route_constraint;

// Functions

Item *new_item(char *name, uint32_t mass);

Delivery *new_delivery(Item *const item, const uint16_t quantity,
		const uint8_t priority, Position position, const uint32_t mass);

Drone *new_drone(const uint32_t max_capacity, const uint8_t max_speed,
		const uint8_t acceleration, const float energy,
		const uint16_t max_flight_time, const uint8_t max_flight_time_speed,
		const uint32_t payload, const float autonomy, Position position,
		Delivery *const targets, const uint8_t nb_targets, float cost);

uint32_t distance_2D(Position pos1, Position pos2);

float consumption(Drone *drone, uint32_t distance, uint8_t speed, uint32_t charge);

float can_handle(Drone *drone, uint8_t nb_deliveries, Delivery *deliveries[nb_deliveries], 
		uint8_t speed);

Position is_constrained(Route_constraint *cnst, const Position* pos1, const Position* pos2);
