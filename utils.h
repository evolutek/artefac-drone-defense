//what do we need ?

// representation of drones
// representation of deliveries
// usefull functions 


struct Delivery{
    char* obj;
    unsigned int priority;
    double[2] position;
    double mass;
}

struct Drones{
    double max_capacity;
    double capacity;

    double max_autonomy;
    double autonomy;

    double max_speed;
    double acceleration;

    double[2] position;
    struct Delivery* targets;
    double weight;
}

struct Delivery build_delivery(char* obj, unsigned int priority, double[2] position, double mass);
struct Drone build_drone(double[2] position, double capacity, double autonomy, double speed, double acceleration, struct Delivery* targets, double weight);

//calcul dist
//calcul weight
//add target drone
//can handle delivery drone