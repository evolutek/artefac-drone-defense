#pragma once

#include "utils.h"
#include <stdio.h>
#include <stdint.h>


typedef struct Element_deliveries {
	struct Delivery* delivery; //pointeur sur delivery
    size_t*  warehouses; //liste des warehouse qui peuvent y accéder
} Element_deliveries;

Node*** choose_drone_naive(struct Drone** drones, Node** warehouses, size_t size);

Node*** choose_drone_naive_warehouse(struct Drone** drones, size_t index, Node** warehouse, Node*** warehouse_solution, 
    Node*** deliveries, size_t* index_return, float* score_return);

char create_new_solution_warehouse(Node*** warehouse_solution, size_t index_to_add, struct Drone* drone, Node* selected_warehouse, Node**** new_warehouse_solution);

Node*** copy_solution(Node*** solution);

Node*** choose_drone_naive_aux(struct Drone** drones, Node*** deliveries, size_t* actual_index, Node*** solution, float* score, size_t** all_edited_indexs);

char good_warehouse(Node** drone_path, Node** delivery);

char create_new_solution(Node*** solution, Node* new_element, size_t drone_to_add, struct Drone* drone, Node**** new_solution);

float cost_between(Node* start, Node* next);

void partial_free_solution_parent(Node*** solution, size_t** modified_son, size_t** modified_parent);

void partial_free_solution(Node*** solution, size_t* modified);

void free_darray_matrice(void** array);