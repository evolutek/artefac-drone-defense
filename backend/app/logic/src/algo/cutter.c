#include "cutter.h"
#include "utils.h"
#include "utils/darray.h"
#include "utils/index.h"
#include "utils/pool.h"
#include <stdlib.h>
#include <string.h>

Ctx ctx;

#define DARRAY_FOR(var, array) for (size_t var = 0; var < darray_size(array); i++)

static ArchetypeIndex find_archetype(ItemIndex item) {

    pool_foreach2(&ctx.archetype_pool, Archetype, idx, arch) {
        if (INDEX_VALUE(arch->item) == INDEX_VALUE(item))
            return idx;
    }
    return MAKE_INDEX(Archetype, INVALID_INDEX);
}

static void unmark_unhandled_archetype(ArchetypeIndex to_remove) {
    DARRAY_FOR(i, &ctx.unhandled_archetypes) {
        ArchetypeIndex idx = ctx.unhandled_archetypes[i];
        if (INDEX_VALUE(idx) == INDEX_VALUE(to_remove)) {
            darray_remove(ctx.unhandled_archetypes, i, NULL);
            return;
        }
    }
}

static ClusterIndex find_cluster(WarehouseIndex wh_idx) {
    pool_foreach2(&ctx.cluster_pool, Cluster, cluster_idx, cluster) {
        if (INDEX_VALUE(cluster->warehouse_idx) == INDEX_VALUE(wh_idx))
            return cluster_idx;
    }
    return MAKE_INDEX(Cluster, INVALID_INDEX);
}

static void remove_delivery_from_archetype(DeliveryIndex del_idx, ArchetypeIndex arch_idx) {
    Archetype* arch = pool_query(&ctx.archetype_pool, arch_idx);

    DARRAY_FOR(i, arch->deliveries_darray) {
        if (INDEX_VALUE(arch->deliveries_darray[i]) == INDEX_VALUE(del_idx)) {
            darray_remove(arch->deliveries_darray, i, NULL);
            return;
        }
    }
}

ClusterIndex* cut(void) {

    decl_darray(dirty_clusters, ClusterIndex, 1);

    /*
      1. Parcourir les nouveaux entrepôts, créer un archétype par item de l'entrepôt (si
      inexistant).
         Associer les archétypes aux entrepôts, dans les clusters.
      2. Parcourir les nouvelles livraisons, les associer à un archétype.
         Si aucun archétype existant, en créer un nouveau dans la liste "invalide"
*/

    // First, pre-allocate every cluster for each warehouse.
    DARRAY_FOR(i, ctx.new_warehouses) {
        WarehouseIndex idx = ctx.new_warehouses[i];
        Warehouse* wh      = pool_query(&ctx.warehouse_pool, idx);
        Cluster cluster    = {
               .warehouse_idx     = idx,
               .archetypes_darray = darray_create(4, sizeof(ArchetypeIndex)),
        };

        for (size_t j = 0; j < wh->item_count; j++) {
            ItemIndex item          = wh->items[j];
            ArchetypeIndex arch_idx = find_archetype(item);
            // Create an archetype is one does not already exist.
            // Also add the found/created archetype to the current cluster.
            if (INDEX_VALUE(arch_idx) != INVALID_INDEX) {
                Archetype* arch = pool_query(&ctx.archetype_pool, arch_idx);
                // Mark "unhandled" archetypes as "handled" now!
                if (arch->ref_count == 0)
                    unmark_unhandled_archetype(arch_idx);
                arch->ref_count++;
                darray_add(cluster.archetypes_darray, arch_idx);
            }
            // Create a new empty archetype
            Archetype arch = {
                .item              = item,
                .deliveries_darray = darray_create(16, sizeof(DeliveryIndex)),
                .ref_count         = 1,
            };
            pool_add(&ctx.archetype_pool, Archetype, arch, arch_idx);
            darray_add(cluster.archetypes_darray, arch_idx);
        }
        ClusterIndex cluster_idx;
        pool_add(&ctx.cluster_pool, Cluster, cluster, cluster_idx);
        darray_add(dirty_clusters, cluster_idx);
    }

    // Add every new delivery to their corresponding archetype.
    DARRAY_FOR(i, ctx.new_deliveries) {
        DeliveryIndex del_idx = ctx.new_deliveries[i];
        Delivery* del         = pool_query(&ctx.delivery_pool, del_idx);

        ArchetypeIndex arch_idx = find_archetype(del->item);
        Archetype* arch;
        if (INDEX_VALUE(arch_idx) == INVALID_INDEX) {
            // No archetype exists for this item, delivery cannot be handled.
            Archetype new_arch = {
                .item              = del->item,
                .deliveries_darray = darray_create(16, sizeof(DeliveryIndex)),
            };
            pool_add(&ctx.archetype_pool, Archetype, new_arch, arch_idx);
            arch = pool_query(&ctx.archetype_pool, arch_idx);
            darray_add(ctx.unhandled_archetypes, arch_idx);
        } else {
            arch      = pool_query(&ctx.archetype_pool, arch_idx);
        }
        darray_add(arch->deliveries_darray, del_idx);
    }

    return dirty_clusters;
}

void add_warehouse(Warehouse wh) {
    WarehouseIndex idx;
    pool_add(&ctx.warehouse_pool, Warehouse, wh, idx);
    darray_add(ctx.new_warehouses, idx);
}
void add_delivery(Delivery del) {
    DeliveryIndex idx;
    pool_add(&ctx.delivery_pool, Delivery, del, idx);
    darray_add(ctx.new_deliveries, idx);
}
void add_item(Item item) {
    pool_add(&ctx.item_pool, Item, item);
}
void remove_warehouse(WarehouseIndex idx) {
    ClusterIndex cluster_idx = find_cluster(idx);
    Cluster* cluster         = pool_query(&ctx.cluster_pool, cluster_idx);

    for (size_t i = 0; i < darray_size(cluster->archetypes_darray); i++) {
        ArchetypeIndex arch_idx = cluster->archetypes_darray[i];
        Archetype* arch         = pool_query(&ctx.archetype_pool, arch_idx);
        arch->ref_count--;
        if (arch->ref_count == 0)
            darray_add(ctx.unhandled_archetypes, arch_idx);
    }
}
void remove_delivery(DeliveryIndex idx) {
    Delivery* del           = pool_query(&ctx.delivery_pool, idx);
    ArchetypeIndex arch_idx = find_archetype(del->item);
    remove_delivery_from_archetype(idx, arch_idx);
}
void add_drone(Drone dr) {
    pool_add(&ctx.drone_pool, Drone, dr);
}
