#pragma once

#include "utils.h"
#include <stdio.h>
#include <stdint.h>


void free_darray_matrice(void** array);

struct Delivery*** build_final_array(struct Drone** drones, struct Delivery** input_list_deliveries, size_t* input_list_drones, size_t input_index, float* min);

struct Delivery*** choose_drone_naive_aux(struct Drone** drones, struct Delivery** deliveries, 
    float* min, struct Delivery** input_list_deliveries, size_t* input_list_drones, size_t* input_index);

struct Delivery*** choose_drone_naive(struct Drone** drones, struct Delivery** deliveries);