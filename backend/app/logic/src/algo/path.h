#pragma once

#include "utils.h"
#include <stdint.h>
#include <stdio.h>

typedef struct Element_deliveries {
    struct Delivery* delivery; // pointeur sur delivery
    size_t* warehouses;        // liste des warehouse qui peuvent y accéder
} Element_deliveries;

NodeIndex** choose_drone_naive(struct Drone** drones, NodeIndex* warehouses);

NodeIndex** choose_drone_naive_warehouse(struct Drone** drones,
                                         DroneIndex index,
                                         NodeIndex* warehouse,
                                         NodeIndex** warehouse_solution,
                                         NodeIndex** deliveries,
                                         DroneIndex* index_return,
                                         float* score_return);

char create_new_solution_warehouse(NodeIndex** warehouse_solution,
                                   DroneIndex index_to_add,
                                   struct Drone* drone,
                                   NodeIndex selected_warehouse,
                                   NodeIndex*** new_warehouse_solution);

NodeIndex** copy_solution(NodeIndex** solution);

NodeIndex** choose_drone_naive_aux(struct Drone** drones,
                                   NodeIndex** deliveries,
                                   DroneIndex* actual_index,
                                   NodeIndex** solution,
                                   float* score,
                                   size_t** all_edited_indexs,
                                   NodeIndex* warehouses);

char good_warehouse(NodeIndex* drone_path, NodeIndex* delivery);

char create_new_solution(NodeIndex** solution,
                         NodeIndex new_element,
                         DroneIndex drone_to_add,
                         struct Drone* drone,
                         NodeIndex*** new_solution,
                         NodeIndex* warehouses);

float cost_between(NodeIndex start, NodeIndex next);

void partial_free_solution_parent(NodeIndex** solution,
                                  size_t** modified_son,
                                  size_t** modified_parent);

void partial_free_solution(NodeIndex** solution, size_t* modified);

void free_darray_matrice(void** array);
