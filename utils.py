import math

class Delivery:
    def __init__(self, obj:str, mass:float, position:(float, float), priority:float):
        self.object = obj
        self.mass = mass
        self.position = position
        self.priority = priority

    def draw(self, surface):
        pygame.draw.circle(surface, RED, (self.position[0], self.position[1]), 10)


class Drone:
    def __init__(self, capacity:float, max_speed:float, acceleration:float, autonomy:float, position:(float, float)):
        self.capacity = capacity
        self.max_speed = max_speed
        self.acceleration = acceleration
        self.autonomy = autonomy
        self.position = position
        self.target = None

    def draw(self, surface):
        pygame.draw.circle(surface, BLUE, (self.position[0], self.position[1]), 10)

    def move(self):
        if self.target:
            dx = self.target[0] - self.position[0]
            dy = self.target[1] - self.position[1]
            dist = math.sqrt(dx**2 + dy**2)
            if dist > 0:
                self.position = (self.position[0] + (dx / dist) * self.max_speed, self.position[1] + (dy / dist) * self.max_speed)
            if dist < 5:
                self.target = None

    def set_target(self, position):
        self.target = position


def distance(position1, position2):
    dx = position1[0] - position2[0]
    dy = position1[1] - position2[1]
    return math.sqrt(dx**2 + dy**2)

