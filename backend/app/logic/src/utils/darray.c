#include "darray.h"
#include "pointers.h"
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>
#include <stdint.h>
#include <inttypes.h>

struct darray_header {
    size_t capacity;
    size_t size;
    size_t stride;
};

#define HEADER_SIZE sizeof(struct darray_header)

void* darray_create(size_t initial_capacity, size_t stride) {
    if (initial_capacity < 4)
        initial_capacity = 4;

    struct darray_header* darray = malloc(sizeof *darray + initial_capacity * stride);
    if (!darray)
        return NULL;

    /* Initialise correctement size à 0 */
    *darray = (struct darray_header) {
        .capacity = initial_capacity,
        .size     = 0,
        .stride   = stride,
    };

    return ptr_offset_bytes(darray, HEADER_SIZE);
}

void darray_destroy(void* darray) {
    if (!darray) return;
    struct darray_header* header = ptr_offset_bytes(darray, -HEADER_SIZE);

    free(header);
}

static struct darray_header* darray_grow(struct darray_header* header) {
    /* Copie du header pour utiliser les anciennes valeurs */
    struct darray_header header_cpy = *header;

    /* croissance 1.5x mais assurer au moins +1 */
    size_t new_cap = header_cpy.capacity + header_cpy.capacity / 2;
    if (new_cap <= header_cpy.capacity)
        new_cap = header_cpy.capacity + 1;

    header = realloc(header, HEADER_SIZE + new_cap * header_cpy.stride);
    if (!header) {
        fputs("Failed to grow a dynamic array", stderr);
        abort();
    }

    header->capacity = new_cap;
    return header;
}

void* _darray_add(void* elements, const void* obj) {
    if (!elements || !obj) return elements;

    struct darray_header* header = ptr_offset_bytes(elements, -HEADER_SIZE);

    if (header->size == header->capacity) {
        header = darray_grow(header);
        elements = ptr_offset_bytes(header, HEADER_SIZE);
    }

    size_t stride = header->stride;
    size_t size   = header->size;

    void* new_elem_ptr = ptr_offset_bytes(elements, stride * size);
    memcpy(new_elem_ptr, obj, stride);
    header->size++;

    return elements;
}

/* Helper: convert an (possibly negative) index to actual index in [0..array_size].
 * Returns true if valid, false if out-of-range. */
static bool compute_actual_index(ssize_t index, size_t array_size, size_t* out_actual_index) {
    if (!out_actual_index) return false;

    if (index < 0) {
        /* index negative: -1 => last element => array_size - 1
           On vérifie que -index <= array_size (ex: index = -11 sur size 10 => invalide) */
        ssize_t neg = -index;
        if ((size_t)neg > array_size)
            return false;
        /* correction : actual = size + index (p.ex. size=10, index=-1 => 9) */
        *out_actual_index = array_size + (size_t)index;
        return true;
    }

    /* index >= 0 : il est accepté jusqu'à size (insertion possible en position size) */
    if ((size_t)index > array_size)
        return false;
    *out_actual_index = (size_t)index;
    return true;
}

void* _darray_insert(void* elements, ssize_t index, const void* obj) {
    if (!elements || !obj) return elements;

    struct darray_header* header = ptr_offset_bytes(elements, -HEADER_SIZE);
    size_t size = header->size;
    size_t actual_index;
    if (!compute_actual_index(index, size, &actual_index))
        return elements; /* ne rien faire si index invalide, retourner le pointeur inchangé */

    if (size == header->capacity) {
        header = darray_grow(header);
        elements = ptr_offset_bytes(header, HEADER_SIZE);
    }

    size_t stride = header->stride;

    /* emplacement où insérer */
    void* new_elem_ptr = ptr_offset_bytes(elements, stride * actual_index);

    /* décaler les éléments existants d'un "stride" vers la droite
       nombre d'octets à déplacer = stride * (size - actual_index) */
    if (size > actual_index) {
        memmove(ptr_offset_bytes(new_elem_ptr, stride),
                new_elem_ptr,
                stride * (size - actual_index));
    }

    /* copier le nouvel élément */
    memcpy(new_elem_ptr, obj, stride);
    header->size++;
    return elements;
}

bool darray_pop(void* darray, void* out_elem) {
    if (!darray) return false;
    struct darray_header* header = ptr_offset_bytes(darray, -HEADER_SIZE);

    if (header->size == 0)
        return false;

    size_t stride = header->stride;

    if (out_elem)
        memcpy(out_elem, ptr_offset_bytes(darray, stride * (header->size - 1)), stride);

    header->size--;
    return true;
}

bool darray_remove(void* darray, ssize_t index, void* out_elem) {
    if (!darray) return false;
    struct darray_header* header = ptr_offset_bytes(darray, -HEADER_SIZE);
    size_t size = header->size;

    if (size == 0)
        return false;

    size_t actual_index;
    if (!compute_actual_index(index, size, &actual_index))
        return false;

    size_t stride = header->stride;
    void* target_ptr = ptr_offset_bytes(darray, stride * actual_index);

    if (out_elem)
        memcpy(out_elem, target_ptr, stride);

    /* décale les éléments après actual_index vers la gauche d'un stride */
    if (actual_index + 1 < size) {
        void* src = ptr_offset_bytes(target_ptr, stride);
        memmove(target_ptr, src, stride * (size - actual_index - 1));
    }

    header->size--;
    return true;
}

void darray_clear(void* darray) {
    if (!darray) return;
    struct darray_header* header = ptr_offset_bytes(darray, -HEADER_SIZE);
    header->size = 0;
}

size_t _darray_get_field(const void* darray, enum _DarrayField field) {
    if (!darray) return 0;
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
