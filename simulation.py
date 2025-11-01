import pygame

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
