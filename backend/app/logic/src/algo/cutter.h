#ifndef CUTTER_H
#define CUTTER_H

#include "utils.h"
#include <stddef.h>

typedef struct {
    DeliveryIndex* deliveries_darray;
    ItemIndex item;
    size_t ref_count;
} Archetype;

typedef struct {
    ArchetypeIndex* archetypes_darray;
    WarehouseIndex warehouse_idx;
    NodeIndex graph_root;
} Cluster;

ClusterIndex* cut(void);

void add_warehouse(Warehouse wh);
void add_delivery(Delivery del);
void add_drone(Drone dr);
void add_item(Item item);

void remove_warehouse(WarehouseIndex idx);
void remove_delivery(DeliveryIndex idx);
void remove_drone(DroneIndex idx);
void remove_item(ItemIndex idx);

#endif /* ! CUTTER_H */
