#include "path.h"
#include "darray.h"
#include <stdlib.h>


void free_darray_matrice(void** array){
    for (size_t k = 0; k < darray_size(array); k++){
        darray_clear(array[k]);
        darray_destroy(array[k]);
    }
    darray_destroy(array);
}

//Actual pb : drones[0] = 0xbebebebebebebebe : check here
struct Delivery*** build_final_array(struct Drone** drones, struct Delivery** input_list_deliveries, size_t* input_list_drones, size_t input_index, float* min){
    float* values_drones_array = calloc(darray_size(drones), sizeof(uint32_t));
    struct Delivery*** output_array = darray_create(darray_size(drones), sizeof(Delivery**));

    for (size_t i = 0; i < darray_size(drones); i++){
        values_drones_array[i] = drones[i]->cost;
        darray_add(output_array, darray_create(5, sizeof(Delivery*)));
    }

    for (size_t i = 0; i < input_index; i++){
        values_drones_array[input_list_drones[i]] += weight(drones[input_list_drones[i]], input_list_deliveries[i], 0);
        darray_add(output_array[input_list_drones[i]], input_list_deliveries[i]);
    }

    //It is possiblie to change that part and find the max instead of the addition
    *min = 0;
    for (size_t i = 1; i < darray_size(drones); i++){
        printf("ajoute dans min %f\n", values_drones_array[i]);
        *min += values_drones_array[i];
    } 

    free(values_drones_array);
    return output_array;
}


struct Delivery*** choose_drone_naive_aux(struct Drone** drones, struct Delivery** deliveries, 
    float* min, struct Delivery** input_list_deliveries, size_t* input_list_drones, size_t* input_index){
    struct Delivery*** output_array = NULL;

    //end case, no delivery left
    if (darray_size(deliveries) == 0){
        printf("passe dans la condition de fin : %zu\n", *input_index);
        output_array = build_final_array(drones, input_list_deliveries, input_list_drones, *input_index, min);
        return output_array;
    }

    float output_min = *min;
    size_t output_index = *input_index;


    struct Delivery** deliveries_call = darray_create(darray_size(deliveries) - 1, sizeof(struct Delivery*));
    for (size_t i = 0; i < darray_size(deliveries) - 1; i ++)
        darray_add(deliveries_call, NULL);

    char at_least_one_solution = 0;

    for (size_t i = 0; i < darray_size(drones); i ++){
        for (size_t j = 0; j < darray_size(deliveries); j++){
            //Create a black list to avoid some of theses tests
            if (can_handle_delivery(drones[i], deliveries[j]) == 0){
                break;
            }
            else if(at_least_one_solution < 2)
                at_least_one_solution += 1;

            //add the selected action to the list
            input_list_deliveries[*input_index] = deliveries[j];
            input_list_drones[*input_index] = i;

            //create an array of all the deliveries left
            char offset = 0;
            for (size_t k = 0; k < darray_size(deliveries); k++){
                if (k == j)
                    offset = 1;
                else
                    deliveries_call[k - offset] = deliveries[k];
            }

            float actual_min = 0;
            size_t index = *input_index + 1;

            struct Delivery*** actual_array = choose_drone_naive_aux(drones, deliveries_call, &actual_min, input_list_deliveries, input_list_drones, &index);

            if (index < output_index || output_min == 0 || (index == output_index && actual_min < output_min)){
                output_index = index;
                output_min = actual_min;
                
                if (output_array  != NULL){
                    free_darray_matrice((void**)output_array);
                }

                output_array = actual_array;
            }
            else{
                free_darray_matrice((void**)actual_array);
            }
        }
    }

    

    if (at_least_one_solution == 0){
        output_array = build_final_array(drones, input_list_deliveries, input_list_drones, *input_index, min);
    }
    else{
        *min = output_min;
        *input_index = output_index;
    }

    darray_clear(deliveries_call);  
    darray_destroy(deliveries_call);

    printf("%f\n", *min);

    return output_array;

    
}



struct Delivery*** choose_drone_naive(struct Drone** drones, struct Delivery** deliveries){
    float min = 0;
    size_t input_index = 0;

    struct Delivery** input_list_deliveries = darray_create(darray_size(deliveries), sizeof(struct Delivery*));
    size_t* input_list_drones = darray_create(darray_size(deliveries), sizeof(size_t));

    struct Delivery*** output_array = choose_drone_naive_aux(drones, deliveries, &min, input_list_deliveries, input_list_drones, &input_index);

    darray_clear(input_list_deliveries);
    darray_destroy(input_list_deliveries);
    darray_clear(input_list_drones);
    darray_destroy(input_list_drones);

    return output_array;
}




int main(){
    struct Position position_drone = {0, 0, 0};
    struct Drone* drone = new_drone(100, 100, 100, 100, 100, 100, 100, 100, &position_drone, darray_create(10,sizeof(Delivery*)), 0, 0);

    struct Position position_drone2 = {1, 0, 0};
    struct Drone* drone2 = new_drone(100, 100, 100, 100, 100, 100, 100, 100, &position_drone2, darray_create(10,sizeof(Delivery*)), 0, 0);

    Drone** array_drones = darray_create(10, sizeof(Drone*));
    darray_add(array_drones, drone);
    darray_add(array_drones, drone2);


    struct Position position_delivery = {10, 0, 0};
    struct Item item_delivery = {"test", 1};
    struct Delivery* delivery = new_delivery(&item_delivery, 1, 1, &position_delivery, 10);

    struct Position position_delivery2 = {0, 0, 0};
    struct Item item_delivery2 = {"test2", 1};
    struct Delivery* delivery2 = new_delivery(&item_delivery2, 1, 1, &position_delivery2, 10);

    Delivery** array_deliveries = darray_create(10, sizeof(Delivery*));
    darray_add(array_deliveries, delivery);
    darray_add(array_deliveries, delivery2);

    printf("%li\n", darray_size(array_deliveries));

    struct Delivery*** result = choose_drone_naive(array_drones, array_deliveries);

    printf("%zu\n", darray_size(result));
    for (size_t i = 0; i < darray_size(result); i++){
        printf("\t%zu\n", darray_size(result[i]));
        for (size_t j = 0; j < darray_size(result[i]); j++){
            printf("\t%s\n", result[i][j]->items->name);
        }
        printf("\n");
    }



    darray_clear(array_deliveries);
    darray_destroy(array_deliveries);

    for (size_t i = 0; i < darray_size(array_drones); i++){
        darray_clear(array_drones[i]->targets);
        darray_destroy(array_drones[i]->targets);
        free(array_drones[i]);
    }

    darray_clear(array_drones);
    darray_destroy(array_drones);


    free_darray_matrice((void*)result);

    free(delivery);
    free(delivery2);

    return 1;
}