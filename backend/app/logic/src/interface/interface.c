#include "interface.h"
#include "algo/cutter.h"
#include "algo/utils.h"
#include "utils/index.h"
#include "utils/pool.h"

#include <fcntl.h>
#include <semaphore.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <wchar.h>

static int shm_fd;
static SharedMemory* shm;
static sem_t* sem_buf1;
static sem_t* sem_buf2;

static bool running = true;

#define MAX_RETRIES 5

static ItemIndex find_item_with_id(uint64_t id) {
    pool_foreach2(&ctx.item_pool, Item, item_idx, item) {
        if (item->id == id)
            return item_idx;
    }

    return MAKE_INDEX(Item, INVALID_INDEX);
}

static Warehouse* find_warehouse_with_id(uint64_t id) {
    PoolIter it = pool_iter_init(&ctx.warehouse_pool);

    Warehouse* wh;
    while ((wh = pool_iter_next(&it))) {
        if (wh->id == id) {
            return wh;
        }
    }
    return NULL;
}

static Delivery* find_delivery_with_id(uint64_t id) {
    PoolIter it = pool_iter_init(&ctx.delivery_pool);

    Delivery* del;
    while ((del = pool_iter_next(&it))) {
        if (del->id == id) {
            return del;
        }
    }
    return NULL;
}

static Drone* find_drone_with_id(uint64_t id) {
    PoolIter it = pool_iter_init(&ctx.drone_pool);

    Drone* dr;
    while ((dr = pool_iter_next(&it))) {
        if (dr->id == id) {
            return dr;
        }
    }
    return NULL;
}

bool init_shared_mem(void) {

    shm_fd = shm_open(SHM_NAME, O_CREAT | O_RDWR, 0666);
    ftruncate(shm_fd, SHM_SIZE);
    shm = mmap(NULL, SHM_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd, 0);

    sem_buf1 = sem_open(SEM_BUF1, O_CREAT, S_IRUSR | S_IWUSR, 0);
    if (sem_buf1 == SEM_FAILED)
        abort();

    size_t retries;
    for (retries = 0; retries < MAX_RETRIES; retries++) {
        sem_buf2 = sem_open(SEM_BUF2, 0);
        if (sem_buf2 != SEM_FAILED)
            break;
        sleep(1);
    }
    if (retries == MAX_RETRIES)
        return false;
    return true;
}
void cleanup_shared_mem(void) {
    munmap(shm, SHM_SIZE);
    close(shm_fd);
    sem_unlink(SEM_BUF1);
}

static void handle_event(const Event* event) {
    printf("IF: Handling event of type %i.\n", event->type);
    switch (event->type) {
    case EVENT_STOP:
        running = false;
        return;
    case EVENT_DRONE_NEW: {
        const NewDronePkt* pkt = &event->data.new_drone;
        add_drone((Drone) {
            .id                    = pkt->id,
            .max_capacity          = pkt->max_capacity,
            .max_speed             = pkt->max_speed,
            .acceleration          = pkt->acceleration,
            .energy                = pkt->energy,
            .max_flight_time       = pkt->max_flight_time,
            .max_flight_time_speed = pkt->max_flight_time_speed,
            .position              = pkt->position,
            .final_position        = pkt->position,
        });
        break;
    }
    case EVENT_DRONE_REMOVE: {
        Drone* dr = find_drone_with_id(event->data.id);
        if (dr)
            pool_free(&ctx.drone_pool, dr);
        break;
    }
    case EVENT_DRONE_FINISHED:
        break;
    case EVENT_DELIVERY_NEW: {
        const NewDeliveryPkt* pkt = &event->data.new_delivery;
        add_delivery((Delivery) {
            .quantity      = pkt->quantity,
            .priority      = pkt->priority,
            .user_priority = pkt->precedence,
            .id            = pkt->id,
            .position      = pkt->position,
        });
        break;
    }
    case EVENT_DELIVERY_REMOVE: {
        Delivery* del = find_delivery_with_id(event->data.id);
        if (del)
            pool_free(&ctx.delivery_pool, del);
        break;
    }
    case EVENT_WAREHOUSE_NEW: {
        const NewWarehousePkt* pkt = &event->data.new_warehouse;
        Warehouse wh               = {
                          .id         = pkt->id,
                          .pos        = pkt->position,
                          .item_count = pkt->item_count,
        };
        wh.items = malloc(sizeof *wh.items * wh.item_count);
        for (size_t i = 0; i < wh.item_count; i++) {
            ItemIndex item = find_item_with_id(pkt->items[i]);
            if (INDEX_VALUE(item) == INVALID_INDEX)
                abort();
            wh.items[i] = item;
        }

        break;
    }
    case EVENT_WAREHOUSE_REMOVE: {
        Warehouse* wh = find_warehouse_with_id(event->data.id);
        if (wh)
            pool_free(&ctx.warehouse_pool, wh);
        break;
    }
    case EVENT_ITEM_NEW: {
        Item* item         = _pool_alloc(&ctx.item_pool, NULL);
        size_t name_length = event->data.new_item.name_length;
        char* name         = malloc(name_length + 1);
        *item              = (Item) {
                         .id   = event->data.new_item.id,
                         .mass = event->data.new_item.mass,
                         .name = name,
        };
        memcpy(name, event->data.new_item.name, name_length);
        name[name_length] = 0;
        break;
    }
    case EVENT_ITEM_REMOVE: {
        // ItemIndex item = find_item_with_id(event->data.id);
        abort();
        // TODO

        break;
    }
    }
    puts("IF: Sending data to backend.");
    sem_post(sem_buf1);
}

void interface_handle(void) {

    while (running) {
        puts("IF: Waiting for backend messages...");
        if (sem_wait(sem_buf2) < 0) {
            perror("sem_wait");
        }

        handle_event(&shm->buf2);
    }
    cleanup_shared_mem();
}
