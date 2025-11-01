#! /usr/bin/env python

import networkx as nx
import sys
import random
import math

def compute_distance(a, b):
    diffx = a[0] - b[0]
    diffy = a[1] - b[1]
    diffz = a[2] - b[2]
    return math.sqrt(diffx * diffx + diffy * diffy + diffz * diffz)

def random_coords():
    return tuple(random.uniform(-200, 200) for _ in range(3))

def gen_rand_graph(num_nodes: int):
    G = nx.Graph()
    half = int(num_nodes / 2)
    for i in range(half):
        G.add_node(i, pos=random_coords(), is_drone = True)

    for i in range(half, num_nodes):
        G.add_node(i, pos=random_coords(), is_drone = False)

    for i in range(half):
        for j in range (half, num_nodes):
            G.add_edge(i, j, distance=compute_distance(G.nodes[i]['pos'], G.nodes[j]['pos']))

    return G

G = gen_rand_graph(int(sys.argv[1]))
with open(sys.argv[2], 'wb') as f:
    nx.write_gml(G, f)
