import math
import pygame


# CLASSES

class Delivery:
    def __init__(self, obj:str, mass:float, position:tuple[float, float], priority:int):
        if priority < 0:
            raise Exception("priority must be greater than zero")
        if mass < 0:
            raise Exception("mass must be greater or equal to zero")
        
        self.object:str = obj
        self.mass:float = mass
        self.position:tuple[float, float] = position
        self.priority:int = priority

    def __str__(self): #when printed alone (to change depending on what you need to check)
        return f"Delivery <obj = {self.object}, mass = {self.mass}, pos = {self.position}, prio = {self.priority}>" 
    
    def __repr__(self): #when printed in a list,dict... (to change depending on what you need to check)
        return f"{self.position}" 
    

    def draw(self, surface):
        pygame.draw.circle(surface, pygame.RED, (self.position[0], self.position[1]), 10)


class Drone:
    def __init__(self, capacity:float, max_speed:float, acceleration:float, autonomy:float, position:tuple[float, float]):
        if capacity < 0:
            raise Exception("capacity must be greater or equal to zero")
        if max_speed <= 0:
            raise Exception("max_speed must be greater than zero")
        if autonomy <= 0:
            raise Exception("autonomy must be greater than 0")

        self.max_capacity:float = capacity
        self.capacity:float = capacity

        self.max_speed:float = max_speed
        self.acceleration:float = acceleration

        self.max_autonomy:float = autonomy
        self.autonomy:float = autonomy
        
        self.position:tuple[float, float] = position
        self.targets:list[Delivery] = []

        self.weight = 0

    def draw(self, surface):
        pygame.draw.circle(surface, pygame.BLUE, (self.position[0], self.position[1]), 10)

    def move(self):
        if self.targets != []:
            dx = self.targets[0].position[0] - self.position[0]
            dy = self.targets[0].position[1] - self.position[1]
            dist = math.sqrt(dx**2 + dy**2)
            if dist > 0:
                self.position = (self.position[0] + (dx / dist) * self.max_speed, self.position[1] + (dy / dist) * self.max_speed)
            if dist < 5:
                del self.targets[0]

    def add_target(self, delivery:Delivery):
        if not self.can_handle_delivery(delivery):
            return False
        
        self.targets.append(delivery)
        self.capacity -= delivery.mass
        self.autonomy -= distance(self.position, delivery.position) #if autonomy is a distance

        self.weight += distance(delivery.position, delivery.position) / self.max_speed
        self.position = delivery.position

        return True
    
    def can_handle_delivery(self, delivery:Delivery):
        return self.capacity >= delivery.mass and self.autonomy >= distance(self.position,delivery.position)
    
    def reset_drone(self):
        self.capacity = self.max_capacity
        self.autonomy = self.max_autonomy
    """
    def weight(self):
        dist = 0
        actual_pos = self.position
        for target in self.targets:
            dist += distance(actual_pos, target.position) / self.max_speed
            actual_pos = target.position
        return dist
    
    def last_position(self):
        if self.targets != []:
            return self.targets[-1].position
        return self.position
    """


# FUNCTIONS

def distance(position1, position2):
    dx = position1[0] - position2[0]
    dy = position1[1] - position2[1]
    return math.sqrt(dx**2 + dy**2)


#Do not take in account the acceleration
def weight(drone:Drone, delivery:Delivery):
    dist = drone.weight + distance(drone.position, delivery.position) 

    return dist * (delivery.priority + 1) * 0.5 / drone.max_speed # Add time




