#ifndef POOL_H
#define POOL_H

#include <stdbool.h>
#include <stddef.h>
#include <assert.h>

typedef struct pool {
    struct slot* blocks;
    struct slot* head;
    struct slot* tail;
    size_t stride;
    size_t capacity;
    size_t size;
} Pool;

typedef bool (*action)(const void* ptr, size_t idx, void* user_data);

void pool_init(Pool* pool, size_t capacity, size_t stride);
void pool_cleanup(Pool* pool);

void* pool_alloc(Pool* pool, long* out_idx);
void pool_free(Pool* pool, void* block);

void* pool_query(Pool* pool, long idx);
void pool_foreach(Pool* pool, action action, void* user_data);

#define pool_add(pool, elem, out_idx_ptr)                                                          \
    {                                                                                              \
        assert(sizeof(elem) == (pool)->stride);                                                    \
        typeof(elem)* ptr = pool_alloc(pool, out_idx_ptr);                                         \
        *ptr              = elem;                                                                  \
    }

#endif /* ! POOL_H */
