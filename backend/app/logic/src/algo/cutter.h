#ifndef CUTTER_H
#define CUTTER_H

#include "utils.h"
#include "utils/pool.h"
#include <stddef.h>

typedef struct {
    Pool item_pool;      // Item
    Pool delivery_pool;  // Delivery
    Pool warehouse_pool; // Warehouse
    Pool drone_pool; // Drone

    Pool archetype_pool; // Archetype
} Ctx;

extern Ctx ctx;

typedef struct {
    uint64_t id;
    const Item** items;
    size_t item_count;
    Position pos;
} Warehouse;

typedef struct {
    size_t* deliveries_darray;
    const Item* item;
} Archetype;

typedef struct {
    size_t* archetypes_darray;
    size_t warehouse_idx;
} Cluster;

Cluster* cut(size_t* out_cluster_count);

void add_warehouse(Warehouse wh);
void add_delivery(Delivery del);
void add_drone(Drone dr);

void init_cutter(void);

#endif /* ! CUTTER_H */
