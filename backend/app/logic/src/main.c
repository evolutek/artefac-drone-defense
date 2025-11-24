#include "algo/cutter.h"
#include "algo/utils.h"
#include "interface/interface.h"
#include "utils/darray.h"
#include "utils/pool.h"
#include <stdio.h>
#include <stdlib.h>

#define ITEM_COUNT 200
#define WH_COUNT 5
#define DEL_COUNT 4000

static ItemIndex items[ITEM_COUNT];

size_t rand_index(size_t max) {
#define RANDOM_MAX ((1LL << 31) - 1)
    long x = random();
    return x * max / RANDOM_MAX;
}

void init() {
    for (size_t i = 0; i < ITEM_COUNT; i++) {
        char* name = malloc(512);
        snprintf(name, 512, "%zu", i);
        Item item = {
            .mass = i,
            .name = name,
        };
        pool_add(&ctx.item_pool, Item, item, items[i]);
    }

    for (size_t i = 0; i < WH_COUNT; i++) {
        size_t item_count = rand_index(ITEM_COUNT / 10) + 1;
        Warehouse wh      = {
                 .pos        = {i + 1, i * 2},
                 .item_count = item_count,
                 .items      = malloc(item_count * sizeof(ItemIndex)),
        };

        for (size_t j = 0; j < item_count; j++) {
            wh.items[j] = items[rand_index(ITEM_COUNT)];
        }
        add_warehouse(wh);
    }

    for (size_t i = 0; i < DEL_COUNT; i++) {
        Delivery del = {
            .position = {i / 3 - 5, i * 1.7 + 8},
            .priority = rand_index(100),
            .item     = items[rand_index(ITEM_COUNT)],
            .quantity = 1,
        };
        add_delivery(del);
    }
}

float weight(Position pos, Delivery* del) {
    uint32_t distance = distance_2D(pos, del->position);
    (void) distance;
    return 0;
}

int main() {

    puts("==== INTERFACE ====");
    if(init_shared_mem())
        interface_handle();
    puts("===================");

    srandom(0);
    init_cutter();
    init();

    printf("Cutting!\n");
    ClusterIndex* clusters = cut();
    size_t cluster_count = darray_size(clusters);

    printf("Cluster count: %zu\n", cluster_count);

    for (size_t i = 0; i < cluster_count; i++) {
        Cluster* cluster = pool_query(&ctx.cluster_pool, clusters[i]);
        printf("Cluster %zu:\n", i);
        printf("  Archetype count: %zu\n", darray_size(cluster->archetypes_darray));
    }

    darray_destroy(clusters);

    pool_cleanup(&ctx.item_pool);
    pool_cleanup(&ctx.warehouse_pool);
    pool_cleanup(&ctx.delivery_pool);
    pool_cleanup(&ctx.archetype_pool);
    pool_cleanup(&ctx.cluster_pool);
    pool_cleanup(&ctx.drone_pool);

    darray_destroy(ctx.new_deliveries);
    darray_destroy(ctx.new_warehouses);
    darray_destroy(ctx.unhandled_archetypes);


    return 0;
}
