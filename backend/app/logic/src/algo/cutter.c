#include "cutter.h"
#include "utils.h"
#include "utils/darray.h"
#include <stdlib.h>
#include <string.h>

typedef struct {
    Item* item;
    size_t count;
} ItemStack;

typedef struct {
    Delivery* deliveries_darray;
    Warehouse* warehouses_darray;
    Drone* drones_darray;
} Ctx;

static Ctx ctx;

typedef struct {
    Delivery** deliveries_darray;
    const Item* item;
} Archetype;

static Archetype* generate_archetypes(void) {
    size_t delivery_count = darray_size(ctx.deliveries_darray);

    decl_darray(archetypes, Archetype, 2);

    for (size_t i = 0; i < delivery_count; i++) {
        Delivery* delivery     = &ctx.deliveries_darray[i];
        size_t archetype_count = darray_size(archetypes);
        bool found_archetype   = false;
        for (size_t j = 0; j < archetype_count; j++) {
            Archetype* arch = &archetypes[i];
            if (arch->item == delivery->items) {
                // Add delivery to archetype
                darray_add(arch->deliveries_darray, delivery);
                found_archetype = true;
                break;
            }
        }
        if (!found_archetype) {
            Archetype new_arch = {
                .item              = delivery->items,
                .deliveries_darray = darray_create(4, sizeof(Delivery*)),
            };
            darray_add(new_arch.deliveries_darray, delivery);
            darray_add(archetypes, new_arch);
        }
    }

    return archetypes;
}

bool is_item_in_warehouse(const Item* item, const Item* const* items, size_t item_count) {
    for (size_t i = 0; i < item_count; i++) {
        if (items[i] == item)
            return true;
    }
    return false;
}

Cluster* cut(size_t* out_cluster_count) {
    Archetype* archetypes  = generate_archetypes();
    size_t archetype_count = darray_size(archetypes);

    size_t cluster_size = darray_size(ctx.warehouses_darray);
    Cluster* clusters   = calloc(cluster_size, sizeof *clusters);

    for (size_t i = 0; i < cluster_size; i++) {
        Warehouse* wh                 = &ctx.warehouses_darray[i];
        Cluster* cluster              = &clusters[i];
        Delivery** cluster_deliveries = darray_create(16, sizeof *cluster_deliveries);
        for (size_t j = 0; j < archetype_count; j++) {
            Archetype* arch = &archetypes[j];
            if (is_item_in_warehouse(arch->item, wh->items, wh->item_count)) {
                for (size_t k = 0; k < darray_size(arch->deliveries_darray); k++) {
                    darray_add(cluster_deliveries, arch->deliveries_darray[k]);
                }
            }
        }
        *cluster = (Cluster) {
            .warehouse      = wh,
            .deliveries     = malloc(darray_size(cluster_deliveries) * sizeof(Delivery*)),
            .delivery_count = darray_size(cluster_deliveries),
        };
        memcpy(cluster->deliveries, cluster_deliveries, darray_size(cluster_deliveries));
    }

    *out_cluster_count = cluster_size;

    return clusters;
}

void add_warehouse(Warehouse wh) {
  darray_add(ctx.warehouses_darray, wh);
}
void add_delivery(Delivery del) {
  darray_add(ctx.deliveries_darray, del);
}

void init_cutter(void) {
  ctx.deliveries_darray = darray_create(16, sizeof(Delivery));
  ctx.warehouses_darray = darray_create(16, sizeof(Delivery));
}
