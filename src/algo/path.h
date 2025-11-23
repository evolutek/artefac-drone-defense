#pragma once

#include "utils.h"
#include <stdio.h>
#include <stdint.h>


void free_darray_matrice(void** array);

char create_new_solution(struct Delivery*** solution, Delivery* new_element, size_t drone_to_add, struct Drone* drone, struct Delivery**** new_solution);

struct Delivery*** choose_drone_naive_aux(struct Drone** drones, struct Delivery** deliveries, size_t* actual_index, struct Delivery*** solution, float* score);

struct Delivery*** choose_drone_naive(struct Drone** drones, struct Delivery** deliveries);