#include "interface/interface.h"
#include "algo/utils.h"
#include "algo/cutter.h"
#include "algo/graph.h"
#include "utils/darray.h"
#include "utils/pool.h"

#include <setjmp.h>
#include <stdio.h>
#include <stdlib.h>

#include <pthread.h>

#define ITEM_COUNT 200
#define WH_COUNT 5
#define DEL_COUNT 4000

/*
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
*/


void init_context(void) {
    pool_init(&ctx.item_pool, 16, sizeof(Item));
    pool_init(&ctx.delivery_pool, 16, sizeof(Delivery));
    pool_init(&ctx.warehouse_pool, 16, sizeof(Warehouse));
    pool_init(&ctx.drone_pool, 16, sizeof(Drone));
    pool_init(&ctx.archetype_pool, 16, sizeof(Archetype));
    pool_init(&ctx.cluster_pool, 16, sizeof(Cluster));
    pool_init(&ctx.node_pool, 16, sizeof(Node));

    ctx.new_warehouses = darray_create(4, sizeof *ctx.new_warehouses);
    ctx.new_deliveries = darray_create(4, sizeof *ctx.new_deliveries);
    ctx.unhandled_archetypes = darray_create(4, sizeof *ctx.unhandled_archetypes);

    pthread_cond_init(&ctx.compute_ready_var, NULL);
    pthread_mutex_init(&ctx.pool_mutex, NULL);
    ctx.main_thread = pthread_self();
}

void cleanup_context(void) {
    pthread_mutex_destroy(&ctx.pool_mutex);
    pthread_cond_destroy(&ctx.compute_ready_var);

    pool_cleanup(&ctx.item_pool);
    pool_cleanup(&ctx.warehouse_pool);
    pool_cleanup(&ctx.delivery_pool);
    pool_cleanup(&ctx.archetype_pool);
    pool_cleanup(&ctx.cluster_pool);
    pool_cleanup(&ctx.drone_pool);

    darray_destroy(ctx.new_deliveries);
    darray_destroy(ctx.new_warehouses);
    darray_destroy(ctx.unhandled_archetypes);
}    

