#include "utils.h"
#include "graph.h"
#include "utils/darray.h"
#include "utils/pool.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdlib.h>

float distance_2D(Position pos1, Position pos2) {
    float dx = pos2.x - pos1.x;
    float dy = pos2.y - pos1.y;
    return sqrtf(dx * dx + dy * dy);
}

// distance in m, speed in m/s, charge in g
// Calculate the estimate consumption in Wh with the following formula :
// (distance * speed / max_flight_time * max_flight_time_speed * max_flight_time_speed) * energy
// 		+ (charge / max_capacity) * (energy / 2)
// Indeed :
// 		consumption(drone, max_flight_time * max_flight_time_speed, max_flight_time_speed,
// 0) = energy 		consumption(drone, 0, speed, charge) = 0 		consumption(drone,
// distance, 0, charge) = 0 O consumption means that the drone can't flight under the current
// conditions
float consumption(Drone* drone, float distance, uint8_t speed, uint32_t charge) {
    float f1 = distance * speed;
    float f2 = drone->max_flight_time * drone->max_flight_time_speed * drone->max_flight_time_speed;
    float f3 = drone->max_capacity * 2;
    return distance && speed && drone->max_capacity ? (f1 / f2 + charge / f3) * drone->energy : 0;
}

// TODO: Add return to base
// Return the remaining autonomy of the drone after delivering or
// a negative value if it can not be delivered.
// nb_deliveries must be strictly higher than 0
float can_handle(Drone* drone,
                 uint8_t nb_deliveries,
                 NodeIndex deliveries[nb_deliveries],
                 uint8_t speed,
                 NodeIndex* warehouses) {
    uint32_t distance, payload;
    payload    = 0;
    float cons = 0;

    float min_dist = -1;
    Node* last     = pool_query(&ctx.node_pool, deliveries[nb_deliveries - 1]);
    for (size_t i = 0; i < darray_size(warehouses); i++) {
        Node* wh   = pool_query(&ctx.node_pool, warehouses[i]);
        float dist = distance_2D(last->content.delivery->position, wh->content.warehouse->pos);
        if (min_dist == -1 || dist < min_dist) {
            min_dist = dist;
        }
    }
    cons += consumption(drone, min_dist, speed, 0);

    while (--nb_deliveries && cons < drone->autonomy && payload < drone->max_capacity) {
        Node* n = pool_query(&ctx.node_pool, deliveries[nb_deliveries]);
        Node* p = pool_query(&ctx.node_pool, deliveries[nb_deliveries - 1]);
        payload += n->content.delivery->mass;
        distance = distance_2D(n->content.delivery->position, p->content.delivery->position);
        cons += consumption(drone, distance, speed, payload);
    }

    Node* first = pool_query(&ctx.node_pool, deliveries[0]);
    payload += first->content.delivery->mass;

    if (drone->autonomy <= cons || drone->max_capacity < payload)
        return -1;

    distance = distance_2D(drone->final_position, first->content.delivery->position);
    cons += consumption(drone, distance, speed, payload);

    return drone->autonomy - cons;
}
/*
float can_handle(Drone* drone,
                 uint8_t nb_deliveries,
                 NodeIndex deliveries[nb_deliveries],
                 uint8_t speed,
                 NodeIndex* warehouses) {
    assert(nb_deliveries > 0);
    uint32_t distance, payload;
    payload    = 0;
    float cons = 0;

    float min_dist = -1;
    for (size_t i = 0; i < darray_size(warehouses); i++) {
        Node* del = pool_query(&ctx.node_pool, deliveries[nb_deliveries -1 ]);
        Node* wh = pool_query(&ctx.node_pool, warehouses[i]);
        float dist = distance_2D(del->content.delivery->position,
                                 wh->content.warehouse->pos);
        if (min_dist == -1 || dist < min_dist) {
            min_dist = dist;
        }
    }
    cons += consumption(drone, min_dist, speed, 0);

    NodeIndex n_current, n_previous;
    n_previous = deliveries[nb_deliveries - 1];
    Node* prev;
    while (--nb_deliveries > 0 && cons < drone->autonomy && payload < drone->max_capacity) {
        Node* cur = pool_query(&ctx.node_pool, n_current);
        prev = pool_query(&ctx.node_pool, n_previous);
        n_current  = n_previous;
        n_previous = deliveries[nb_deliveries - 1];
        payload += cur->content.delivery->mass;
        distance = distance_2D(cur->content.delivery->position,
                               prev->content.delivery->position);
        cons += consumption(drone, distance, speed, payload);
    }

    payload += prev->content.delivery->mass;

    if (drone->autonomy <= cons || drone->max_capacity < payload)
        return -1;

    Node* first = pool_query(&ctx.node_pool, deliveries[0]);
    //distance = distance_2D(first->content.warehouse->pos, prev->content.delivery->position);
    distance = distance_2D(drone->final_position, first->content.delivery->position);
    cons += consumption(drone, distance, speed, payload);

    return drone->autonomy - cons;
}
*/

static void vec_multf(Position* vec, float f) {
    vec->x *= f;
    vec->y *= f;
}

static float vec_length(Position vec) {
    return sqrtf(vec.x * vec.x + vec.y * vec.y);
}

// Calculate and return the distance added by conturning the constraint
bool is_constrained(ExclusionZone* cnst,
                    const Position* pos1,
                    const Position* pos2,
                    Detour* out_detour) {
    Position p12, p1C, intersect; // Vectors 1 -> 2, 1 -> cnsc->center

    p12.x = pos2->x - pos1->x;
    p12.y = pos2->y - pos1->y;

    p1C.x = cnst->center.x - pos1->x;
    p1C.y = cnst->center.y - pos1->y;

    float dot = p12.x * p1C.x + p12.y * p1C.y;

    float i = dot / (p12.x * p12.x + p12.y * p12.y);

    intersect.x = p12.x * i + pos1->x;
    intersect.y = p12.y * i + pos1->y;

    float dist = distance_2D(cnst->center, intersect);
    if (cnst->radius < dist)
        return false;

    if (dist == 0) {
        Position normal = {.x = p12.y, .y = -p12.x};
        vec_multf(&normal, (cnst->radius + 1) / vec_length(normal));
        *out_detour = (Detour) {
            .distance = dist,
            .pos      = intersect,
        };
        return true;
    }
    *out_detour = (Detour) {
        .distance = dist,
        .pos      = intersect,
    };
    return true;
}
