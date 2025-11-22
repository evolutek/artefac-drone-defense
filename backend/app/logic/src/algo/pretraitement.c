#include "utils.h"


float weight(Position *pos, Delivery *del) {
	uint32_t distance = distance_2D(pos, del->position);
	return 0;
}

#include <stdio.h>
int main(void) {
	// ~DJI Mavic 4 Pro : https://www.dji.com/nl/mavic-4-pro/specs
	Drone *drone = new_drone(100, 0, 0, 95.3, 51 * 60, 32 / 3.6, 0, 0, NULL, NULL, 0, 0);

	Route_constraint c;
	c.center = new_position(30, 20, 0);
	c.radius = 16;
	Position *p1 = new_position(50, 60, 0);
	Position *p2 = new_position(-10, 0, 0);
	Position *p = is_constrained(&c, p1, p2);

	printf("x: %u\ny: %u\n", p->x, p->y);
	return 0;
}

