#! /usr/bin/env python

import networkx as nx
import matplotlib.pyplot as plt
import random
import math
import sys
import numpy as np
import utils

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


if (len(sys.argv) == 1):
    #raise Exception("error, you must give a gml graph in argument if you want to create a graph")
    print("if you want to create a graph, give on in argument (.gml)")

else:
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
        allocations.append((int(shortest_edge[1]), i)) #very pygame oriented. The paint() methods take pygame.Surfaces, the event() methods take pygame.Events.pgu is easy to extend with your own pygame based widgets.


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







#Baptiste's version


def choose_drones_with_priority(drones:list[utils.Drone], deliveries:list[utils.Delivery]):
    while (deliveries != []):
        min_weight:float = -1
        min_drone:utils.Drone = None
        min_index:int = 0
        for i in range(len(deliveries)):
            for drone in  drones:
                drone_weight:float = utils.weight(drone, deliveries[i])
                if drone.can_handle_delivery(deliveries[i]) and (min_weight < 0 or drone_weight < min_weight):
                    min_weight = drone_weight
                    min_drone = drone
                    min_index = i
            
        if min_drone == None:
            return False
        
        min_drone.add_target(deliveries[min_index])
        del deliveries[min_index]

    return True




def choose_drones_naive_aux(drones:list[utils.Drone], deliveries:list[utils.Delivery], tab:dict[utils.Drone:list[utils.Delivery]] = []):
    min = 0
    tab_min = tab
    deliveries_left = deliveries
    for i in range(len(deliveries)):
        for j in range(len(drones)):
            if drones[j].can_handle_delivery(deliveries[i]):
                drone_value,drone_tab,drone_deliveries = choose_drones_naive_aux(drones, deliveries[:i] + deliveries[i + 1:], tab + [(drones[j], deliveries[i])])
                if min == 0 or drone_value < min:
                    min = drone_value
                    tab_min = drone_tab
                    deliveries_left = drone_deliveries

    if min == 0:
        max = 0
        weights = {drone:(drone.weight(),drone.last_position()) for drone in drones}
        for drone,delivery in tab:
            weights[drone] = (weights[drone][0] + utils.distance(weights[drone][1], delivery.position), delivery.position)
        
        for weight in weights.values():
            if weight[0] > max:
                max = weight[0]
        min = max 
            

    return min,tab_min,deliveries_left


def choose_drones_naive(drones:list[utils.Drone], deliveries:list[utils.Delivery]):
    returned_value = choose_drones_naive_aux(drones, deliveries)
    for drone,delivery in returned_value[1]:
        drone.add_target(delivery)
    return returned_value[2]



#Simple test of the function choose_drones_for_deliveries

drone1 = utils.Drone(capacity=10, max_speed=1, acceleration=1, autonomy=100, position=(0,0))
drone2 = utils.Drone(capacity=10, max_speed=1, acceleration=1, autonomy=100, position=(4,0))
drones = [drone1,drone2]

delivery1 = utils.Delivery(obj="default_item_1", mass=1, position=(1,0), priority=2)
delivery2 = utils.Delivery(obj="default_item_2", mass=1, position=(2.1,0), priority=2)
delivery3 = utils.Delivery(obj="default_item_3", mass=1, position=(3,0), priority=0)
deliveries = [delivery1, delivery2, delivery3]

"""
if(not choose_drones_with_priority(drones, deliveries)):
    print("The drone do not have enought space to hanle every deliveries")
"""
deliveries = choose_drones_naive(drones, deliveries)

for i in range (len(drones)):
    print(f"drone {i} : {drones[i].targets}")

print(f"deliveries left ({len(deliveries)}) : {deliveries}")