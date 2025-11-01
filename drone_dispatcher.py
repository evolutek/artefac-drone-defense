from typing import List
import math
from utils import *

waiting_drones: List[Drone] = []
running_drones: List[Drone] = []
waiting_delivery_points: List[Delivery] = []
running_delivery_points: List[Delivery] = []

def delivery_with_greatest_prority() -> Delivery:
    greatest_priority : float = 0;
    point_idx: int = -1
    for i in range(len(waiting_delivery_points)):
        d : Delivery = waiting_delivery_points[i]
        if d.priority > priority:
            point_idx = i
            greatest_priority = d.priority
    
    return waiting_delivery_points.pop(i)

def delivery_closest(drone: Drone) -> Delivery:
    min_distance = math.inf
    point_idx: int = -1
    for i in range(len(waiting_delivery_points)):
        point : Delivery = waiting_delivery_points[i]
        dist: float = distance(point.position, drone.position)
        if dist > min_distance:
            point_idx = i
            min_distance = dist
    
    return waiting_delivery_points.pop(i)

def select_destination() -> Delivery:
    # self explanatory
    return delivery_with_greatest_prority()
    # return delivery_closest(drone)

    # Delivery point which was added first
    # return waiting_delivery_points.pop()

def launch_delivery(drone: Drone):
    """Launches a delivery.
    The drone and delivery point passed to this function are hints; another drone may be allocated to deliver the given point.
    """

    point = select_destination()

    running_delivery_points.append(point)
    running_drones.append(drone)
    drone.target = point
    

def add_drone(drone: Drone):
    if len(waiting_delivery_points) > 0:
        point = waiting_delivery_points.pop()
        launch_delivery(drone, point)
    else:
        waiting_drones.append(drone)

def add_delivery_point(point: Delivery):
    if len(waiting_drones) > 0:
        drone = waiting_drones.pop()
        launch_delivery(drone, point)
    else:
        waiting_delivery_points.append(point)

def mark_drone_as_free(drone: Drone):
    waiting_drones.append(drone)
    running_drones.remove(drone)
    running_delivery_points.remove(drone.target)
    drone.target = None
