#pragma once

#include <math.h>
#include <stdio.h>
#include <stdlib.h>


#define MAX_DELIVERY_PER_DRONE 5


struct Position{
    double x;
    double y;
};

struct Delivery{
    //Propre à l'objet
    char* obj;
    unsigned int priority;
    struct Position* position;
    double mass;
};

struct Drone{
    //Propre à l'objet
    double max_capacity;
    double max_autonomy;
    double max_speed;
    double acceleration;

    //En temps réel
    double actual_capacity;
    double actual_autonomy;
    struct Position* position;
    struct Delivery* targets[MAX_DELIVERY_PER_DRONE];
    size_t nb_targets;

    //Pour le programme
    double cost;
};



struct Delivery* build_delivery(char* obj, unsigned int priority, struct Position* position, double mass);

struct Drone* build_drone(struct Position* position, double capacity, double autonomy, double speed, double acceleration);

double Distance(struct Position* position1, struct Position* position2);

double Weight(struct Drone* drone, struct Delivery* delivery, double distance);

int add_target(struct Drone* drone, struct Delivery* delivery);

int can_handle_delivery(struct Drone* drone, struct Delivery* delivery);