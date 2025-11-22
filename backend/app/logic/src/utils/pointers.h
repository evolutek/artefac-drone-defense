#include <stdio.h>

static inline void* ptr_offset_bytes(const void* ptr, ssize_t offset) {
    return (void*) ((char*) ptr) + offset;
}
