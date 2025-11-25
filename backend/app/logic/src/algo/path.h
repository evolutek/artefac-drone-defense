#pragma once

#include "utils.h"
#include <stdio.h>
#include <stdint.h>


typedef struct Element_deliveries {
	struct Delivery* delivery; //pointeur sur delivery
    size_t*  warehouses; //liste des warehouse qui peuvent y accéder
} Element_deliveries;


void free_darray_matrice(void** array);

void partial_free_solution(struct Node*** solution, size_t* modified);

void partial_free_solution_parent(struct Node*** solution, size_t** modified_son, size_t** modified_parent);

char create_new_solution(struct Node*** solution, Node* new_element, size_t drone_to_add, struct Drone* drone, struct Node**** new_solution);

struct Node*** choose_drone_naive_aux(struct Drone** drones, struct Node*** deliveries, size_t* actual_index, struct Node*** solution, float* score, size_t** all_edited_indexs);

struct Node*** choose_drone_naive(struct Drone** drones, struct Node** warehouses, size_t size);