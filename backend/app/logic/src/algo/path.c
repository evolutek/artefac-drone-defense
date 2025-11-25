#include "path.h"
#include "utils/darray.h"
#include <stdlib.h>
#include "graph.h"


//take in argument a list of drones and a list of deliveries and return the best asignment
Node*** choose_drone_naive(struct Drone** drones, Node** warehouses){

    //consreuire deliveries : une liste des livraisons et des entrepots qui peuvent y accéder
    //appel choose_drone_naive_warehouse

    //prend les drones 
    Node*** deliveries = darray_create(10, sizeof(Node**));
    for (size_t i = 0; i < darray_size(warehouses); i++){
        for (size_t j = 0; j < warehouses[i]->nb_edges; j++){
            //on a la livraison qu'on veut ajouter : regarder si elle est présente dans deliveries, sinon ajouter : faire une struct
            char found = 0;
            for (size_t k = 0; k < darray_size(deliveries); k++){
                if (warehouses[i]->edges[j].next == deliveries[k][0]){
                    darray_add(deliveries[k], warehouses[i]);
                    found = 1;
                    break;
                }
            }
            if (found == 0){
                Node** new_list = darray_create(4, sizeof(Node*));
                darray_add(new_list, warehouses[i]->edges[j].next);
                darray_add(new_list, warehouses[i]);
                darray_add(deliveries, new_list);
            }
            
            //recherche de si il existe
            //sinon l'ajouter
        }
    }

    Node*** warehouse_solution = darray_create(darray_size(drones), sizeof(Node**));
    for (size_t i = 0; i < darray_size(drones); i++){
        darray_add(warehouse_solution, darray_create(10, sizeof(Node*)));
    }

    size_t indx = 0;
    float score = 0;
    Node*** result = choose_drone_naive_warehouse(drones, 0, warehouses, warehouse_solution, deliveries, &indx, &score);


    free_darray_matrice((void**)deliveries);

    //free tout ce que j'ai à free (qui n'est pas free par les autres fonctions)
    free_darray_matrice((void**)warehouse_solution);

    return result;
}

//call choose_drone_naive as many times as needed
Node*** choose_drone_naive_warehouse(struct Drone** drones, size_t index, Node** warehouse, Node*** warehouse_solution, 
    Node*** deliveries, size_t* index_return, float* score_return){

    //condition d'arrêt
    if (index == darray_size(drones)){
        //appel choose_drone_naive_aux

        size_t actual_index = 0;
        //Node*** solution = darray_create(darray_size(drones), sizeof(Node**));
        size_t* all_edited_indexs = darray_create(darray_size(drones), sizeof(size_t));
        for (size_t i = 0; i < darray_size(drones); i++){
            darray_add(all_edited_indexs, i);
            //darray_add(solution, darray_create(5, sizeof(Node*)));
        }
        float score = 0;
        Node*** temp_solution = copy_solution(warehouse_solution);

        Node*** result = choose_drone_naive_aux(drones, deliveries, &actual_index, temp_solution, &score, &all_edited_indexs);

        *index_return = actual_index;
        *score_return = score;


        darray_clear(all_edited_indexs);
        darray_destroy(all_edited_indexs);


        return result;
    }

    //initialise les meilleurs scores
    size_t best_index = 0;
    float best_score = 0;
    Node*** best_result = NULL;

    for (size_t i = 0; i < darray_size(warehouse); i++){
        Node*** new_solution;
        if (create_new_solution_warehouse(warehouse_solution, index, drones[index], warehouse[i], &new_solution)){

            drones[index]->autonomy = drones[index]->energy; 
            size_t actual_index = 0;
            float score = 0;
            Node*** result = choose_drone_naive_warehouse(drones, index + 1, warehouse, new_solution, deliveries, &actual_index, &score);

            if (best_result == NULL){
                best_index = actual_index;
                best_score = score;
                best_result = result;
            }
            else if (actual_index > best_index || (actual_index == best_index && score < best_score)){
                best_index = actual_index;
                best_score = score;
                free_darray_matrice((void**)best_result);
                best_result = result;
            }
            else{
                free_darray_matrice((void**)result);
            }
            free_darray_matrice((void**)new_solution);
        }
    }
    //free_darray_matrice((void**)warehouse_solution);

    return best_result;
}

