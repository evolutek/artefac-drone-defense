#include "utils.h"

struct Delivery build_delivery(char* obj, unsigned int priority, double[2] position, double mass){
    struct Delivery d = malloc(sizeof(struct Delivery));

    d.obj = obj;
    d.priority = priority;
    d.position = position;
    d.mass = mass;

    return d;
}


struct Drone build_drone(double[2] position, double capacity, double autonomy, double speed, double acceleration, struct Delivery* targets, double weight){
    struct Drone d = malloc(sizeof(struct Drone));

    d.position = position;
    d.max_capacity = capacity;
    d.capacity = capacity
    d.max_autonomy = autonomy;
    d.autonomy = autonomy;
    d.max_speed = speed;
    d.acceleration = acceleration;
    d.targets = targets;
    d.weight = weight;

    return d;
}