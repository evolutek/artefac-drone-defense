#pragma once

#include <stdint.h>
#include "utils/pool.h"
#include "utils/index.h"
#include <pthread.h>
#include <setjmp.h>

typedef struct Node Node;

#define MIN_PRIORITY 5

// Structures

DEFINE_INDEX(Drone);
DEFINE_INDEX(Item);
DEFINE_INDEX(Warehouse);
DEFINE_INDEX(Delivery);
DEFINE_INDEX(Archetype);
DEFINE_INDEX(Cluster);
DEFINE_INDEX(ExclusionZone);

typedef struct {
    /*
      These pools hold all objects used by the algorithm.
      All references to these objects should use indices of slots inside those pools instead of
      pointers.
      */
    Pool item_pool;      // Item
    Pool delivery_pool;  // Delivery
    Pool warehouse_pool; // Warehouse
    Pool drone_pool;     // Drone
    Pool exclusion_zone_pool;     // Drone

    Pool archetype_pool; // Archetype
    Pool cluster_pool;   // Cluster
	Pool node_pool; 	 // Node

    WarehouseIndex* new_warehouses;
    DeliveryIndex* new_deliveries;
    DroneIndex* new_drones;
    ArchetypeIndex* unhandled_archetypes;

    pthread_mutex_t pool_mutex;
    sigjmp_buf restart_point;
    pthread_t main_thread;
    pthread_cond_t compute_ready_var;
} Ctx;

typedef struct Position {
	int32_t x;
	int32_t y;
	//int32_t z;
} Position;

typedef struct Item {
    uint64_t id;
	const char *name;
	uint32_t mass;	// In grams
} Item;

typedef struct Delivery {
    uint64_t id;
	ItemIndex item;
	uint16_t quantity;
	float priority;	// 0 -> Max priority | 5 -> Min priority : priority of the delivery
	uint8_t user_priority; // 0 -> Max user priority | 5 -> Min user priority : if a delevery must be delivered before another one in the same trip
	Position position;
	uint32_t mass;		// In grams
	
	// Algorithm internal attributes
	Node *node;
	uint8_t mark;
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
} Drone;

typedef struct {
    uint64_t id;
    ItemIndex* items;
    size_t item_count;
    Position pos;
} Warehouse;


typedef struct {
	Position center;
	uint32_t radius;
} ExclusionZone;

typedef struct Detour {
	uint32_t distance;
	Position pos;
} Detour;

extern Ctx ctx;

// Functions

uint32_t distance_2D(Position pos1, Position pos2);

float consumption(Drone *drone, uint32_t distance, uint8_t speed, uint32_t charge);

float can_handle(Drone *drone, uint8_t nb_deliveries, Node *deliveries[nb_deliveries], 
		uint8_t speed);

bool is_constrained(ExclusionZone *cnst, const Position* pos1, const Position* pos2, Detour* out_detour);
