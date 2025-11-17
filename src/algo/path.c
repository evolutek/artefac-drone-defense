#include "utils.h"
#include "path.h"
#include "darray.h"


//renvoi une liste de liste de livraisons (une liste par drone)
//prend une liste de drones et une liste de livraisons
//appel récurcivement en enlevant la premiere livraison (récupère la valeur, le nombre de livraisons restantes, la liste finale)

//à faire : une fonction du cas d'arret qui regarde toutes les combinaisons et qui remet la liste dans l'ordre
//testes pour vérifier si la liste fonctionne
//



struct Delivery*** build_final_array(struct Drone** drones, size_t size_drones, struct Deliveries** input_list_deliveries, struct Drones** input_list_drones, size_t input_index, unsigned double* min,){
    unsigned double* values_drones_array = calloc(size_drones, sizeof(unsigned double));
    struct Delivery*** output_array = darray_create(size_drones, sizeof(Delivery**));

    for (size_t i = 0; i < size_drones; i++){
        values_drones_array[i] = drones[i]->cost;
        output_array[i] = darray_create(5, sizeof(Delivery*));
    }

    for (size_t i = 0; i < input_index; i++){
        values_drones_array[input_list_drones[i]] += weight(drones[input_list_drones[i]], input_list_deliveries[i], 0);
        darray_add(output_array[input_list_drones[i]], input_list_deliveries[i]);
    }

    //It is possiblie to change that part and find the max instead of the addition
    *min = 0;
    for (size_t i = 1; i < size_drones; i++){
        min += values_drones_array[i];
    } 

    free(values_drones_array);
    return output_array;
}


struct Delivery*** choose_drone_naive_aux(struct Drone** drones, struct Delivery** deliveries, unsigned double* min, struct Deliveries** input_list_deliveries, struct size_t* input_list_drones, size_t* input_index){ //Qu'est ce qui est nécéssaire en parametre ?

    struct darray_header* header_deliveries = ptr_offset_bytes(elements, -HEADER_SIZE);

    //end case, no delivery left
    if (deliveries->size == 0){
        output_array = build_final_array(drones, header_drones->size, input_list_deliveries, input_list_drones, *input_index, min);
        return output_array;
    }

    struct darray_header* header_drones = ptr_offset_bytes(elements, -HEADER_SIZE);

    double output_min = *min; //récupère le minimum actuel pour comparer et s'arreter suffisament tôt
    struct Deliveries*** output_array; //construit la liste de sortie, ajout de la liste d'entrée
    size_t output_index = input_index;


    size_t size_deliveries_call = header_deliveries->size - 1;
    struct Deliveries** deliveries_call = darray_create(header_deliveries->size - 1, sizeof(struct Deliveries*));

    char at_least_one_solution = 0;

    for (size_t i = 0; i < header_drones->size, i ++){
        for (size_t j = 0; j < header_deliveries->size; j++){
            //Create a black list to avoid some of theses tests
            if (can_handle_delivery(drones[i], deliveries[j]) == 0){
                break;
            }
            else if(at_least_one_solution < 2)
                at_least_one_solution += 1;

            //add the selected action to the list
            input_list_deliveries[input_index] = deliveries[j];
            input_list_drones[input_index] = i;

            //create an array of all the deliveries left
            char offset = 0;
            for (size_t k = 0; k < header_deliveries->size; k++){
                if (k == j)
                    offset = 1;
                else
                    deliveries_call[k - offset] = deliveries[k];
            }

            unsigned double actual_min = 0;
            size_t index = input_index + 1;

            struct Delivery*** actual_array = choose_drone_naive_aux(drones, deliveries_call, &actaul_min, input_list_deliveries, input_list_drones, &index);

            if (index < output_index || output_min == 0 || (index == output_index && actaul_min < output_min)){
                output_index = index;
                output_min = actual_min;

                if(at_least_one_solution == 2){
                    darray_clear(output_array);
                    darray_destroy(output_array);
                }
                output_array = actual_array;
            }
            else{
                darray_clear(actual_array);
                darray_destroy(actual_array);
            }
        }
    }

    darray_clear(deliveries_call);
    darray_destroy(deliveries_call);

    if (at_least_one_solution == 0){
        output_array = build_final_array(drones, header_drones->size, input_list_deliveries, input_list_drones, *input_index, min);
    }
    else{
        *min = min_weight;
        *input_index = output_index;
    }
    return output_array;

    
}



struct Delivery*** choose_drone_naive(struct Drone** drones, struct Delivery** deliveries){
    unsigned double min = 0;
    size_t input_index = 0;
    size_t size_deliveries = ptr_offset_bytes(deliveries, -HEADER_SIZE)->size;
    struct Deliveries** input_list_deliveries = darray_create(size_deliveries, sizeof(struct Deliveries*));
    struct size_t* input_list_drones = darray_create(size_deliveries, sizeof(struct size_t));

    struct Deliveries*** output_array = choose_drone_naive_aux(drones, deliveries, &min, input_list_deliveries, &input_index);

    darray_clear(input_list_deliveries);
    darray_destroy(input_list_deliveries);
    darray_clear(input_list_drones);
    darray_destroy(input_list_drones);

    return output_array;
}
