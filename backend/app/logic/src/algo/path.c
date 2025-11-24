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


//prend une solution et free ce qui est modifié (modified : liste d'indexs)
void partial_free_solution(struct Node*** solution, size_t* modified){
    for (size_t i = 0; i < darray_size(modified); i++){
        darray_clear(solution[modified[i]]);
        darray_destroy(solution[modified[i]]);
    }
    darray_clear(solution);
    darray_destroy(solution);
}

//prend une solution et free ce qui est modifié par le parent et le son (listes de pointeurs sur indexs) => modifie le son pour qu'il contienne aussi les éléments du parent
void partial_free_solution_parent(struct Node*** solution, size_t** modified_son, size_t** modified_parent){
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

//find the link between the start node and the next node
float cost_between(Node* start, Node* next){
    for (size_t i = 0; i < start->nb_edges; i++){
        if (start->edges[i].next == next)
            return start->edges[i].cost;
    }
    return -1;
}



//check if the new solution can be created, if it is the case it create a copy of the solution with the new element
//solution : liste de listes de pointeurs sur nodes (ancienne solution implémentée)
//new_element : un pointeur sur le nouveau Node à ajouter
//drone_to_add : l'index de du chemin qui doit etre modifié
// drone : le drone qui doit prendre la nouvelle livraison
//new_solution : pointeur pour return la 

char create_new_solution(struct Node*** solution, Node* new_element, size_t drone_to_add, struct Drone* drone, struct Node**** new_solution){

    //copy and add the element
    struct Node** drone_to_edit = darray_create(darray_size(solution[drone_to_add]), sizeof(struct Node*));
    char changed = 0;
    uint32_t min_insert = 0;
    uint32_t min_actual = 0;
    size_t index_edit = 0;

    struct Node* ancient = solution[drone_to_add][0];
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
            if (solution[drone_to_add][i]->content.delivery->user_priority >= new_element->content.delivery->user_priority){
                darray_add(drone_to_edit, new_element);
            }
        }
    }
    else{
        darray_insert(drone_to_edit, index_edit - 1, new_element);
    }


    //check if the solution can exist
    if (changed == 0 || can_handle(drone, darray_size(drone_to_edit), drone_to_edit, drone->max_speed) > 0){ //EDIT (que j'ai edit)
        darray_insert(drone_to_edit, 0, solution[drone_to_add][0]);
        //copy all the list
        *new_solution = darray_create(darray_size(solution), sizeof(struct Node**));
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

char good_warehouse(Node** drone_path, Node** delivery){
    for (size_t i = 1; i < darray_size(delivery); i++){
        if (delivery[i] == drone_path[0]){
            return 1;
        }
    }
    return 0;
}


//build all the possible solutions and return the best one with it score
struct Node*** choose_drone_naive_aux(struct Drone** drones, struct Node*** deliveries, size_t* actual_index, struct Node*** solution, float* score, size_t** all_edited_indexs){

    //End of the recursion
    if (*actual_index == darray_size(deliveries)){
        float new_score = 0;
        for (size_t i = 0; i < darray_size(drones); i++){
            struct Position* ancient = drones[i]->position;
            for (size_t j = 0; j < darray_size(solution[i]); j++){
                new_score += cost_between(ancient, solution[i][j]); //EDIT
                ancient = solution[i][j]; //EDIT
            }
        }
        
        *score = new_score;
        return solution;
    }

    //Initialize the variables to stock the best result
    struct Node*** best_solution = NULL;
    float best_score = 0;
    size_t best_depth = *actual_index;
    size_t* best_indexs_edited;

    for (size_t d = 0; d < darray_size(drones); d++){

        //check if we can create a new solution and create it iif it is the case
        struct Node*** new_solution;
        if (good_warehouse(solution[d], deliveries[actual_index]) && 
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
        float new_score = 0;
        for (size_t i = 0; i < darray_size(drones); i++){
            struct Position* ancient = drones[i]->position;
            for (size_t j = 0; j < darray_size(solution[i]); j++){
                new_score += cost_between(ancient, solution[i][j]); //EDIT
                ancient = solution[i][j]; //EDIT
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




//create a copy with the drone->selected_warehouse
char create_new_solution_warehouse(struct Node*** warehouse_solution, size_t index_to_add, struct Drone* drone, struct Node* selected_warehouse, Node**** new_warehouse_solution){

    if (consumption(drone, distance_2D(drone->position, selected_warehouse->content->position), drone->max_speed, 0) < drone->autonomy){
        //copie
        *new_warehouse_solution = darray_create(darray_size(warehouse_solution), sizeof(Node**));
        for (size_t i = 0; i < darray_size(warehouse_solution); i++){
            struct Node** cpy_line = darray_create(darray_size(warehouse_solution[i]), sizeof(Node*));
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

//call choose_drone_naive as many times as needed
struct Node*** choose_drone_naive_warehouse(struct Drone** drones, size_t index, struct Node** warehouse, struct Node*** warehouse_solution, struct Node*** deliveries){

    //condition d'arrêt
    if (index == darray_size(drones)){
        //appel choose_drone_naive_aux

        size_t actual_index = 0;
        struct Node*** solution = darray_create(darray_size(drones), sizeof(Node**));
        size_t* all_edited_indexs = darray_create(darray_size(drones), sizeof(size_t));
        for (size_t i = 0; i < darray_size(drones); i++){
            darray_add(all_edited_indexs, i);
            darray_add(solution, darray_create(5, sizeof(Node*)));
        }
        float score = 0;

        struct Node*** result choose_drone_naive_aux(drones, deliveries, &actual_index, solution, &score, &all_edited_indexs);

        darray_clear(all_edited_indexs);
        darray_destroy(all_edited_indexs);

        return result;
    }

    //initialise les meilleurs scores
    size_t best_index = 0;
    float best_score = 0;
    struct Node*** best_result = NULL;

    for (size_t i = 0; i < darray_size(warehouse); i++){
        struct Node*** new_solution;
        if (create_new_solution_warehouse(warehouse_solution, index, drones[index], warehouse[i], &new_solution)){

            drones[index]->autonomy = drones[index]->energy; 
            struct Node*** result = choose_drone_naive_warehouse(drones, index + 1, warehouse, new_solution, deliveries);

            if (best_index == 0){
                best_index = actual_index;
                best_score = score;
                best_result = result;
            }
            else if (actual_index < best_index || score < best_score){
                best_index = actual_index;
                best_score = score;
                free_darray_matrice(best_result);
                best_result = result;
            }
        }
    }

    return best_result;
}


//take in argument a list of drones and a list of deliveries and return the best asignment
struct Node*** choose_drone_naive(struct Drone** drones, struct Node** warehouses, size_t size){

    //consreuire deliveries : une liste des livraisons et des entrepots qui peuvent y accéder
    //appel choose_drone_naive_warehouse

    //prend les drones 
    struct Node*** deliveries = darray_create(10, sizeof(struct Node**));
    for (size_t i = 0; i < size; i++){
        for (size_t j = 0; j < warehouses[i]->nb_edges; j++){
            warehouses[i]->edges[j].next->content.delivery //on a la livraison qu'on veut ajouter : regarder si elle est présente dans deliveries, sinon ajouter : faire une struct
            char found = 0;
            for (size_t k = 0; k < darray_size(deliveries), k++){
                if (warehouses[i]->edges[j].next->content.delivery = deliveries[k]){
                    darray_add(deliveries[k], warehouses[i]);
                    found = 1;
                    break;
                }
            }
            if (found == 0){
                darray_add(deliveries, warehouses[i]->edges[j].next->content.delivery);
                darray_add(deliveries[darray_size(deliveries)], warehouses[i]);
            }
            
            //recherche de si il existe
            //sinon l'ajouter
        }
    }

    struct Node*** warehouse_solution = darray_create(darray_size(drones), sizeof(struct Node**));
    for (size_t i = 0; i < darray_size(drones); i++){
        darray_add(warehouse_solution, darray_create(10, sizeof(struct Node*)));
    }

    Node*** result = choose_drone_naive_warehouse(drones, 0, warehouse, warehouse_solution, deliveries);

    //free tout ce que j'ai à free (qui n'est pas free par les autres fonctions)

    return result;
}






int main(void){
    struct Position position_drone = {0, 0, 0};
    struct Drone* drone = new_drone(1000, 100, 100, 100, 100, 100, 100, 100, &position_drone, darray_create(10,sizeof(Delivery*)), 0, 0);

    struct Position position_drone2 = {10, 0, 0};
    struct Drone* drone2 = new_drone(1000, 100, 100, 100, 100, 100, 100, 100, &position_drone2, darray_create(10,sizeof(Delivery*)), 0, 0);

    Drone** array_drones = darray_create(10, sizeof(Drone*));
    darray_add(array_drones, drone);
    darray_add(array_drones, drone2);

/*
    
    Delivery** array_deliveries = darray_create(10, sizeof(Delivery*));
    for (size_t i = 0; i < 18; i++){
        Position *position_delivery = malloc(sizeof(Position));
        position_delivery->x =  1 + i;
        position_delivery->y = 0;
        position_delivery->z = 0;


        Item *item_delivery = malloc(sizeof(Item));
        char buffer[32];
        snprintf(buffer, sizeof(buffer), "L%zu", 1 + i);

        item_delivery->name = strdup(buffer);
        item_delivery->mass = 1;

        Delivery *delivery = new_delivery(item_delivery, 1, 1, position_delivery, 10);
        darray_add(array_deliveries, delivery);
    }
        */


    struct Position position_delivery2 = {1, 0, 0};
    struct Item item_delivery2 = {"L1", 1};
    struct Delivery* delivery2 = new_delivery(&item_delivery2, 1, 1, &position_delivery2, 10);
    struct Node* node1 = {.content.delivery = delivery2, .type = 0, .edges = NULL, 1}; //changer edges et nb_edges quand tout sera défini

    struct Position position_delivery3 = {2, 0, 0};
    struct Item item_delivery3 = {"L2", 1};
    struct Delivery* delivery3 = new_delivery(&item_delivery3, 1, 1, &position_delivery3, 10);
    struct Node* node2 = {.content.delivery = delivery3, .type = 0, .edges = NULL, 1}; //changer edges et nb_edges quand tout sera défini
    struct Node* node4 = {.content.delivery = delivery3, .type = 0, .edges = NULL, 1}; //changer edges et nb_edges quand tout sera défini


    struct Position position_delivery = {11, 0, 0};
    struct Item item_delivery = {"W1", 1};
    struct Warehouse* warehouse = new_delivery(0, &item_delivery, 1, &position_delivery);
    struct Node* wnode1 = {.content.warehouse = warehouse, .type = 1, .edges = NULL, .nb_edges = 2};



    struct Position position_delivery4 = {2, 0, 0};
    struct Item item_delivery4 = {"L3", 1};
    struct Delivery* delivery4 = new_delivery(&item_delivery4, 1, 1, &position_delivery4, 10);
    struct Node* node3 = {.content.delivery = delivery4, .type = 0, .edges = NULL, .nb_edges = 1}; //changer edges et nb_edges quand tout sera défini


    struct Position position_delivery1 = {11, 0, 0};
    struct Item item_delivery1 = {"W2", 1};
    struct Warehouse* warehouse1 = new_delivery(0, &item_delivery1, 1, &position_delivery1);
    struct Node* wnode2 = {.content.warehouse = warehouse1, .type = 1, .edges = NULL, .nb_edges = 2};

    Edge e1 = {1, 0, 0, node1};
    Edge e2 = {1, 0, 0, node2};

    Edge e3 = {1, 0, 0, node2};
    Edge e4 = {1, 0, 0, node3};

    Edge e5 = {1, 0, 0, node1};

    Edge e6 = {1, 0, 0, node2};

    Edge e7 = {1, 0, 0, node3};

    Edge e8 = {1, 0, 0, node4};

    Edge* array_warehouse = calloc(2, sizeof(Edge));
    array_warehouse[0] = e1;
    array_warehouse[1] = e2;
    wnode1->edges = array_warehouse;

    Edge* array_warehouse2 = calloc(2, sizeof(Edge));
    array_warehouse2[0] = e3;
    array_warehouse2[1] = e4;
    wnode2->edges = array_warehouse2;

    Edge* array_delivery1 = calloc(2, sizeof(Edge));
    array_delivery1[0] = e6;
    node1->edges = array_delivery1;

    Edge* array_delivery2 = calloc(2, sizeof(Edge));
    array_delivery2[0] = e5;
    node2->edges = array_delivery2;

    Edge* array_delivery3 = calloc(2, sizeof(Edge));
    array_delivery3[0] = e7;
    node4->edges = array_array_delivery3delivery1;

    Edge* array_delivery4 = calloc(2, sizeof(Edge));
    array_delivery4[0] = e8;
    node3->edges = array_delivery4;



    
    Node** array_deliveries = darray_create(10, sizeof(Node*));
    darray_add(array_deliveries, warehouse);
    darray_add(array_deliveries, warehouse1);

    printf("%li\n", darray_size(array_deliveries));

    struct Delivery*** result = choose_drone_naive(array_drones, array_deliveries, darray_size(array_deliveries));

    printf("%zu\n", darray_size(result));
    for (size_t i = 0; i < darray_size(result); i++){
        printf("\t%zu\n", darray_size(result[i]));

        for (size_t j = 0; j < darray_size(result[i]); j++){
            printf("\t%s\n", result[i][j]->item->name);
        }

        printf("\n");
    }

    free(array_warehouse);
    free(array_warehouse2);
    free(array_delivery1);
    free(array_delivery2);
    free(array_delivery3);
    free(array_delivery4);


    for (size_t i = 0; i < darray_size(array_drones); i++){
        darray_clear(array_drones[i]->targets);
        darray_destroy(array_drones[i]->targets);
        free(array_drones[i]);
    }

    darray_clear(array_drones);
    darray_destroy(array_drones);


    free_darray_matrice((void**)result);


    for (size_t i = 0; i < darray_size(array_deliveries); i++){
        free(array_deliveries[i]->position);
        free(array_deliveries[i]->item->name);
        free(array_deliveries[i]->item);
        free(array_deliveries[i]);
    }

    darray_clear(array_deliveries);
    darray_destroy(array_deliveries);

    printf("end\n");

    return 1;
}