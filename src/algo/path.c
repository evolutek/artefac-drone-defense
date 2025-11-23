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

void partial_free_solution(struct Delivery*** solution, size_t* modified){
    for (size_t i = 0; i < darray_size(modified); i++){
        darray_clear(solution[modified[i]]);
        darray_destroy(solution[modified[i]]);
    }
    darray_clear(solution);
    darray_destroy(solution);
}


void partial_free_solution_parent(struct Delivery*** solution, size_t** modified_son, size_t** modified_parent){
    for (size_t i = 0; i < darray_size(*modified_parent); i++){
        
        char found = 0;
        for (size_t j = 0; j < darray_size((*modified_son)); j++){
            if ((*modified_parent)[i] == (*modified_son)[j]){
                darray_clear(solution[(*modified_parent)[i]]);
                darray_destroy(solution[(*modified_parent)[i]]);
                found = 1;
                break;
            }
        }
        if (found == 0){
            darray_add(*modified_son, (*modified_parent)[i]);
        }
        
    }
    darray_clear(solution);
    darray_destroy(solution);

    darray_clear(*modified_parent);
    darray_destroy(*modified_parent);
}



//check if the new solution can be created, if it is the case it create a copy of the solution with the new element
char create_new_solution(struct Delivery*** solution, Delivery* new_element, size_t drone_to_add, struct Drone* drone, struct Delivery**** new_solution){

    //copy and add the element
    struct Delivery** drone_to_edit = darray_create(darray_size(solution[drone_to_add]), sizeof(struct Delivery*));
    char changed = 0;
    uint32_t min_insert = 0;
    uint32_t min_actual = 0;
    size_t index_edit = 0;

    struct Position* ancient = drone->position;
    for (size_t i = 0; i < darray_size(solution[drone_to_add]); i++){
        darray_add(drone_to_edit, solution[drone_to_add][i]);
        min_actual = distance_2D(ancient, new_element->position) + 
                    distance_2D(new_element->position, drone_to_edit[i]->position) -
                    distance_2D(ancient, drone_to_edit[i]->position);
        ancient = drone_to_edit[i]->position;
        if (changed == 0 || min_insert > min_actual){
            min_insert = min_actual;
            index_edit = i;
            changed = 1;
        }
    }

    //add the new element
    if (index_edit == 0 || min_insert > distance_2D(ancient, new_element->position)){
        darray_add(drone_to_edit, new_element);
    }
    else{
        darray_insert(drone_to_edit, index_edit, new_element);
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
                darray_add(*new_solution, solution[i]);
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
struct Delivery*** choose_drone_naive_aux(struct Drone** drones, struct Delivery** deliveries, size_t* actual_index, struct Delivery*** solution, float* score, size_t** all_edited_indexs){

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
    size_t* best_indexs_edited;

    for (size_t d = 0; d < darray_size(drones); d++){

        //check if we can create a new solution and create it iif it is the case
        struct Delivery*** new_solution;
        if (create_new_solution(solution, deliveries[*actual_index], d, drones[d], &new_solution)){

            size_t* indexs_edited = darray_create(5, sizeof(size_t));
            darray_add(indexs_edited, d);

            //get the best solution
            float best_actual_score = 0;
            size_t depth = *actual_index + 1;
            new_solution = choose_drone_naive_aux(drones, deliveries, &depth, new_solution, &best_actual_score, &indexs_edited);
            
            //replace the best solution by he current solution if it is better
            if (best_score == 0){
                best_score = best_actual_score;
                best_depth = depth;
                best_indexs_edited = indexs_edited;
                best_solution = new_solution;
            }
            else if (depth < best_depth || best_actual_score < best_score){
                best_score = best_actual_score;
                best_depth = depth;

                //free tout ce qui a été modifié par l'ancien meilleur fils
                partial_free_solution(best_solution, best_indexs_edited);

                darray_clear(best_indexs_edited);
                darray_destroy(best_indexs_edited);

                best_indexs_edited = indexs_edited;
                best_solution = new_solution;
            }
            else{
                //free tout ce qui a été modifié par le fils
                partial_free_solution(new_solution, indexs_edited);

                darray_clear(indexs_edited);
                darray_destroy(indexs_edited);
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

    partial_free_solution_parent(solution, &best_indexs_edited, all_edited_indexs);
    *all_edited_indexs = best_indexs_edited;

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
    size_t* all_edited_indexs = darray_create(darray_size(drones), sizeof(size_t));
    for (size_t i = 0; i < darray_size(drones); i++){
        darray_add(all_edited_indexs, i);
        darray_add(solution, darray_create(5, sizeof(Delivery*)));
    }
    float score = 0;

    struct Delivery*** result = choose_drone_naive_aux(drones, deliveries, &actual_index, solution, &score, &all_edited_indexs);

    darray_clear(all_edited_indexs);
    darray_destroy(all_edited_indexs);

    return result;

}
