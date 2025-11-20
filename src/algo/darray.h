#ifndef DARRAY_H
#define DARRAY_H

#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>

enum _DarrayField {
    DARRAY_FIELD_CAPACITY,
    DARRAY_FIELD_SIZE,
    DARRAY_FIELD_STRIDE,
};

/**
 * Example:
 *
 * int* my_int_array = darray_create(16, sizeof(int))
 * darray_add(my_int_array, 42);
 * darray_add(my_int_array, 17);
 * darray_add(my_int_array, 9);

 * my_int_array[1] = -17;
 */
void* darray_create(size_t initial_capacity, size_t stride);
void darray_destroy(void* darray);

/**
 * @brief Add an element at the end of the array.
 *
 * This function should not be called directly ! Use the @ref darray_add macro.
 *
 * @param[inout] elements The dynamic array to use (pointer to its elements)
 * @param[in] obj A pointer to the object to add
 * @return The new array pointer, in case it was reallocated.
 */
void* _darray_add(void* elements, const void* obj);

/**
 * @brief Inserts an element in a dynamic array at the specified index.
 *
 * This function should not be called directly ! Use the @ref darray_insert macro.
 *
 * When the index is negative, it tells a position relative to the *end*  of the array.
 * (like python)
 *
 * @param[inout] elements The dynamic array to use (pointer to its elements)
 * @param[in] index The index to add the element at. Can be negative to indicate an offset from the
 * end of the array.
 * @param[in] obj A pointer to the object to add
 * @return The new array pointer, in case it was reallocated.
 */
void* _darray_insert(void* elements, ssize_t index, const void* obj);

/**
 * @brief Removes the last element of an array.
 *
 * @param[inout] elements The dynamic array to use (pointer to its elements)
 * @param[out] out_elem A pointer to store the popped element.
 * @return The new array pointer, in case it was reallocated.
 */
bool darray_pop(void* darray, void* out_elem);

/**
 * @brief Removes an element inside an array at an index.
 *
 * When the index is negative, it tells a position relative to the *end*  of the array.
 * (like python)
 *
 * @param[inout] elements The dynamic array to use (pointer to its elements)
 * @param[in] index The index of the element to remove. Can be negative to indicate an offset from
 * the end of the array.
 * @param[out] out_elem A pointer to store the popped element.
 * @return The new array pointer, in case it was reallocated.
 */
bool darray_remove(void* darray, ssize_t index, void* out_elem);

void darray_clear(void* darray);

size_t _darray_get_field(const void* darray, enum _DarrayField field);

#define darray_add(darray, elem)                                                                   \
    {                                                                                              \
        typeof(elem) tmp = elem;                                                                   \
        darray           = _darray_add(darray, &tmp);                                              \
    }
#define darray_insert(darray, elem, idx)                                                           \
    {                                                                                              \
        typeof(elem) tmp = elem;                                                                   \
        darray           = _darray_insert(darray, idx, &tmp);                                      \
    }

#define darray_capacity(darray) _darray_get_field(darray, DARRAY_FIELD_CAPACITY)
#define darray_size(darray) _darray_get_field(darray, DARRAY_FIELD_SIZE)
#define darray_stride(darray) _darray_get_field(darray, DARRAY_FIELD_STRIDE)

#define decl_darray(name, type, capacity) type* name = darray_create(capacity, sizeof(type))

#endif /* ! DARRAY_H */