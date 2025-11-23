#include "cutter.h"
#include "utils.h"
#include "utils/darray.h"
#include "utils/pool.h"
#include <stdlib.h>
#include <string.h>

typedef struct {
    Item* item;
    size_t count;
} ItemStack;

static Ctx ctx;

struct archetype_search_data {
    ssize_t archetype_idx;
    const Item* item;
};

static bool find_archetype_loop(const void* obj, size_t idx, void* data) {
    const Archetype* arch                     = obj;
    struct archetype_search_data* search_data = data;

    if (arch->item == search_data->item) {
        search_data->archetype_idx = idx;
        return false;
    }
    return true;
}

static ssize_t find_archetype(Pool* archetype_pool, const Item* item) {
    struct archetype_search_data data = {
        .item          = item,
        .archetype_idx = -1,
    };

    pool_foreach(archetype_pool, find_archetype_loop, &data);

    return data.archetype_idx;
}

static bool categorize_delivery(const void* obj, size_t idx, void* data) {
    (void) idx;
    (void) data;
    const Delivery* delivery = obj;

    ssize_t archetype_idx = find_archetype(&ctx.archetype_pool, delivery->item);
    Archetype* arch;
    if (archetype_idx == -1) {
        arch  = pool_alloc(&ctx.archetype_pool, NULL);
        *arch = (Archetype) {
            .item              = delivery->item,
            .deliveries_darray = darray_create(4, sizeof(size_t)),
        };
    } else {
        arch = pool_query(&ctx.archetype_pool, archetype_idx);
    }
    size_t* idx_ptr = pool_alloc(&ctx.archetype_pool, NULL);
    *idx_ptr = idx;
    return true;
}

static void generate_archetypes(void) {
    pool_foreach(&ctx.delivery_pool, categorize_delivery, NULL);
}

bool is_item_in_warehouse(const Item* item, const Item* const* items, size_t item_count) {
    for (size_t i = 0; i < item_count; i++) {
        if (items[i] == item)
            return true;
    }
    return false;
}

struct archetype_dispatch_data {
    size_t** cluster_archetype_darray;
    const Item** warehouse_items;
    size_t warehouse_item_count;
};

static bool dispatch_archetype(const void* obj, size_t idx, void* user_data) {
    const Archetype* arch = obj;

    struct archetype_dispatch_data* data = user_data;

    if (is_item_in_warehouse(arch->item, data->warehouse_items, data->warehouse_item_count))
        darray_add(*data->cluster_archetype_darray, idx);

    return true;
}

struct cluter_dispatch_data {
    Cluster* clusters;
    size_t cluster_idx;
};

static bool dispatch_archetypes(const void* obj, size_t idx, void* user_data) {
    const Warehouse* wh = obj;

    struct cluter_dispatch_data* super_data = user_data;

    super_data->clusters[super_data->cluster_idx] = (Cluster) {
        .warehouse_idx     = idx,
        .archetypes_darray = darray_create(4, sizeof(size_t)),
    };

    struct archetype_dispatch_data data = {
        .cluster_archetype_darray = &super_data->clusters[super_data->cluster_idx].archetypes_darray,
        .warehouse_items          = wh->items,
        .warehouse_item_count     = wh->item_count,
    };
    pool_foreach(&ctx.archetype_pool, dispatch_archetype, &data);

    super_data->cluster_idx++;

    return true;
}

Cluster* cut(size_t* out_cluster_count) {
    generate_archetypes();

    size_t cluster_size = ctx.warehouse_pool.size;
    Cluster* clusters   = calloc(cluster_size, sizeof *clusters);

    struct cluter_dispatch_data data = {
        .clusters    = clusters,
        .cluster_idx = 0,
    };
    pool_foreach(&ctx.warehouse_pool, dispatch_archetypes, &data);
    *out_cluster_count = cluster_size;

    return clusters;
}

void add_warehouse(Warehouse wh) {
    pool_add(&ctx.warehouse_pool, wh, NULL);
}
void add_delivery(Delivery del) {
    pool_add(&ctx.delivery_pool, del, NULL);
}

void init_cutter(void) {
    pool_init(&ctx.delivery_pool, 16, sizeof(Delivery));
    pool_init(&ctx.warehouse_pool, 16, sizeof(Warehouse));
    pool_init(&ctx.archetype_pool, 16, sizeof(Archetype));
}