/*
void test_clustering(void) {
    srandom(0);
    init_context();
    //init();

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
}

int repart_test(void) {
    // Création de deux drones
    struct Position position_drone = {.x = 0, .y = -1};
    struct Drone* drone            = malloc(sizeof(*drone));
    *drone                         = (struct Drone) {0,
                                                     1000,
                                                     100,
                                                     100,
                                                     100,
                                                     100.0f,
                                                     100,
                                                     100,
                                                     100,
                                                     position_drone,
                                                     darray_create(10, sizeof(struct Delivery*)),
                                                     0};

    struct Position position_drone2 = {.x = -10, .y = -1};
    struct Drone* drone2            = malloc(sizeof(*drone2));
    *drone2                         = (struct Drone) {0,
                                                      1000,
                                                      100,
                                                      100,
                                                      100,
                                                      100.0f,
                                                      100,
                                                      100,
                                                      100,
                                                      position_drone2,
                                                      darray_create(10, sizeof(struct Delivery*)),
                                                      0};

    Drone** array_drones = darray_create(10, sizeof(Drone*));
    darray_add(array_drones, drone);
    darray_add(array_drones, drone2);

    // === Deliveries ===
    struct Delivery* delivery2 = malloc(sizeof(*delivery2));
    delivery2->id              = 1;
    delivery2->position        = (struct Position) {2, 2};
    delivery2->user_priority   = 1;
    delivery2->mass            = 10;

    Node* node1             = malloc(sizeof(*node1));
    node1->content.delivery = delivery2;
    node1->type             = E_DELIVERY;
    node1->nb_edges         = 0;
    node1->edges            = NULL;

    struct Delivery* delivery3 = malloc(sizeof(*delivery3));
    delivery3->id              = 2;
    delivery3->position        = (struct Position) {0, 2};
    delivery3->user_priority   = 1;
    delivery3->mass            = 10;

    Node* node2             = malloc(sizeof(*node2));
    node2->content.delivery = delivery3;
    node2->type             = E_DELIVERY;
    node2->nb_edges         = 0;
    node2->edges            = NULL;

    struct Delivery* delivery4 = malloc(sizeof(*delivery4));
    delivery4->id              = 3;
    delivery4->position        = (struct Position) {-2, 2};
    delivery4->user_priority   = 1;
    delivery4->mass            = 10;

    Node* node3             = malloc(sizeof(*node3));
    node3->content.delivery = delivery4;
    node3->type             = E_DELIVERY;
    node3->nb_edges         = 0;
    node3->edges            = NULL;

    Node* node4             = malloc(sizeof(*node4));
    node4->content.delivery = delivery3;
    node4->type             = E_DELIVERY;
    node4->nb_edges         = 0;
    node4->edges            = NULL;

    // === Warehouses ===
    Warehouse* warehouse  = malloc(sizeof(Warehouse));
    warehouse->id         = 0;
    warehouse->pos        = (struct Position) {0, 0};
    warehouse->item_count = 1;

    Node* wnode1              = malloc(sizeof(*wnode1));
    wnode1->content.warehouse = warehouse;
    wnode1->type              = E_WAREHOUSE;
    wnode1->edges             = NULL;
    wnode1->nb_edges          = 0;

    Warehouse* warehouse1  = malloc(sizeof(Warehouse));
    warehouse1->id         = 1;
    warehouse1->pos        = (struct Position) {-10, 0};
    warehouse1->item_count = 1;

    Node* wnode2              = malloc(sizeof(*wnode2));
    wnode2->content.warehouse = warehouse1;
    wnode2->type              = E_WAREHOUSE;
    wnode2->edges             = NULL;
    wnode2->nb_edges          = 0;

    // === Edges (simplifiés) ===
    Edge* array_wh1   = calloc(2, sizeof(Edge));
    array_wh1[0].cost = 1;
    array_wh1[0].next = node1;
    array_wh1[1].cost = 1;
    array_wh1[1].next = node2;
    wnode1->edges     = array_wh1;
    wnode1->nb_edges  = 2;

    Edge* array_wh2   = calloc(2, sizeof(Edge));
    array_wh2[0].cost = 1;
    array_wh2[0].next = node2;
    array_wh2[1].cost = 1;
    array_wh2[1].next = node3;
    wnode2->edges     = array_wh2;
    wnode2->nb_edges  = 2;

    Edge* array_l1   = calloc(1, sizeof(Edge));
    array_l1[0].cost = 1;
    array_l1[0].next = node2;
    node1->edges     = array_l1;
    node1->nb_edges  = 1;

    Edge* array_l2   = calloc(1, sizeof(Edge));
    array_l2[0].cost = 1;
    array_l2[0].next = node1;
    node2->edges     = array_l2;
    node2->nb_edges  = 1;

    Edge* array_l3   = calloc(1, sizeof(Edge));
    array_l3[0].cost = 1;
    array_l3[0].next = node4;
    node3->edges     = array_l3;
    node3->nb_edges  = 1;

    Edge* array_l4   = calloc(1, sizeof(Edge));
    array_l4[0].cost = 1;
    array_l4[0].next = node3;
    node4->edges     = array_l4;
    node4->nb_edges  = 1;

    // === Deliveries list ===
    Node** array_deliveries = darray_create(10, sizeof(Node*));
    darray_add(array_deliveries, wnode1);
    darray_add(array_deliveries, wnode2);

    printf("%zu\n", darray_size(array_deliveries));

    // === Call algorithm ===
    Node*** result =
        choose_drone_naive(array_drones, array_deliveries, darray_size(array_deliveries));

    // === Display result ===
    if (result != NULL) {
        printf("%zu\n", darray_size(result));
        for (size_t i = 0; i < darray_size(result); i++) {
            printf("\t%zu\n", darray_size(result[i]));
            for (size_t j = 0; j < darray_size(result[i]); j++) {
                if (result[i][j] && result[i][j]->type == E_DELIVERY)
                    printf("\t(delivery at %d,%d)\n",
                           result[i][j]->content.delivery->position.x,
                           result[i][j]->content.delivery->position.y);
            }
            printf("\n");
        }
    }

    // free_darray_matrice((void**)result);

    // === Free ===

    free(array_wh1);
    free(array_wh2);

    if (result)
        free_darray_matrice((void**) result);

    darray_clear(array_deliveries);
    darray_destroy(array_deliveries);

    darray_clear(array_drones);
    darray_destroy(array_drones);

    free(node1);
    free(node2);
    free(node3);
    free(node4);
    free(wnode1);
    free(wnode2);

    free(delivery2);
    free(delivery3);
    free(delivery4);

    free(warehouse);
    free(warehouse1);

    printf("end\n");
    return 0;
}
    */

void usr1_handler(int sig) {
    (void)sig;
    siglongjmp(ctx.restart_point, 1);
}

int main(void) {
    init_context();
    init_interface();

    if (sigsetjmp(ctx.restart_point, 1) != 0) {
        pthread_mutex_unlock(&ctx.pool_mutex);
        pthread_mutex_lock(&ctx.pool_mutex);
        pthread_cond_wait(&ctx.compute_ready_var, &ctx.pool_mutex);
        // Recompute needed, discard
        //ClusterIndex* dirty_cluster_indices = cut();
    }

    // Wave compute

    stop_interface();
    cleanup_context();
    return 0;
}