//create a copy with the drone->selected_warehouse
char create_new_solution_warehouse(Node*** warehouse_solution, size_t index_to_add, struct Drone* drone, Node* selected_warehouse, Node**** new_warehouse_solution){

    if (consumption(drone, distance_2D(drone->final_position, selected_warehouse->content.warehouse->pos), drone->max_speed, 0) < drone->autonomy){
        //copie
        *new_warehouse_solution = darray_create(darray_size(warehouse_solution), sizeof(Node**));
        for (size_t i = 0; i < darray_size(warehouse_solution); i++){
            Node** cpy_line = darray_create(darray_size(warehouse_solution[i]), sizeof(Node*));
            for (size_t j = 0; j < darray_size(warehouse_solution[i]); j++){
                darray_add(cpy_line, warehouse_solution[i][j]);
            }
            if (i == index_to_add)
                darray_add(cpy_line, selected_warehouse);
            darray_add(*new_warehouse_solution, cpy_line);
        }
        return 1;
    }
    return 0;
}

Node*** copy_solution(Node*** solution){
    Node *** new_solution = darray_create(darray_size(solution), sizeof(Node**));
    for (size_t i = 0; i < darray_size(solution); i++){
        Node** line = darray_create(darray_size(solution[i]), sizeof(Node*));
        for (size_t j = 0; j < darray_size(solution[i]); j++){
            darray_add(line, solution[i][j]);
        }
        darray_add(new_solution, line);
    }
    return new_solution;
}

