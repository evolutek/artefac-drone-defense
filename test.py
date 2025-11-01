import pygame
import random
import math

# Initialisation de Pygame
pygame.init()

# Dimensions de la fenêtre
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simulation de Drones et Livraisons")

# Couleurs
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)

# Classe pour représenter un drone
class Drone:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 10
        self.color = BLUE
        self.speed = 2
        self.target = None

    def move(self):
        if self.target:
            dx = self.target[0] - self.x
            dy = self.target[1] - self.y
            distance = math.sqrt(dx**2 + dy**2)
            if distance > 0:
                self.x += (dx / distance) * self.speed
                self.y += (dy / distance) * self.speed
            if distance < 5:
                self.target = None

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)

# Classe pour représenter un point de livraison
class DeliveryPoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = 8
        self.color = RED

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, (self.x - self.size, self.y - self.size, self.size * 2, self.size * 2))

# Création des drones et des points de livraison
drones = [Drone(random.randint(50, WIDTH - 50), random.randint(50, HEIGHT - 50)) for _ in range(3)]
delivery_points = [DeliveryPoint(random.randint(50, WIDTH - 50), random.randint(50, HEIGHT - 50)) for _ in range(5)]

# Boucle principale
running = True
clock = pygame.time.Clock()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Déplacement des drones
    for drone in drones:
        if not drone.target or random.random() < 0.01:  # Changement aléatoire de cible
            drone.target = random.choice(delivery_points)
            drone.target = (drone.target.x, drone.target.y)
        drone.move()

    # Dessin
    screen.fill(WHITE)

    # Dessin des routes (grille)
    for x in range(0, WIDTH, 50):
        pygame.draw.line(screen, GRAY, (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, 50):
        pygame.draw.line(screen, GRAY, (0, y), (WIDTH, y))

    # Dessin des drones et des points de livraison
    for drone in drones:
        drone.draw(screen)
    for point in delivery_points:
        point.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()

