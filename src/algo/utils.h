#pragma once

#include <stdint.h>

// Structures

typedef struct Position {
	uint32_t x;
	uint32_t y;
	uint32_t z;
} Position;

typedef struct Item {
	char *name;
	uint32_t mass;	// In grams
} Item;

typedef struct Delivery {
	Item *items;
	uint16_t quantity;
	uint8_t priority;	// 0 -> Max priority | 5 -> Min priority
	Position *position;
	uint32_t mass;		// In grams
} Delivery;

typedef struct Drone {
	// Technical specifications
	uint32_t max_capacity;	// In grams
	uint8_t max_speed;		// In m/s
	uint8_t acceleration;	// In m/s²
	// Battery
	uint16_t energy;				// In Wh
	uint16_t max_flight_time;		// In minutes
	uint16_t max_flight_time_speed;	// In km/h

	// Operating characteristics
	uint32_t payload;	// In grams
	uint16_t autonomy;	// In Wh
	Position *position;
	Delivery **targets;
	uint8_t nb_targets;

	// Algorithm internal attributes
	float cost;
} Drone;

// Functions

Position *new_position(uint32_t x, uint32_t y, uint32_t z);

Item *new_item(char *name, uint32_t mass);

Delivery *new_delivery(Item *const items, const uint16_t quantity,
		const uint8_t priority, Position *const position, const uint32_t mass);

Drone *new_drone(const uint32_t max_capacity, const uint8_t max_speed,
		const uint8_t acceleration, const uint16_t energy,
		const uint16_t max_flight_time, const uint16_t max_flight_time_speed,
		const uint32_t payload, const uint16_t autonomy, Position *const position,
		Delivery **const targets,
		const uint8_t nb_targets, float cost);

uint32_t distance(const Position *pos1, const Position *pos2);

float weight(struct Drone* drone, struct Delivery* delivery, uint32_t pre_calculated_dist);

int add_target(struct Drone* drone, struct Delivery* delivery);

int can_handle_delivery(struct Drone* drone, struct Delivery* delivery);