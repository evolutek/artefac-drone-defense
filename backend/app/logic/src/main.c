#include "algo/cutter.h"
#include "algo/utils.h"
#include "interface/interface.h"
#include "utils/darray.h"
#include <stdio.h>
#include <stdlib.h>

#define ITEM_COUNT 200
#define WH_COUNT 5
#define DEL_COUNT 4000

static Item items[ITEM_COUNT];

size_t rand_index(size_t max) {
#define RANDOM_MAX ((1LL << 31) - 1)
    long x = random();
    return x * max / RANDOM_MAX;
}

void init() {
    for (size_t i = 0; i < ITEM_COUNT; i++) {
        char* name = malloc(512);
        snprintf(name, 512, "%zu", i);
        items[i] = (Item) {
            .mass = i,
            .name = name,
        };
    }

    for (size_t i = 0; i < WH_COUNT; i++) {
        size_t item_count = rand_index(ITEM_COUNT / 10) + 1;
        Warehouse wh      = {
                 .pos        = {i + 1, i * 2, i * i},
                 .item_count = item_count,
                 .items      = malloc(item_count * sizeof(Item*)),
        };

        for (size_t j = 0; j < item_count; j++) {
            wh.items[j] = &items[rand_index(ITEM_COUNT)];
        }
        add_warehouse(wh);
    }

    for (size_t i = 0; i < DEL_COUNT; i++) {
        Delivery del = {
            .position = {i / 3 - 5, i * 1.7 + 8, i * i / 4},
            .priority = rand_index(100),
            .item     = &items[rand_index(ITEM_COUNT)],
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

void gab_test(void) {
    // ~DJI Mavic 4 Pro : https://www.dji.com/nl/mavic-4-pro/specs
    Drone* drone = new_drone(100, 0, 0, 95.3, 51 * 60, 32 / 3.6, 0, 0, (Position) {0}, NULL, 0, 0);
    (void) drone;

    Route_constraint c = {
        .center = {30, 20, 0},
        .radius = 16,
    };
    Position p1 = {50, 60, 0};
    Position p2 = {-10, 0, 0};
    Position p  = is_constrained(&c, &p1, &p2);

    printf("x: %u\ny: %u\n", p.x, p.y);
}

int main() {

    puts("==== INTERFACE ====");
    init_shared_mem();
    interface_handle();
    puts("===================");

    puts("==== GAB TEST ====");
    gab_test();
    puts("==================");

    srandom(0);
    init_cutter();
    init();

    size_t cluster_count;
    printf("Cutting!\n");
    Cluster* clusters = cut(&cluster_count);

    printf("Cluster count: %zu\n", cluster_count);

    for (size_t i = 0; i < cluster_count; i++) {
        Cluster* cluster = &clusters[i];
        printf("Cluster %zu:\n", i);
        printf("  Archetype count: %zu\n", darray_size(cluster->archetypes_darray));
    }

    return 0;
}
