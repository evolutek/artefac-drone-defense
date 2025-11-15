#include "utils.h"



struct Delivery* build_delivery(char* obj, unsigned int priority, struct Position* position, double mass){
    struct Delivery* l = malloc(sizeof(struct Delivery));

    l->obj = obj;
    l->priority = priority;
    l->position = position;
    l->mass = mass;

    return l;
}

struct Drone* build_drone(struct Position* position, double capacity, double autonomy, double speed, double acceleration){
    struct Drone* d = malloc(sizeof(struct Drone));

    d->position = position;
    d->max_capacity = capacity;
    d->actual_capacity = capacity;
    d->max_autonomy = autonomy;
    d->actual_autonomy = autonomy;
    d->max_speed = speed;
    d->acceleration = acceleration;
    d->nb_targets = 0;
    d->cost = 0;

    return d;
}

double Distance(struct Position* position1, struct Position* position2){
    double dx = position2->x - position1->x;
    double dy = position2->y - position1->y;
    return sqrt(dx*dx + dy*dy);
}

double Weight(struct Drone* drone, struct Delivery* delivery, double distance){ // distance = 0 if not calculated before
    double dist = drone->cost;
    if (distance == 0)
        dist += Distance(drone->position, delivery->position);
    else
        dist += distance;
    return dist * (delivery->priority + 1) * 0.5f / drone->max_speed;
}

int add_target(struct Drone* drone, struct Delivery* delivery){
    double dist = Distance(drone->position, delivery->position);
    if (drone->actual_capacity < delivery->mass || drone->actual_autonomy < dist){
        //add the delivery to the targets
        drone->actual_capacity -= delivery->mass;
        drone->actual_autonomy -= dist;
        drone->targets[drone->nb_targets] = delivery;
        drone->nb_targets++;
        
        drone->cost += Weight(drone, delivery, dist);
        drone->position = delivery->position;

        return 1;
    }
    return 0; //fail
}

int can_handle_delivery(struct Drone* drone, struct Delivery* delivery){
    return drone->actual_capacity >= delivery->mass && drone->actual_autonomy >= Distance(drone->position, delivery->position);
}