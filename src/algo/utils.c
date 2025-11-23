#include "utils.h"
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

Delivery *new_delivery(Item *const item, const uint16_t quantity,
		const uint8_t priority, Position *const position, const uint32_t mass) {
	struct Delivery* del = malloc(sizeof(Delivery));

	del->item = item;
	del->quantity = quantity;
	del->priority = priority;
	del->position = position;
	del->mass = mass;

	return del;
}

Drone *new_drone(const uint32_t max_capacity, const uint8_t max_speed,
		const uint8_t acceleration, const float energy,
		const uint16_t max_flight_time, const uint8_t max_flight_time_speed,
		const uint32_t payload, const float autonomy, Position *const position,
		Delivery *const targets, const uint8_t nb_targets, float cost) {
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

uint32_t distance_2D(const Position *pos1, const Position *pos2) {
	float dx = pos2->x - pos1->x;
	float dy = pos2->y - pos1->y;
	return (uint32_t) sqrtf(dx * dx + dy * dy);
}

// distance in m, speed in m/s, charge in g
// Calculate the estimate consumption in Wh with the following formula :
// (distance * speed / max_flight_time * max_flight_time_speed * max_flight_time_speed) * energy 
// 		+ (charge / max_capacity) * (energy / 2)
// Indeed : 
// 		consumption(drone, max_flight_time * max_flight_time_speed, max_flight_time_speed, 0) = energy
// 		consumption(drone, 0, speed, charge) = 0
// 		consumption(drone, distance, 0, charge) = 0
// O consumption means that the drone can't flight under the current conditions
float consumption(Drone *drone, uint32_t distance, uint8_t speed, uint32_t charge) {
	float f1 = distance * speed;
	float f2 = drone->max_flight_time * drone->max_flight_time_speed * drone->max_flight_time_speed;
	float f3 = drone->max_capacity * 2;
	return distance && speed && drone->max_capacity ? (f1 / f2 + charge / f3) * drone->energy : 0;
}

// Return the remaining autonomy of the drone after delivering or
// a negative value if it can not be delivered.
// nb_deliveries must be strictly higher than 0
float can_handle(Drone *drone, uint8_t nb_deliveries, Delivery *deliveries[nb_deliveries], 
		uint8_t speed) {
	uint32_t distance, payload;
	payload = 0;
	float cons = 0;

	while (--nb_deliveries && cons < drone->autonomy && payload < drone->max_capacity) {
		payload += deliveries[nb_deliveries]->mass;
		distance = distance_2D(deliveries[nb_deliveries]->position, deliveries[nb_deliveries - 1]->position);
		cons += consumption(drone, distance, speed, payload);
	}
	
	payload += deliveries[0]->mass;
	
	if (drone->autonomy <= cons || drone->max_capacity < payload)
		return -1;

	distance = distance_2D(drone->position, deliveries[0]->position);
	cons += consumption(drone, distance, speed, payload);
		
	return drone->autonomy - cons;
}

// Calculate and return the distance added by conturning the constraint
Position* is_constrained(Route_constraint *cnst, Position *pos1, Position *pos2) {
	Position p12, p1C, intersect; // Vectors 1 -> 2, 1 -> cnsc->center
	
	p12.x = pos2->x - pos1->x;
	p12.y = pos2->y - pos1->y;

	p1C.x = (cnst->center)->x - pos1->x;
	p1C.y = (cnst->center)->y - pos1->y;

	float i = (float)(p12.x * p1C.x + p12.y * p1C.y) / (float)(p12.x * p12.x + p12.y * p12.y);

	intersect.x = p12.x * i + pos1->x;
	intersect.y = p12.y * i + pos1->y;

	return new_position(p12.x * i + pos1->x, p12.y * i + pos1->y, 0);
}

// TODO :
// 	- Poids entre les nœuds
// 	- Définir contrainte
// 	- Lier contraites et livraisons


/*
double Weight(struct Drone* drone, struct Delivery* delivery, double distance){ // distance = 0 if not calculated before
    double dist = drone->cost;
    if (distance == 0)
        dist += Distance(drone->position, delivery->position);
    else
        dist += distance;
    return dist * (delivery->priority + 1) * 0.5f / drone->max_speed;
}

*/