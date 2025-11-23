#pragma once

#include "utils.h"
#include <stdio.h>
#include <stdint.h>


void free_darray_matrice(void** array);

void partial_free_solution(struct Delivery*** solution, size_t* modified);

char create_new_solution(struct Delivery*** solution, Delivery* new_element, size_t drone_to_add, struct Drone* drone, struct Delivery**** new_solution);

struct Delivery*** choose_drone_naive_aux(struct Drone** drones, struct Delivery** deliveries, size_t* actual_index, struct Delivery*** solution, float* score, size_t** all_edited_indexs);

struct Delivery*** choose_drone_naive(struct Drone** drones, struct Delivery** deliveries);