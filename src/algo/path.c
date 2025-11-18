#include "path.h"
#include "darray.h"
#include <stdlib.h>


//Actual pb : drones[0] = 0xbebebebebebebebe : check here
struct Delivery*** build_final_array(struct Drone** drones, size_t size_drones, struct Delivery** input_list_deliveries, size_t* input_list_drones, size_t input_index, uint32_t* min){
    uint32_t* values_drones_array = calloc(size_drones, sizeof(uint32_t));
    struct Delivery*** output_array = darray_create(size_drones, sizeof(Delivery**));

    for (size_t i = 0; i < size_drones; i++){
        values_drones_array[i] = drones[i]->cost;
        darray_add(output_array, darray_create(5, sizeof(Delivery*)))
    }

    for (size_t i = 0; i < input_index; i++){
        values_drones_array[input_list_drones[i]] += weight(drones[input_list_drones[i]], input_list_deliveries[i], 0);
        darray_add(output_array[input_list_drones[i]], input_list_deliveries[i]);
    }

    //It is possiblie to change that part and find the max instead of the addition
    *min = 0;
    for (size_t i = 1; i < size_drones; i++){
        *min += values_drones_array[i];
    } 

    free(values_drones_array);
    return output_array;
}


struct Delivery*** choose_drone_naive_aux(struct Drone** drones, size_t drone_size, struct Delivery** deliveries, 
    size_t deliveries_size, uint32_t* min, struct Delivery** input_list_deliveries, size_t* input_list_drones, size_t* input_index){
    struct Delivery*** output_array;

    //end case, no delivery left
    if (deliveries_size == 0){
        output_array = build_final_array(drones, drone_size, input_list_deliveries, input_list_drones, *input_index, min);
        return output_array;
    }

    uint32_t output_min = *min;
    size_t output_index = *input_index;


    struct Delivery** deliveries_call = darray_create(deliveries_size - 1, sizeof(struct Delivery*));

    char at_least_one_solution = 0;

    for (size_t i = 0; i < drone_size; i ++){
        for (size_t j = 0; j < deliveries_size; j++){
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
            for (size_t k = 0; k < deliveries_size; k++){
                if (k == j)
                    offset = 1;
                else
                    deliveries_call[k - offset] = deliveries[k];
            }

            uint32_t actual_min = 0;
            size_t index = *input_index + 1;

            struct Delivery*** actual_array = choose_drone_naive_aux(drones, drone_size, deliveries_call, deliveries_size - 1, &actual_min, input_list_deliveries, input_list_drones, &index);

            if (index < output_index || output_min == 0 || (index == output_index && actual_min < output_min)){
                output_index = index;
                output_min = actual_min;

                if (output_array  != NULL){
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

    

    if (at_least_one_solution == 0){
        output_array = build_final_array(drones, drone_size, input_list_deliveries, input_list_drones, *input_index, min);
    }
    else{
        *min = output_min;
        *input_index = output_index;
    }

    darray_clear(deliveries_call);
    darray_destroy(deliveries_call);

    return output_array;

    
}



struct Delivery*** choose_drone_naive(struct Drone** drones, size_t drone_size, struct Delivery** deliveries, size_t deliveries_size){
    uint32_t min = 0;
    size_t input_index = 0;
    size_t size_deliveries = deliveries_size;

    struct Delivery** input_list_deliveries = darray_create(size_deliveries, sizeof(struct Delivery*));
    size_t* input_list_drones = darray_create(size_deliveries, sizeof(size_t));

    struct Delivery*** output_array = choose_drone_naive_aux(drones, drone_size, deliveries, deliveries_size, &min, input_list_deliveries, input_list_drones, &input_index);

    darray_clear(input_list_deliveries);
    darray_destroy(input_list_deliveries);
    darray_clear(input_list_drones);
    darray_destroy(input_list_drones);

    return output_array;
}




int main(){
    struct Position position_drone = {0, 0, 0};
    struct Drone* drone = new_drone(100, 100, 100, 100, 100, 100, 100, 100, &position_drone, darray_create(10,sizeof(Delivery*)), 0, 0);
    Drone** array_drone = darray_create(10, sizeof(Drone*));
    darray_add(array_drone, drone);


    struct Position position_delivery = {100, 100, 100};
    struct Item item_delivery = {"test", 1};
    struct Delivery* delivery = new_delivery(&item_delivery, 1, 1, &position_delivery, 10);
    Delivery** array_deliveries = darray_create(10, sizeof(Delivery*));
    darray_add(array_deliveries, delivery);

    choose_drone_naive(array_drone, 1, array_deliveries, 1);



    darray_clear(array_deliveries);
    darray_destroy(array_deliveries);

    

    darray_clear(drone->targets);
    darray_destroy(drone->targets);

    darray_clear(array_drone);
    darray_destroy(array_drone);
}