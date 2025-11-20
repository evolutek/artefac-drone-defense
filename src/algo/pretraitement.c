#include "utils.h"


float weight(Position *pos, Delivery *del) {
	uint32_t distance = distance_2D(pos, del->position);
	return 0;
}

#include <stdio.h>
int main(void) {
	// ~DJI Mavic 4 Pro : https://www.dji.com/nl/mavic-4-pro/specs
	Drone *drone = new_drone(100, 0, 0, 95.3, 51 * 60, 32 / 3.6, 0, 0, NULL, NULL, 0, 0);

	printf("%f\n", consumption(drone, drone->max_flight_time * drone->max_flight_time_speed, 
				drone->max_flight_time_speed, 0));
	return 0;
}

