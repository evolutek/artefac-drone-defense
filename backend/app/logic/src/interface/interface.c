#include "interface.h"
#include "algo/cutter.h"
#include "algo/graph.h"
#include "algo/utils.h"
#include "utils/darray.h"
#include "utils/index.h"
#include "utils/pool.h"

#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <semaphore.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

static int shm_fd;
static SharedMemory* shm;
static sem_t* sem_buf1;
static sem_t* sem_buf2;

static pthread_t thread;

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

static void handle_event(const Event* event) {
    printf("IF: Handling event of type %i.\n", event->type);
    ctx.should_recompute = true;
    switch (event->type) {
    case EVENT_STOP:
        ctx.running = false;
        break;
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
        ctx.missions_in_progress = false;
        break;
    case EVENT_DELIVERY_NEW: {
        pthread_kill(ctx.main_thread, SIGUSR1);
        pthread_mutex_lock(&ctx.pool_mutex);

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
        if (del) {
            ctx.should_recompute = del->repartition_id == 0;
            pthread_kill(ctx.main_thread, SIGUSR1);
            pthread_mutex_lock(&ctx.pool_mutex);
            pool_free(&ctx.delivery_pool, del);
        }
        break;
    }
    case EVENT_WAREHOUSE_NEW: {
        pthread_kill(ctx.main_thread, SIGUSR1);
        pthread_mutex_lock(&ctx.pool_mutex);
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
        add_warehouse(wh);
        break;
    }
    case EVENT_WAREHOUSE_REMOVE: {
        ctx.should_recompute = true;
        pthread_kill(ctx.main_thread, SIGUSR1);
        pthread_mutex_lock(&ctx.pool_mutex);
        Warehouse* wh = find_warehouse_with_id(event->data.id);
        if (wh)
            pool_free(&ctx.warehouse_pool, wh);
        break;
    }
    case EVENT_ITEM_NEW: {
        size_t name_length = event->data.new_item.name_length;
        char* name         = malloc(name_length + 1);
        Item item          = {
                     .id   = event->data.new_item.id,
                     .mass = event->data.new_item.mass,
                     .name = name,
        };
        memcpy(name, event->data.new_item.name, name_length);
        name[name_length] = 0;
        add_item(item);
        break;
    }
    case EVENT_ITEM_REMOVE: {
        // ItemIndex item = find_item_with_id(event->data.id);
        abort();
        // TODO

        break;
    }
    }
    pthread_mutex_unlock(&ctx.pool_mutex);
    sem_post(&ctx.compute_ready_sem);
}

static void* interface_handle(void* _unused) {
    (void) _unused;

    // Block SIGUSR1 on the interface thread
    sigset_t mask;
    sigemptyset(&mask);
    sigaddset(&mask, SIGUSR1);
    pthread_sigmask(SIG_BLOCK, &mask, NULL);

    puts("Algorithm interface initialized.");
    while (ctx.running) {
        puts("IF: Waiting for backend messages...");
        if (sem_wait(sem_buf2) < 0) {
            perror("sem_wait");
        }

        handle_event(&shm->buf2);
    }
    puts("Interface finished.");
    return NULL;
}

static sem_t* try_open_semaphore(const char* name) {
    printf("Attempting to open semaphore file '%s'...", name);
    fflush(stdout);
    size_t retries;
    sem_t* sem;
    for (retries = 0; retries < MAX_RETRIES; retries++) {
        sem = sem_open(name, 0);
        if (sem != SEM_FAILED)
            break;
        sleep(1);
    }
    if (retries == MAX_RETRIES) {
        puts("Timed out.");
        return NULL;
    }
    puts("Done.");
    return sem;
}

static void* try_open_shm(const char* name, int* out_fd) {
    printf("Attempting to open shared memory file '%s'...", name);
    fflush(stdout);
    int fd;
    size_t retries = 0;
    do {
        fd = shm_open(name, O_RDWR, 0666);
        retries++;
        sleep(1);
    } while (fd == -1 && errno == ENOENT && retries < MAX_RETRIES);

    if (retries == MAX_RETRIES) {
        puts("Timed out.");
        return NULL;
    }

    if (ftruncate(fd, SHM_SIZE) == -1) {
        puts("Not resized.");
        close(fd);
        return NULL;
    }

    void* addr = mmap(NULL, SHM_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (addr == MAP_FAILED) {
        close(fd);
        puts("Mapping error.");
        perror("Failed to mmap shared memory");
        return NULL;
    }
    *out_fd = fd;
    puts("Done.");
    return addr;
}

bool init_interface(void) {

    sem_buf1 = try_open_semaphore(SEM_BUF1);
    if (!sem_buf1)
        return false;
    sem_buf2 = try_open_semaphore(SEM_BUF2);
    if (!sem_buf2) {
        sem_close(sem_buf1);
        return false;
    }

    shm = try_open_shm(SHM_NAME, &shm_fd);
    if (!shm) {
        sem_close(sem_buf1);
        sem_close(sem_buf2);
    }

    pthread_create(&thread, NULL, &interface_handle, NULL);
    return true;
}

void stop_interface(void) {
    void* unused;
    pthread_join(thread, &unused);
    (void) unused;

    munmap(shm, SHM_SIZE);
    close(shm_fd);
    sem_close(sem_buf2);
    sem_close(sem_buf1);
}

void send_mission(NodeIndex* repart, const Drone* drone) {

    DroneAssignment ass = {
        .drone_id       = drone->id,
        .waypoint_count = darray_size(repart),
    };
    assert(ass.waypoint_count <= MAX_DELIVERIES_PER_DRONE);

    DARRAY_FOR(i, repart) {
        NodeIndex idx = repart[i];
        Node* n       = pool_query(&ctx.node_pool, idx);
        if (n->type == E_WAREHOUSE) {
            ass.waypoints[i] = (DroneWaypoint) {
                .type = WAYPOINT_WAREHOUSE,
                .pos  = n->content.warehouse->pos,
            };
        } else {
            ass.waypoints[i] = (DroneWaypoint) {
                .type = WAYPOINT_DELIVERY,
                .pos  = n->content.delivery->position,
            };
        }
    }
}

void send_repartitions(NodeIndex** repartitions) {
    if (ctx.missions_in_progress)
        sem_wait(&ctx.compute_ready_sem);

    PoolIter it = pool_iter_init(&ctx.drone_pool);
    DARRAY_FOR(i, repartitions) {
        NodeIndex* drone_repart = repartitions[i];
        const Drone* drone      = pool_iter_next(&it);
        send_mission(drone_repart, drone);
    }
    ctx.missions_in_progress = true;
}
