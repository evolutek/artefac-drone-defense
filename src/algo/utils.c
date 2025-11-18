#include "utils.h"
#include "darray.h"
#include <math.h>
#include <stdlib.h>

Position *new_position(uint32_t x, uint32_t y, uint32_t z) {
	Position *pos = malloc(sizeof(Position));
	
	pos->x = x;
	pos->y = y;
	pos->z = z;
	
	return pos;
}

Item *new_item(char *name, uint32_t mass) {
	Item *item = malloc(sizeof(Item));
	
	item->name = name;
	item->mass = mass;

	return item;
}

Delivery *new_delivery(Item *const items, const uint16_t quantity,
		const uint8_t priority, Position *const position, const uint32_t mass) {
	struct Delivery* del = malloc(sizeof(Delivery));

	del->items = items;
	del->quantity = quantity;
	del->priority = priority;
	del->position = position;
	del->mass = mass;

	return del;
}

Drone *new_drone(const uint32_t max_capacity, const uint8_t max_speed,
		const uint8_t acceleration, const uint16_t energy,
		const uint16_t max_flight_time, const uint16_t max_flight_time_speed,
		const uint32_t payload, const uint16_t autonomy, Position *const position,
		Delivery **const targets,
		const uint8_t nb_targets, float cost) {
	Drone *drone = malloc(sizeof(Drone));

	drone->max_capacity = max_capacity;
	drone->max_speed = max_speed;
	drone->acceleration = acceleration;
	drone->energy = energy;
	drone->max_flight_time = max_flight_time;
	drone->max_flight_time_speed = max_flight_time_speed;
	
	drone->payload = payload;
	drone->autonomy = autonomy;
	drone->position = position;
	drone->targets = targets;
	drone->nb_targets = nb_targets;

	drone->cost = cost;

	return drone;
}

uint32_t distance(const Position *pos1, const Position *pos2) {
	float dx = pos2->x - pos1->x;
	float dy = pos2->y - pos1->y;
	return (uint32_t) sqrtf(dx * dx + dy * dy);
}

// TODO :
// 	- Poids entre les nœuds
// 	- Définir contrainte
// 	- Lier contraites et livraisons
// 	- Batterie
// 	- can_handle



double weight(struct Drone* drone, struct Delivery* delivery, uint32_t pre_calculated_dist){ // distance = 0 if not calculated before
    uint32_t dist = drone->cost;
    if (pre_calculated_dist == 0)
        dist += distance(drone->position, delivery->position);
    else
        dist += pre_calculated_dist;
    return dist * (delivery->priority + 1) * 0.5f / drone->max_speed;
}

int add_target(struct Drone* drone, struct Delivery* delivery){
    uint32_t dist = distance(drone->position, delivery->position);

	//add the delivery to the targets
	drone->payload -= delivery->mass;
	drone->autonomy -= dist;
	darray_add(drone->targets, delivery);
	drone->nb_targets ++;
	
	drone->cost += weight(drone, delivery, dist);
	drone->position = delivery->position;

	return 1;
}

int can_handle_delivery(struct Drone* drone, struct Delivery* delivery){
	return 1;
    //return drone->payload >= delivery->mass && drone->autonomy >= Distance(drone->position, delivery->position);
}

