#include "darray.h"
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

struct darray_header {
    size_t capacity;
    size_t size;
    size_t stride;
};

#define HEADER_SIZE sizeof(struct darray_header)

static void* ptr_offset_bytes(const void* ptr, ssize_t offset) {
    return (void*) ((char*) ptr) + offset;
}

void* darray_create(size_t initial_capacity, size_t stride) {
    if (initial_capacity < 4)
        initial_capacity = 4;

    struct darray_header* darray = malloc(sizeof *darray + initial_capacity * stride);
    if (!darray)
        return NULL;
    *darray = (struct darray_header) {
        .capacity = initial_capacity,
        .stride   = stride,
    };

    return ptr_offset_bytes(darray, HEADER_SIZE);
}

void darray_destroy(void* darray) {
    struct darray_header* header = ptr_offset_bytes(darray, -HEADER_SIZE);

    free(header);
}

static struct darray_header* darray_grow(struct darray_header* header) {
    struct darray_header header_cpy = *header;
    size_t new_cap                  = header_cpy.capacity * 1.5;

    header = realloc(header, HEADER_SIZE + new_cap * header_cpy.stride);
    if (!header)
        return NULL;

    header->capacity = new_cap;
    return header;
}

void* _darray_add(void* elements, const void* obj) {
    struct darray_header* header = ptr_offset_bytes(elements, -HEADER_SIZE);

    if (header->size == header->capacity) {
        header = darray_grow(header);
        if (!header)
            return NULL;
    }

    size_t stride = header->stride;
    size_t size   = header->size;

    void* new_elem_ptr = ptr_offset_bytes(elements, stride * size);
    memcpy(new_elem_ptr, obj, stride);
    header->size++;

    return ptr_offset_bytes(elements, HEADER_SIZE);
}

static bool compute_actual_index(ssize_t index, size_t array_size, size_t* out_actual_index) {
    if (index < 0) {
        if ((size_t) (-index) > array_size)
            return false;
        *out_actual_index = array_size - index;
        return true;
    }

    if ((size_t) index > array_size)
        return false;
    *out_actual_index = index;
    return true;
}

void* _darray_insert(void* elements, ssize_t index, const void* obj) {
    struct darray_header* header = ptr_offset_bytes(elements, -HEADER_SIZE);
    size_t size                  = header->size;
    size_t actual_index;
    if (!compute_actual_index(index, size, &actual_index))
        return false;

    if (size == header->capacity) {
        header = darray_grow(header);
        if (!header)
            return NULL;
    }

    size_t stride = header->stride;

    void* new_elem_ptr = ptr_offset_bytes(elements, stride * actual_index);
    memmove(ptr_offset_bytes(new_elem_ptr, stride), new_elem_ptr, size - actual_index);
    memcpy(new_elem_ptr, obj, stride);
    header->size++;
    return ptr_offset_bytes(elements, HEADER_SIZE);
}

bool darray_pop(void* darray, void* out_elem) {
    struct darray_header* header = ptr_offset_bytes(darray, -HEADER_SIZE);

    if (header->size == 0)
        return false;

    size_t stride = header->stride;

    memcpy(out_elem, ptr_offset_bytes(darray, stride * (header->size - 1)), stride);

    header->size--;
    return true;
}

bool darray_remove(void* darray, ssize_t index, void* out_elem) {
    struct darray_header* header = ptr_offset_bytes(darray, -HEADER_SIZE);
    size_t size                  = header->size;

    if (size == 0)
        return false;

    size_t actual_index;
    if (!compute_actual_index(index, size, &actual_index))
        return false;

    size_t stride = header->stride;

    memcpy(out_elem, ptr_offset_bytes(darray, stride * actual_index), stride);

    header->size--;
    return true;
}

void darray_clear(void* darray) {
    struct darray_header* header = ptr_offset_bytes(darray, -HEADER_SIZE);
    header->size = 0;
}

size_t _darray_get_field(const void* darray, enum _DarrayField field) {
    struct darray_header* header = ptr_offset_bytes(darray, -HEADER_SIZE);

    switch (field) {
    case DARRAY_FIELD_CAPACITY:
        return header->capacity;
    case DARRAY_FIELD_SIZE:
        return header->size;
    case DARRAY_FIELD_STRIDE:
        return header->stride;
    }
    return 0;
}