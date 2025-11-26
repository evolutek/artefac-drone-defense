#ifndef INDEX_H
#define INDEX_H

#define INVALID_INDEX SIZE_MAX

#ifdef NDEBUG
    #define DEFINE_INDEX(name) typedef size_t name##Index
    #define INDEX_VALUE(idx) (idx)
    #define MAKE_INDEX(name, val) (val)
#else
    #define DEFINE_INDEX(name) typedef struct { size_t value; } name##Index
    #define INDEX_VALUE(idx) ((idx).value)
#define MAKE_INDEX(name, val) ((name##Index){(val)})
#endif

#endif /* ! INDEX_H */