//build all the possible solutions and return the best one with it score
Node*** choose_drone_naive_aux(struct Drone** drones, Node*** deliveries, size_t* actual_index, Node*** solution, float* score, size_t** all_edited_indexs){

    //End of the recursion
    if (*actual_index == darray_size(deliveries)){
        float max_score = 0;
        for (size_t i = 0; i < darray_size(drones); i++){
            struct Node* ancient = solution[i][0];
            float total_score = 0;
            for (size_t j = 1; j < darray_size(solution[i]); j++){
                total_score += cost_between(ancient, solution[i][j]); //EDIT
                ancient = solution[i][j]; //EDIT
            }
            if (total_score > max_score){
                max_score = total_score;
            }
        }
        
        *score = max_score;
        return solution;
    }

    //Initialize the variables to stock the best result
    Node*** best_solution = NULL;
    float best_score = 0;
    size_t best_depth = *actual_index;
    size_t* best_indexs_edited;

    for (size_t d = 0; d < darray_size(drones); d++){
        //check if we can create a new solution and create it iif it is the case
        Node*** new_solution;
        if (good_warehouse(solution[d], deliveries[*actual_index]) && 
            create_new_solution(solution, deliveries[*actual_index][0], d, drones[d], &new_solution)){ //EDIT

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
        float max_score = 0;
        for (size_t i = 0; i < darray_size(drones); i++){
            struct Node* ancient = solution[i][0];
            float total_score = 0;
            for (size_t j = 1; j < darray_size(solution[i]); j++){
                total_score += cost_between(ancient, solution[i][j]); //EDIT
                ancient = solution[i][j]; //EDIT
            }
            if (total_score > max_score){
                max_score = total_score;
            }
        }
        
        *score = max_score;
        return solution;
    }

    partial_free_solution_parent(solution, &best_indexs_edited, all_edited_indexs);
    *all_edited_indexs = best_indexs_edited;

    //return the best solution
    *score = best_score;
    *actual_index = best_depth;
    return best_solution;
}

char good_warehouse(Node** drone_path, Node** delivery){
    for (size_t i = 1; i < darray_size(delivery); i++){
        if (delivery[i] == drone_path[0]){
            return 1;
        }
    }
    return 0;
}

//check if the new solution can be created, if it is the case it create a copy of the solution with the new element
//solution : liste de listes de pointeurs sur nodes (ancienne solution implémentée)
//new_element : un pointeur sur le nouveau Node à ajouter
//drone_to_add : l'index de du chemin qui doit etre modifié
// drone : le drone qui doit prendre la nouvelle livraison
//new_solution : pointeur pour return la 
char create_new_solution(Node*** solution, Node* new_element, size_t drone_to_add, struct Drone* drone, Node**** new_solution){

    //copy and add the element
    Node** drone_to_edit = darray_create(darray_size(solution[drone_to_add]), sizeof(Node*));
    char changed = 0;
    uint32_t min_insert = 0;
    uint32_t min_actual = 0;
    size_t index_edit = 0;

    Node* ancient = solution[drone_to_add][0];
    for (size_t i = 1; i < darray_size(solution[drone_to_add]); i++){
        darray_add(drone_to_edit, solution[drone_to_add][i]);

        if (ancient->type == 1 || ancient->content.delivery->user_priority >= new_element->content.delivery->user_priority){
            if (solution[drone_to_add][i]->content.delivery->user_priority >= new_element->content.delivery->user_priority){
                min_actual = cost_between(ancient, new_element) + 
                            cost_between(new_element, solution[drone_to_add][i]) -
                            cost_between(ancient, solution[drone_to_add][i]); //OPTI : stoquer cette information
                if (changed == 0 || min_insert > min_actual){
                    min_insert = min_actual;
                    index_edit = i;
                    changed = 1;
                }
            }
        }
        ancient = solution[drone_to_add][i];
    }

    if (changed == 0){
        if (ancient->type == 1 || ancient->content.delivery->user_priority >= new_element->content.delivery->user_priority){
            darray_add(drone_to_edit, new_element);
            changed = 1;
        }
    }
    else{
        darray_insert(drone_to_edit, index_edit - 1, new_element);
    }
    


    //check if the solution can exist
    if (changed != 0 && can_handle(drone, darray_size(drone_to_edit), drone_to_edit, drone->max_speed) > 0){ //EDIT (que j'ai edit)
        darray_insert(drone_to_edit, 0, solution[drone_to_add][0]);
        //copy all the list
        *new_solution = darray_create(darray_size(solution), sizeof(Node**));
        for (size_t i = 0; i < darray_size(solution); i++){
            if (i == drone_to_add){
                darray_add(*new_solution, drone_to_edit);
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

//find the link between the start node and the next node
float cost_between(Node* start, Node* next){
    if (next->type == E_WAREHOUSE){
        for (size_t i = 0; i < start->nb_edges; i++){
            if (start->edges[i].next->type == E_WAREHOUSE && start->edges[i].next->content.warehouse->id == next->content.warehouse->id)
                return start->edges[i].cost;
        }
    }
    else{
        for (size_t i = 0; i < start->nb_edges; i++){
            if (start->edges[i].next->type == E_DELIVERY && start->edges[i].next->content.delivery->id == next->content.delivery->id){
                return start->edges[i].cost;
            }     
        }
    }
    return -1;
}

//prend une solution et free ce qui est modifié par le parent et le son (listes de pointeurs sur indexs) => modifie le son pour qu'il contienne aussi les éléments du parent
void partial_free_solution_parent(Node*** solution, size_t** modified_son, size_t** modified_parent){
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

//prend une solution et free ce qui est modifié (modified : liste d'indexs)
void partial_free_solution(Node*** solution, size_t* modified){
    for (size_t i = 0; i < darray_size(modified); i++){
        darray_clear(solution[modified[i]]);
        darray_destroy(solution[modified[i]]);
    }
    darray_clear(solution);
    darray_destroy(solution);
}


//free an darray of darray
void free_darray_matrice(void** array){
    for (size_t k = 0; k < darray_size(array); k++){
        darray_clear(array[k]);
        darray_destroy(array[k]);
    }
    darray_destroy(array);
}





/*
int main(void){
    // Création de deux drones
    struct Position position_drone = { .x = 0, .y = 0 };
    struct Drone* drone = malloc(sizeof(*drone));
    *drone = (struct Drone){
        0, 1000, 100, 100, 100, 100.0f,
        100, 100, 100, position_drone,
        darray_create(10,sizeof(struct Delivery*)), 0
    };

    struct Position position_drone2 = { .x = 10, .y = 0 };
    struct Drone* drone2 = malloc(sizeof(*drone));
    *drone = (struct Drone){
        0, 1000, 100, 100, 100, 100.0f,
        100, 100, 100, position_drone2,
        darray_create(10,sizeof(struct Delivery*)), 0
    };

    Drone** array_drones = darray_create(10, sizeof(Drone*));
    darray_add(array_drones, drone);
    darray_add(array_drones, drone2);


    // === Deliveries ===
    struct Delivery* delivery2 = malloc(sizeof(*delivery2));
    delivery2->position = (struct Position){1,0};
    delivery2->user_priority = 1;
    delivery2->mass = 10;

    Node* node1 = malloc(sizeof(*node1));
    node1->content.delivery = delivery2;
    node1->type = E_DELIVERY;
    node1->nb_edges = 0;
    node1->edges = NULL;

    struct Delivery* delivery3 = malloc(sizeof(*delivery3));
    delivery3->position = (struct Position){2,0};
    delivery3->user_priority = 1;
    delivery3->mass = 10;

    Node* node2 = malloc(sizeof(*node2));
    node2->content.delivery = delivery3;
    node2->type = E_DELIVERY;
    node2->nb_edges = 0;
    node2->edges = NULL;

    struct Delivery* delivery4 = malloc(sizeof(*delivery4));
    delivery4->position = (struct Position){2,0};
    delivery4->user_priority = 1;
    delivery4->mass = 10;

    Node* node3 = malloc(sizeof(*node3));
    node3->content.delivery = delivery4;
    node3->type = E_DELIVERY;
    node3->nb_edges = 0;
    node3->edges = NULL;

    Node* node4 = malloc(sizeof(*node4));
    node4->content.delivery = delivery3;
    node4->type = E_DELIVERY;
    node4->nb_edges = 0;
    node4->edges = NULL;


    // === Warehouses ===
    Warehouse* warehouse = malloc(sizeof(Warehouse));
    warehouse->id = 0;
    warehouse->pos = (struct Position){11,0};
    warehouse->item_count = 1;

    Node* wnode1 = malloc(sizeof(*wnode1));
    wnode1->content.warehouse = warehouse;
    wnode1->type = E_WAREHOUSE;
    wnode1->edges = NULL;
    wnode1->nb_edges = 0;

    Warehouse* warehouse1 = malloc(sizeof(Warehouse));
    warehouse1->id = 1;
    warehouse1->pos = (struct Position){11,0};
    warehouse1->item_count = 1;

    Node* wnode2 = malloc(sizeof(*wnode2));
    wnode2->content.warehouse = warehouse1;
    wnode2->type = E_WAREHOUSE;
    wnode2->edges = NULL;
    wnode2->nb_edges = 0;


    // === Edges (simplifiés) ===
    Edge* array_wh1 = calloc(2, sizeof(Edge));
    array_wh1[0].cost = 1; array_wh1[0].next = node1;
    array_wh1[1].cost = 1; array_wh1[1].next = node2;
    wnode1->edges = array_wh1;
    wnode1->nb_edges = 2;

    Edge* array_wh2 = calloc(2, sizeof(Edge));
    array_wh2[0].cost = 1; array_wh2[0].next = node2;
    array_wh2[1].cost = 1; array_wh2[1].next = node3;
    wnode2->edges = array_wh2;
    wnode2->nb_edges = 2;


    // === Deliveries list ===
    Node** array_deliveries = darray_create(10, sizeof(Node*));
    darray_add(array_deliveries, wnode1);
    darray_add(array_deliveries, wnode2);

    printf("%zu\n", darray_size(array_deliveries));


    // === Call algorithm ===
    Node*** result =
        choose_drone_naive(array_drones, array_deliveries,
                           darray_size(array_deliveries));


    // === Display result ===
    if (result != NULL) {
        printf("%zu\n", darray_size(result));
        for (size_t i = 0; i < darray_size(result); i++){
            printf("\t%zu\n", darray_size(result[i]));
            for (size_t j = 0; j < darray_size(result[i]); j++){
                if (result[i][j] && result[i][j]->type == E_DELIVERY)
                    printf("\t(delivery at %d,%d)\n",
                           result[i][j]->content.delivery->position.x,
                           result[i][j]->content.delivery->position.y);
            }
            printf("\n");
        }
    }


    // === Free ===

    free(array_wh1);
    free(array_wh2);

    if (result)
        free_darray_matrice((void**)result);

    darray_clear(array_deliveries);
    darray_destroy(array_deliveries);

    darray_clear(array_drones);
    darray_destroy(array_drones);

    free(node1);
    free(node2);
    free(node3);
    free(node4);
    free(wnode1);
    free(wnode2);

    free(delivery2);
    free(delivery3);
    free(delivery4);

    free(warehouse);
    free(warehouse1);

    printf("end\n");
    return 0;
}
    */
