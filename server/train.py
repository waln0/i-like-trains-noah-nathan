import pygame
import random


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

NB_TICKS_FOR_MOVING = 10

class Train:
    """
    A class to represent a train in the game.
    Attributes
    ----------
    position : tuple
        The current position of the train (x, y).
    wagons : list
        A list of positions representing the wagons of the train.
    direction : tuple
        The current direction of the train.
    alive : bool
        A flag indicating whether the train is alive.
    color : tuple
        The color of the train.
    agent : object
        The agent controlling the train.
    tick_count : int
        A counter for the number of ticks since the last move.
    Methods
    -------
    __init__(x, y, color, agent):
        Initializes the train with a position, color, and agent.
    get_position():
        Returns the current position of the train.
    change_direction(new_direction):
        Changes the direction of the train if the new direction is not directly opposite to the current direction.
    update(passengers):
        Updates the state of the train, including moving it if necessary.
    move(grid_size):
        Moves the train in the current direction by the grid size.
    draw(screen, grid_size):
        Draws the train and its wagons on the screen.
    """


    def __init__(self, x, y, color, agent):
        self.position = (x, y)
        self.wagons = []
        self.direction = RIGHT
        self.alive = True
        self.color = color
        self.agent = agent
        self.tick_count = 0

    def get_position(self):
        return self.position

    def change_direction(self, new_direction):
        if (new_direction[0] * -1, new_direction[1] * -1) != self.direction:
            self.direction = new_direction
    
    def update(self, passengers):
        if not self.alive:
            return
        
        
        
        if self.tick_count/len(self.wagons) == NB_TICKS_FOR_MOVING:
            self.tick_count = 0
            self.move()

    def add_wagon(self, position):
        self.wagons.append(position)

    def move(self, grid_size, passengers):
        last_wagon_position = self.wagons[-1] if self.wagons else self.position
        if self.wagons:
            # Move each wagon to the position of the previous
            for i in range(len(self.wagons) - 1, 0, -1):
                self.wagons[i] = self.wagons[i - 1]
            self.wagons[0] = self.position  # The first wagon takes the old position of the locomotive

        # Move the locomotive
        self.position = (self.position[0] + self.direction[0] * grid_size, 
                        self.position[1] + self.direction[1] * grid_size)
        # if train collides with passenger
        for passenger in passengers:
            if self.position == passenger.position:
                self.add_wagon(last_wagon_position)
                passenger.respawn()
                break
    
    def draw(self, screen, grid_size):
        pygame.draw.rect(screen, self.color, (*self.position, grid_size, grid_size))
        for wagon in self.wagons:
            pygame.draw.rect(screen, self.color, (*wagon, grid_size, grid_size))