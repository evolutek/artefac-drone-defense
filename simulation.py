import pygame
import utils

# Initialisation de Pygame
pygame.init()


# Dimensions de la fenêtre
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simulation")

# Couleurs
# Useless, already in pygame : WHITE = pygame.white
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)



def attribution(drones, deliveries):
    drones[0].add_target(deliveries[0])
    

def main():
    deliveries = [utils.Delivery("Poche de sang", 0.5, (600,500), 1)]
    drones = [utils.Drone(1, 1, 1, 1, (50,50))]
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
