#pragma once

#include "utils.h"
#include <stdio.h>
#include <stdint.h>


struct Delivery*** build_final_array(struct Drone** drones, size_t size_drones, struct Delivery** input_list_deliveries, size_t* input_list_drones, size_t input_index, uint32_t* min);

struct Delivery*** choose_drone_naive_aux(struct Drone** drones, size_t drone_size, struct Delivery** deliveries,
     size_t deliveries_size, uint32_t* min, struct Delivery** input_list_deliveries, size_t* input_list_drones, size_t* input_index);

struct Delivery*** choose_drone_naive(struct Drone** drones, size_t drone_size, struct Delivery** deliveries, size_t deliveries_size);