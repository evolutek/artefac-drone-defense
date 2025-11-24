#ifndef GRAPH_H
#define GRAPH_H

#include "utils.h"
#include <stdint.h>

enum Node_type {
	E_DELIVERY,
	E_WAREHOUSE
};

typedef struct Edge Edge;

typedef struct Node {
	union {
		Delivery *delivery;
		Warehouse *warehouse;
	} content;
	enum Node_type type;
	Edge *edges;
	uint32_t nb_edges;
} Node;

struct Edge {
	float cost;
	Position *pos;	// Intermediary position due to constraints
	uint8_t nb_pos;
	Node *next;
};

#endif /* ! GRAPH_H */
