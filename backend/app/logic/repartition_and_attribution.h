//What do we need

//naive optimised function to find the best path

#pragma once

#include <utils.h>

struct List{
    void* elements;
    void type;
    size_t max_size;
    size_t size;
}

void Add_element(struct List, void* element);