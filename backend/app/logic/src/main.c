#include "interface/interface.h"
#include "algo/utils.h"
#include "algo/cutter.h"
#include "algo/graph.h"
#include "utils/darray.h"
#include "utils/pool.h"
#include "algo/graph.h"
#include "algo/path.h"

#include <stdio.h>
#include <stdlib.h>

/*
// For init_test
//#define ITEM_COUNT 200
//#define WH_COUNT 5
//#define DEL_COUNT 4000
static ItemIndex items[ITEM_COUNT];

size_t rand_index(size_t max) {
#define RANDOM_MAX ((1LL << 31) - 1)
    long x = random();
    return x * max / RANDOM_MAX;
}

void init_test() {
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



void init_context(void);

*/


Ctx ctx;

void init_context(void) {
    pool_init(&ctx.item_pool, 16, sizeof(Item));
    pool_init(&ctx.delivery_pool, 16, sizeof(Delivery));
    pool_init(&ctx.warehouse_pool, 16, sizeof(Warehouse));
    pool_init(&ctx.drone_pool, 16, sizeof(Drone));
    pool_init(&ctx.archetype_pool, 16, sizeof(Archetype));
    pool_init(&ctx.cluster_pool, 16, sizeof(Cluster));
    pool_init(&ctx.node_pool, 64, sizeof(Node));
	pool_init(&ctx.edge_pool, 256, sizeof(Edge));

    ctx.new_warehouses = darray_create(4, sizeof *ctx.new_warehouses);
    ctx.new_deliveries = darray_create(4, sizeof *ctx.new_deliveries);
    ctx.unhandled_archetypes = darray_create(4, sizeof *ctx.unhandled_archetypes);
}


int main(void) {
	// INTERFACE
    puts("==== INTERFACE ====");
    if(init_shared_mem())
        interface_handle();
    puts("===================");

    init_context();
    //srandom(0);
    //init();

	// CUTS
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
