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

uint32_t count_edges(Cluster* clt);
float Weight(Delivery* delivery, uint32_t dist);
Edge link(Position pos, Delivery* del);
void link_deliveries(Delivery* del1, Delivery* del2);
void link_archetypes(Archetype* at1, Archetype* at2);
void link_intra_archetype(Archetype* at, Node* wh, uint32_t* i_wh_edge);
Node** to_graph(Cluster* clusters, uint16_t nb_cluster);

#endif /* ! GRAPH_H */
