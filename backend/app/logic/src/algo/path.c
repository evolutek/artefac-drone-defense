#include "path.h"
#include "darray.h"
#include <stdlib.h>

//free an darray of darray
void free_darray_matrice(void** array){
    for (size_t k = 0; k < darray_size(array); k++){
        darray_clear(array[k]);
        darray_destroy(array[k]);
    }
    darray_destroy(array);
}

//check if the new solution can be created, if it is the case it create a copy of the solution with the new element
char create_new_solution(struct Delivery*** solution, Delivery* new_element, size_t drone_to_add, struct Drone* drone, struct Delivery**** new_solution){

    //copy and add the element
    struct Delivery** drone_to_edit = darray_create(darray_size(solution[drone_to_add]), sizeof(struct Delivery*));
    char changed = 0;
    uint32_t min_insert = 0;
    uint32_t min_actual = 0;
    size_t index_to_add = 0;

    struct Position* ancient = drone->position;
    for (size_t i = 0; i < darray_size(solution[drone_to_add]); i++){
        darray_add(drone_to_edit, solution[drone_to_add][i]);
        min_actual = distance_2D(ancient, new_element->position) + 
                    distance_2D(new_element->position, drone_to_edit[i]->position) -
                    distance_2D(ancient, drone_to_edit[i]->position);
        ancient = drone_to_edit[i]->position;
        if (changed == 0 || min_insert > min_actual){
            min_insert = min_actual;
            index_to_add = i;
            changed = 1;
        }
    }

    //add the new element
    if (index_to_add == 0 || min_insert > distance_2D(ancient, new_element->position)){
        darray_add(drone_to_edit, new_element);
    }
    else{
        darray_insert(drone_to_edit, index_to_add, new_element);
    }

    //check if the solution can exist
    if (can_handle(drone, darray_size(drone_to_edit), drone_to_edit, drone->max_speed) > 0){
        //copy all the list
        *new_solution = darray_create(darray_size(solution), sizeof(struct Delivery**));
        for (size_t i = 0; i < darray_size(solution); i++){
            if (i == drone_to_add){
                darray_add((*new_solution), drone_to_edit);
            }
            else{
                struct Delivery** cpy_drone;
                if (darray_size(solution[i]) < 5)
                    cpy_drone = darray_create(5, sizeof(struct Delivery*));
                else
                    cpy_drone = darray_create(darray_size(solution[i]), sizeof(struct Delivery*));

                for (size_t j = 0; j < darray_size(solution[i]); j++){
                    darray_add(cpy_drone, solution[i][j]);
                }
                darray_add((*new_solution), cpy_drone);
            }
        }
        return 1;
    }

    //clear the list if it can't be handled
    darray_clear(drone_to_edit);
    darray_destroy(drone_to_edit);

    return 0;
}


//build all the possible solutions and return the best one with it score
struct Delivery*** choose_drone_naive_aux(struct Drone** drones, struct Delivery** deliveries, size_t* actual_index, struct Delivery*** solution, float* score){

    //End of the recursion
    if (*actual_index == darray_size(deliveries)){
        float new_score = 0;
        for (size_t i = 0; i < darray_size(drones); i++){
            struct Position* ancient = drones[i]->position;
            for (size_t j = 0; j < darray_size(solution[i]); j++){
                new_score += distance_2D(ancient, solution[i][j]->position);
                ancient = solution[i][j]->position;
            }
        }
        
        *score = new_score;
        return solution;
    }

    //Initialize the variables to stock the best result
    struct Delivery*** best_solution = NULL;
    float best_score = 0;
    size_t best_depth = *actual_index;

    for (size_t d = 0; d < darray_size(drones); d++){

        //check if we can create a new solution and create it iif it is the case
        struct Delivery*** new_solution;
        if (create_new_solution(solution, deliveries[*actual_index], d, drones[d], &new_solution)){

            //get the best solution
            float best_actual_score = 0;
            size_t depth = *actual_index + 1;
            new_solution = choose_drone_naive_aux(drones, deliveries, &depth, new_solution, &best_actual_score);
            
            //replace the best solution by he current solution if it is better
            if (best_score == 0){
                best_score = best_actual_score;
                best_depth = depth;
                best_solution = new_solution;
            }
            else if (depth < best_depth || best_actual_score < best_score){
                best_score = best_actual_score;
                best_depth = depth;

                free_darray_matrice((void**)best_solution);

                best_solution = new_solution;
            }
            else{
                free_darray_matrice((void**)new_solution);
            }
        }
    }

    //no solution created
    if (best_score == 0){
        float new_score = 0;
        for (size_t i = 0; i < darray_size(drones); i++){
            struct Position* ancient = drones[i]->position;
            for (size_t j = 0; j < darray_size(solution[i]); j++){
                new_score += distance_2D(ancient, solution[i][j]->position);
                ancient = solution[i][j]->position;
            }
        }
        
        *score = new_score;
        return solution;
    }

    free_darray_matrice((void**)solution);

    //return the best solution
    *score = best_score;
    *actual_index = best_depth;
    return best_solution;
}


//take in argument a list of drones and a list of deliveries and return the best asignment
struct Delivery*** choose_drone_naive(struct Drone** drones, struct Delivery** deliveries){

    //call the auxiliar function and return the result
    size_t actual_index = 0;
    struct Delivery*** solution = darray_create(darray_size(drones), sizeof(Delivery**));
    for (size_t i = 0; i < darray_size(drones); i++){
        darray_add(solution, darray_create(5, sizeof(Delivery*)));
    }
    float score = 0;

    struct Delivery*** result = choose_drone_naive_aux(drones, deliveries, &actual_index, solution, &score);

    return result;

}