#ifndef POOL_H
#define POOL_H

#include "index.h"
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>

#define MACRO_2_OPT(_1, _2, _3, _4, NAME, ...) NAME

typedef struct pool {
    struct slot* blocks;
    struct slot* head;
    struct slot* tail;
    size_t stride;
    size_t capacity;
    size_t size;
} Pool;

typedef struct {
    const Pool* pool;
    size_t in_pool_idx;
    size_t iterated_count;
} PoolIter;

typedef bool (*action)(const void* ptr, size_t idx, void* user_data);

void pool_init(Pool* pool, size_t capacity, size_t stride);
void pool_cleanup(Pool* pool);

void* _pool_alloc(Pool* pool, size_t* out_idx);
void pool_free(Pool* pool, void* block);

void* _pool_query(const Pool* pool, long idx);
void pool_foreach(Pool* pool, action action, void* user_data);

PoolIter pool_iter_init(const Pool* pool);
void* pool_iter_next(PoolIter* iter);
size_t pool_iter_idx(const PoolIter* iter);

#define pool_add_idx(pool, type, elem, out_idx)                                                    \
    {                                                                                              \
        assert(sizeof(elem) == (pool)->stride && sizeof(type) == sizeof(elem));                    \
        size_t _idx;                                                                               \
        type* ptr = _pool_alloc(pool, &_idx);                                                      \
        *ptr      = elem;                                                                          \
        out_idx   = MAKE_INDEX(type, _idx);                                                        \
    }

#define pool_add_no_idx(pool, type, elem)                                                          \
    {                                                                                              \
        assert(sizeof(elem) == (pool)->stride && sizeof(type) == sizeof(elem));                    \
        type* ptr = _pool_alloc(pool, NULL);                                                       \
        *ptr      = elem;                                                                          \
    }

#define pool_add(...) MACRO_2_OPT(__VA_ARGS__, pool_add_idx, pool_add_no_idx)(__VA_ARGS__)

#define pool_foreach2(pool, type, idx_name, var_name)                                              \
    for (PoolIter _it = pool_iter_init(pool); _it.iterated_count < (pool)->size;)                    \
        for (type* var_name = (type*) pool_iter_next(&_it); var_name; var_name = NULL)             \
            for (type##Index idx_name = MAKE_INDEX(type, pool_iter_idx(&_it)); var_name;           \
                 var_name             = NULL)

#define pool_query(pool, index) _pool_query(pool, INDEX_VALUE(index))

#endif /* ! POOL_H */
