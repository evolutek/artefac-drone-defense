#include "graph.h"
#include "algo/utils.h"
#include "cutter.h"
#include "utils/darray.h"
#include "utils/pool.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

NodeIndex* to_graph(ClusterIndex* cluster_indices, uint16_t nb_cluster) {
    // List of nb_cluster Node each representing a warehouse
    // Node** n_wh_darr = darray_create(nb_cluster, sizeof(Node *));
    NodeIndex* n_wh_darr = darray_create(nb_cluster, sizeof(NodeIndex));

    // For each cluster -> for each warehouse
    for (uint16_t i_clt = 0; i_clt < nb_cluster; i_clt++) {
        Cluster* clt = pool_query(&ctx.cluster_pool, cluster_indices[i_clt]);

        // Node of the warehouse
        Node n_wh = {
            .content.warehouse = pool_query(&ctx.warehouse_pool, clt->warehouse_idx),
            .type              = E_WAREHOUSE,
            .nb_edges          = count_edges(clt),
        };
        n_wh.edges = malloc(n_wh.nb_edges * sizeof(Edge));

        NodeIndex idx_wh;
        pool_add(&ctx.node_pool, Node, n_wh, idx_wh);
        n_wh_darr[i_clt] = idx_wh;

        uint32_t i_wh_edge = 0;
        size_t nb_at       = darray_size(clt->archetypes_darray);

        if (nb_at == 0)
            continue;

        // Creation of archetypes
        for (size_t i_at = 0; i_at < nb_at; i_at++) {
            Archetype* at = pool_query(&ctx.archetype_pool, clt->archetypes_darray[i_at]);
            link_intra_archetype(at, n_wh_darr[i_clt], &i_wh_edge);
        }

        // Linkage of archetypes
        for (size_t i1_at = 0; i1_at < nb_at - 1; i1_at++) {
            Archetype* at1 = pool_query(&ctx.archetype_pool, clt->archetypes_darray[i1_at]);
            size_t at_size = darray_size(at1->deliveries_darray);

            for (size_t i2_at = i1_at + 1; i2_at < at_size; i2_at++) {
                Archetype* at2 = pool_query(&ctx.archetype_pool, clt->archetypes_darray[i2_at]);
                link_archetypes(at1, at2);
            }
        }
    }

    return n_wh_darr;
}

// Links deliveries of different archetypes.
// All deliveries must have existing nodes.
void link_archetypes(Archetype* at1, Archetype* at2) {
    size_t at1_nb_del = darray_size(at1->deliveries_darray);
    size_t at2_nb_del = darray_size(at2->deliveries_darray);

    Delivery *del1, *del2;

    for (size_t i_at1 = 0; i_at1 < at1_nb_del; i_at1++) {
        del1 = pool_query(&ctx.delivery_pool, at1->deliveries_darray[i_at1]);

        for (size_t i_at2 = 0; i_at2 < at2_nb_del; i_at2++) {
            del2 = pool_query(&ctx.delivery_pool, at2->deliveries_darray[i_at2]);
            link_deliveries(del1, del2);
        }
    }
}

// Creates nodes for all deliveries and then links the deliveries and finally the warehouse
void link_intra_archetype(Archetype* at, NodeIndex wh_idx, uint32_t* i_wh_edge) {
    size_t nb_del = darray_size(at->deliveries_darray);
    printf("nb_del = %zu\n", nb_del);

    // Creation of all nodes
    for (size_t i_del = 0; i_del < nb_del; i_del++) {
        Delivery* del = pool_query(&ctx.delivery_pool, at->deliveries_darray[i_del]);
        Node* wh = pool_query(&ctx.node_pool, wh_idx);
        printf("nb_edges (wh) = %zu\n", wh->nb_edges);
        Node n_del    = {
               .content.delivery = del,
               .type             = E_DELIVERY,
               .edges            = malloc(wh->nb_edges * sizeof(EdgeIndex)),
               .nb_edges         = 0,
        };
        NodeIndex n_del_idx;
        pool_add(&ctx.node_pool, Node, n_del, n_del_idx);

        del->node = n_del_idx;
    }

    // Link between deliveries
    for (size_t i1_del = 0; i1_del < nb_del; i1_del++) {
        Delivery* del1 = pool_query(&ctx.delivery_pool, at->deliveries_darray[i1_del]);
        Delivery* del2;
        Node* wh = pool_query(&ctx.node_pool, wh_idx);

        EdgeIndex idx_edge;
        pool_add(&ctx.edge_pool, Edge, link_single(wh->content.warehouse->pos, del1), idx_edge);
        wh->edges[(*i_wh_edge)++] = idx_edge;
        for (size_t i2_del = i1_del + 1; i2_del < nb_del; i2_del++) {
            del2 = pool_query(&ctx.delivery_pool, at->deliveries_darray[i2_del]);
            link_deliveries(del1, del2);
        }
    }
}

void link_deliveries(Delivery* del1, Delivery* del2) {
    EdgeIndex idx_edge1, idx_edge2;
    Node* n1 = pool_query(&ctx.node_pool, del1->node);
    Node* n2 = pool_query(&ctx.node_pool, del2->node);
    if (del1->user_priority <= del2->user_priority) {
        pool_add(&ctx.edge_pool, Edge, link_single(del1->position, del2), idx_edge1);
        printf("nb_edges: %zu\n", n1->nb_edges);
        n1->edges[n1->nb_edges++] = idx_edge1;

        if (del1->user_priority == del2->user_priority) {
            pool_add(&ctx.edge_pool, Edge, link_single(del2->position, del1), idx_edge2);
            n2->edges[n2->nb_edges++] = idx_edge2;
        }
    } else {
        pool_add(&ctx.edge_pool, Edge, link_single(del2->position, del1), idx_edge2);
        n2->edges[n2->nb_edges++] = idx_edge2;
    }
}

Edge link_single(Position pos, Delivery* del) {
    Position last_pos = pos;
    float distance    = 0;

    Position* detours  = malloc(ctx.exclusion_zone_pool.size * sizeof(Position));
    uint8_t nb_detours = 0;

    // foreach dans l'ordre de proximité
    pool_foreach2(&ctx.exclusion_zone_pool, ExclusionZone, __attribute__((unused)) idx, zone) {
        Detour detour;
        if (is_constrained(zone, &last_pos, &del->position, &detour)) {
            last_pos = detour.pos;
            distance += detour.distance;
            detours[nb_detours++] = last_pos;
        }
    }

    return (Edge) {
        .cost   = Weight(del, distance),
        .pos    = detours,
        .nb_pos = nb_detours,
        .next   = del->node,
    };
}

// for each archetype of the warehouse, how much deliveries ?
size_t count_edges(Cluster* clt) {
    size_t res = 0;

    for (uint32_t arch = 0; arch < darray_size(clt->archetypes_darray); arch++) {
        Archetype* archetype = pool_query(&ctx.archetype_pool, clt->archetypes_darray[arch]);
        res += darray_size(archetype->deliveries_darray);
    }

    return res;
}

float Weight(Delivery* delivery, uint32_t dist) {
    return dist * (1.0f / (1.0f + expf(MIN_PRIORITY * 0.5f - delivery->priority)));
}
