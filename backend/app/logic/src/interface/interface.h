#ifndef INTERFACE_H
#define INTERFACE_H

#include "algo/utils.h"
#include <linux/limits.h>
#include <stddef.h>
#include <stdint.h>

#define PACKED __attribute__((packed))

#define SHM_NAME "/algo_shm"
#define SHM_SIZE 65536

// Buf1: C -> Python
// Buf2: Python -> C
#define SEM_BUF1 "/sem_buf1"
#define SEM_BUF2 "/sem_buf2"

#define MAX_WAREHOUSE_ITEMS 32
#define MAX_ITEM_NAME_SIZE 128
#define MAX_ASSIGNMENTS 32
#define MAX_DELIVERIES_PER_DRONE 8

enum EventType {
    EVENT_STOP      = 0,
    EVENT_DRONE_NEW = 1,
    EVENT_DRONE_REMOVE,
    EVENT_DRONE_FINISHED,

    EVENT_DELIVERY_NEW,
    EVENT_DELIVERY_REMOVE,

    EVENT_WAREHOUSE_NEW,
    EVENT_WAREHOUSE_REMOVE,

    EVENT_ITEM_NEW,
    EVENT_ITEM_REMOVE,
};

typedef struct NewDeliveryPkt {
    uint64_t id;
    Position position;
    uint8_t priority;
    uint8_t precedence;
    uint16_t quantity;
    uint64_t item_id;
} PACKED NewDeliveryPkt;

typedef struct {
    uint64_t id;
    Position position;
    uint32_t max_capacity;         // In grams
    float energy;                  // In Wh
    uint16_t max_flight_time;      // In s
    uint8_t max_flight_time_speed; // In m/s
    uint8_t max_speed;             // In m/s
    uint8_t acceleration;          // In m/s²
} PACKED NewDronePkt;

typedef struct {
    uint64_t id;
    Position position;
    uint32_t item_count;
    uint64_t items[MAX_WAREHOUSE_ITEMS];
} PACKED NewWarehousePkt;

typedef struct {
    uint64_t id;
    uint32_t mass;
    uint32_t name_length;
    char name[MAX_ITEM_NAME_SIZE];
} PACKED NewItemPkt;

typedef struct {
    enum EventType type;
    union {
        NewDeliveryPkt new_delivery;
        NewDronePkt new_drone;
        NewWarehousePkt new_warehouse;
        NewItemPkt new_item;
        uint64_t id; // Used for remove and drone finished events.
    } data;
} PACKED Event;

enum DroneWaypointType {
    WAYPOINT_DELIVERY,
    WAYPOINT_WAREHOUSE,
    WAYPOINT_ROUTE,
};

typedef struct {
    Position pos;
    enum DroneWaypointType type;
} PACKED DroneWaypoint;

typedef struct {
    uint64_t drone_id;
    uint32_t waypoint_count;
    Position waypoints[MAX_DELIVERIES_PER_DRONE];
} PACKED DroneAssignment;

typedef struct {

    volatile uint32_t backend_ready;
    volatile uint32_t algo_ready;

    volatile uint32_t active_buf1;
    volatile uint32_t active_buf2;

    Event buf2;
    DroneAssignment buf1;
} PACKED SharedMemory;

bool init_interface(void);
void stop_interface(void);

#endif /* ! INTERFACE_H */
