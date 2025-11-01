import pygame
import math

# Initialisation de Pygame
pygame.init()

# Dimensions de la fenêtre
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simulation")

# Couleurs
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)

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


def attribution(drones, deliveries):
    drones[0].target = deliveries[0].position
    

def main():
    deliveries = [Delivery("Poche de sang", 0.5, (600,500), 1)]
    drones = [Drone(1, 1, 1, 1, (50,50))]
    tic = 0
    running = True
    clock = pygame.time.Clock()

    
    while running:
        tic += 1
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Dessin
        screen.fill(WHITE)

        attribution(drones, deliveries)
        for drone in drones:
            drone.move()

        # Dessin des drones et des points de livraison
        for drone in drones:
            drone.draw(screen)
        for point in deliveries:
            point.draw(screen)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

main()
