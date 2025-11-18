#include "utils.h"
#include "repartition_and_attribution.h"


void Add_element_list(struct List, Delivery* element){
    if (List.max_size < List.size + 1){
        List.elements = realloc(List.elements, (max_size + 10) * sizeof(struct type));
    }
    List.element[size] = element;
    List.size ++;
}

void Remove_first_element(struct List){
    List.elements = List.elements + 1;
    //free here
}

struct List Create_list(void type){
    struct List list;

    list.size = 0;
    list.max_size = 10;
    list.elements = NULL;
    list.type = type;

    return list;
}

//à faire : une fonction du cas d'arret qui regarde toutes les combinaisons et qui remet la liste dans l'ordre
//testes pour vérifier si la liste fonctionne
//
struct Delivery*** Choose_drone_naive_aux(struct Drone** drones, size_t len_drones, struct Delivery** deliveries, size_t len_deliveries, double* min){
    double min_weight = *min; //récupère le minimum actuel pour comparer et s'arreter suffisament tôt
    struct List output_list = Create_list(Delivery**); //construit la liste de sortie
    size_t output_len_deliveries_left = len_deliveries;
    for (size_t i = 0; i < len_drones, i ++){
        //appel avec attribution dans de la delivery au drone
        //appel qui attend le minimum
        double actaul_min = 0;
        size_t len_deliveries_left = 0;
        //struct Delivery*** actual_list = Choose_drone_naive_aux(drones, len_drones, deliveries + 1, len_deliveries - 1, &actaul_min, &len_actual_list, output_list);
        
        if (output_len_deliveries_left < len_deliveries_left || (output_len_deliveries_left == len_deliveries_left && actaul_min < min_weight)){
            min_weight = actual_min;
            output_list = actual_list;
            len_actual_list = 0;
        }
    }
    //renvoyer le nombre d'éléments restants à la fin et la liste finale résultante (dans l'ordre) -> remettre dans l'ordre en testant
    *min = min_weight;
}



struct Delivery*** Choose_drone_naive(struct Drone** drones, size_t len_drones, struct Delivery** deliveries, size_t len_deliveries){
    struct List output_list = Create_list(Delivery**); //liste de sortie de base qui va etre remplit par les appels

    //dans les parametres : drones, deliveries, min pour descente, min pour montée, liste des deliveries restantes avec leur nombre, la liste finale à utiliser
}