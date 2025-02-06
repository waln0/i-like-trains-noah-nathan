import pygame
import random

class Passenger:
    def __init__(self, wagons):
        self.position = self.get_random_position(wagons)
    
    def get_random_position(self, wagons):
        while True:
            x = random.randint(0, SCREEN_SIZE // GRID_SIZE - 1) * GRID_SIZE
            y = random.randint(0, SCREEN_SIZE // GRID_SIZE - 1) * GRID_SIZE
            if (x, y) not in wagons:
                return (x, y)
    
    def respawn(self, wagons):
        self.position = self.get_random_position(wagons)
    
    def draw(self, screen):
        pygame.draw.rect(screen, RED, (*self.position, GRID_SIZE, GRID_SIZE))