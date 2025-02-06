import pygame
import random

# Constants
SCREEN_SIZE = 600
GRID_SIZE = 20
TICK_RATE = 10

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

# Directions
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

class Train:
    def __init__(self, x, y, color, agent):
        self.position = (x, y)
        self.wagons = []
        self.direction = RIGHT
        self.alive = True
        self.color = color
        self.agent = agent

    def change_direction(self, new_direction):
        if (new_direction[0] != -self.direction[0] or new_direction[1] != -self.direction[1]):
            self.direction = new_direction
    
    def update(self, passengers):
        if not self.alive:
            return
        
        new_direction = self.agent.get_action(self.position, self.wagons, passengers)
        if new_direction:
            self.change_direction(new_direction)
        
        new_head = (self.position[0] + self.direction[0] * GRID_SIZE,
                    self.position[1] + self.direction[1] * GRID_SIZE)
        
        if new_head[0] < 0 or new_head[0] >= SCREEN_SIZE or new_head[1] < 0 or new_head[1] >= SCREEN_SIZE:
            self.alive = False
            return
        
        if new_head in self.wagons:
            self.alive = False
            return
        
        self.wagons.insert(0, self.position)
        self.position = new_head
        
        for passenger in passengers:
            if passenger.position == self.position:
                passenger.respawn(self.wagons)
            else:
                self.wagons.pop()
    
    def draw(self, screen):
        pygame.draw.rect(screen, self.color, (*self.position, GRID_SIZE, GRID_SIZE))
        for wagon in self.wagons:
            pygame.draw.rect(screen, self.color, (*wagon, GRID_SIZE, GRID_SIZE))