#ifndef GRAPH_H
#define GRAPH_H

#include "algo/cutter.h"
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
	EdgeIndex* edges;
	size_t nb_edges;
    bool visited;
} Node;

struct Edge {
	float cost;
	Position *pos;	// Intermediary position due to constraints
	uint8_t nb_pos;
    NodeIndex next;
};

NodeIndex* to_graph(ClusterIndex* cluster_indices, uint16_t nb_cluster);
size_t count_edges(Cluster* clt);
float Weight(Delivery* delivery, uint32_t dist);
Edge link_single(Position pos, Delivery* del);
void link_deliveries(Delivery* del1, Delivery* del2);
void link_archetypes(Archetype* at1, Archetype* at2);
void link_intra_archetype(Archetype* at, NodeIndex wh, uint32_t* i_wh_edge);

#endif /* ! GRAPH_H */
