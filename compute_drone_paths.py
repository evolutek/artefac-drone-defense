#! /usr/bin/env python

import networkx as nx
import matplotlib.pyplot as plt
import random
import math
import sys
import numpy as np

class Destination:

    def __init__(self, node_idx, path, score):
        self.node_idx = node_idx
        self.score = score
        self.path = path

def compute_distance(a, b):
    diffx = a[0] - b[0]
    diffy = a[1] - b[1]
    diffz = a[2] - b[2]
    return math.sqrt(diffx * diffx + diffy * diffy + diffz * diffz)

G = nx.read_gml(sys.argv[1])
pos = {}
for n in G.nodes:
    position = G.nodes[n]['pos']
    pos[n] = np.array([position[0], position[1]])

allocations = []

node_count = len(G.nodes)
half = int(node_count / 2)
for i in range (half, node_count):
    shortest_edge = None
    shortest_distance = None
    for edge in G.edges(str(i)):
        if 'allocated' in G.nodes[edge[0]] or 'allocated' in G.nodes[edge[1]]:
            continue
        distance = G.edges[edge]['distance']
        if shortest_edge is None or distance < shortest_distance:
            shortest_distance = distance
            shortest_edge = edge
    closest_drone = G.nodes[shortest_edge[0]] if shortest_edge[0] != str(i) else G.nodes[shortest_edge[1]]
    closest_drone['allocated'] = i
    allocations.append((int(shortest_edge[1]), i))very pygame oriented. The paint() methods take pygame.Surfaces, the event() methods take pygame.Events.pgu is easy to extend with your own pygame based widgets.


print (allocations)


       
# for i in range(half):
#     shortest_path = nx.astar_path(G, start_node_idx, i, heuristic = lambda na, nb: compute_distance(G.nodes[na]['pos'], G.nodes[nb]['pos']), weight = 'distance')
#     total_distance = 0
#     for i in range(len(shortest_path) - 1):
#         total_distance += G.get_edge_data(shortest_path[i], shortest_path[i + 1])['distance']
#     destinations.append(Destination(i, shortest_path, total_distance))

subax1 = plt.subplot(121)
options = {"edgecolors": "tab:gray", "node_size": 800, "alpha": 0.9}
nx.draw_networkx_nodes(G, pos, nodelist=[str(i) for i in range(half)], node_color="tab:red", **options)
nx.draw(G, pos, with_labels=True, font_weight='bold')
plt.show()
