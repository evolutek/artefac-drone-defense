#include "pool.h"
#include "pointers.h"

#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <sys/types.h>
#include <stdlib.h>
#include <string.h>

#define HEADER_SIZE offsetof(struct slot, next)

struct slot {
    bool allocated;
    ssize_t next;
};

/*
static ssize_t node_index(Pool* pool, struct node* node) {
    return node - pool->blocks;
}
*/

static size_t compute_slot_size(size_t stride) {
    size_t size_with_element = stride + HEADER_SIZE;

    return size_with_element > sizeof(struct slot) ? size_with_element : sizeof(struct slot);
}

static inline struct slot* from_index(const Pool* pool, size_t idx) {
    return ptr_offset_bytes(pool->blocks, compute_slot_size(pool->stride) * idx);
}

static inline ptrdiff_t to_index(const Pool* pool, const struct slot* slot) {
    ptrdiff_t diff_bytes = (char*) slot - (char*) pool->blocks;

    return diff_bytes / compute_slot_size(pool->stride);
}

void pool_init(Pool* pool, size_t capacity, size_t stride) {
    assert(pool);
    assert(capacity > 4);
    assert(stride > 0);

    size_t slot_size = compute_slot_size(stride);
    pool->blocks     = malloc(slot_size * capacity);

    for (size_t i = 0; i < capacity; i++) {
        struct slot* n = ptr_offset_bytes(pool->blocks, i * slot_size);
        n->next        = i + 1;
        n->allocated   = false;
    }
    pool->stride     = stride;
    pool->head       = from_index(pool, 0);
    pool->tail       = from_index(pool, capacity - 1);
    pool->tail->next = -1;
    pool->capacity   = capacity;
    pool->size       = 0;

    assert(pool->head == pool->blocks);
    assert(pool->tail == ptr_offset_bytes(pool->blocks, slot_size * (capacity - 1)));
    assert(pool->stride == stride);
    assert(pool->capacity == capacity);
    assert(pool->size == 0);
}

void pool_cleanup(Pool* pool) {
    free(pool->blocks);

    *pool = (Pool) {0};
}

static void grow(Pool* pool) {
    size_t slot_size = compute_slot_size(pool->stride);
    size_t new_cap   = pool->capacity << 1;

    struct slot* new_array = realloc(pool->blocks, slot_size * new_cap);
    if (!new_array) {
        fputs("Could not grow pool\n", stderr);
        abort();
    }

    pool->blocks = new_array;

    for (size_t i = pool->capacity; i < new_cap - 1; i++) {
        struct slot* n = ptr_offset_bytes(new_array, slot_size * i);
        n->next        = i + 1;
        n->allocated   = false;
    }
    struct slot* last_slot = from_index(pool, new_cap - 1);
    last_slot->next        = -1;
    last_slot->allocated   = false;

    pool->head     = from_index(pool, pool->capacity);
    pool->tail     = last_slot;
    pool->capacity = new_cap;
}

void* _pool_alloc(Pool* pool, size_t* out_idx) {
    if (pool->size == pool->capacity) {
        grow(pool);
    }

    struct slot* target = pool->head;
    ssize_t next        = target->next;
    if (next < 0) {
        pool->head = NULL;
        pool->tail = NULL;
    } else
        pool->head = from_index(pool, next);

    target->allocated = true;
    if (out_idx) {
        ssize_t idx = to_index(pool, target);
        assert((size_t) idx < pool->capacity && idx >= 0);
        *out_idx = idx;
    }

    pool->size++;

    return ptr_offset_bytes(target, HEADER_SIZE);
}

void pool_free(Pool* pool, void* ptr) {
    struct slot* node = ptr_offset_bytes(ptr, -HEADER_SIZE);
    ptrdiff_t index   = to_index(pool, node);

    assert(index >= 0 && (size_t) index < pool->capacity && index >= 0);

    node->allocated = false;
    node->next      = -1;
    if (pool->tail)
        pool->tail->next = index;
    else
        pool->head = node;
    pool->tail = node;

    pool->size--;
}

void* _pool_query(const Pool* pool, ssize_t idx) {
    if (idx < 0 || (size_t) idx >= pool->capacity)
        return NULL;
    struct slot* slot = from_index(pool, idx);
    if (!slot->allocated)
        return NULL;
    return ptr_offset_bytes(slot, HEADER_SIZE);
}

void pool_foreach(Pool* pool, action action, void* user_data) {
    size_t slot_size = compute_slot_size(pool->stride);
    for (size_t i = 0; i < pool->capacity; i++) {
        struct slot* node = ptr_offset_bytes(pool->blocks, slot_size * i);
        if (!node->allocated)
            continue;
        if (!action(ptr_offset_bytes(node, HEADER_SIZE), i, user_data))
            return;
    }
}

PoolIter pool_iter_init(const Pool* pool) {
    return (PoolIter) {
        .pool = pool,
    };
}
void* pool_iter_next(PoolIter* iter) {
    if (iter->contiguous_idx >= iter->pool->size)
        return NULL;

    const Pool* pool = iter->pool;

    void* ptr = _pool_query(pool, iter->in_pool_idx);

    iter->contiguous_idx++;
    if (iter->contiguous_idx < pool->size) {
        size_t slot_size = compute_slot_size(pool->stride);
        struct slot* slot;
        do {
            iter->in_pool_idx++;
            slot = ptr_offset_bytes(pool->blocks, slot_size * iter->in_pool_idx);
        } while(!slot->allocated);
    }

    return ptr;
}
size_t pool_iter_idx(const PoolIter* iter) {
    return iter->in_pool_idx;
}
