import pygame
import random


# Colors
RED = (255, 0, 0)

class Passenger:
    """
    Represents a passenger in the train simulation.
    Attributes:
        position (tuple): The (x, y) position of the passenger on the grid.
    Methods:
        __init__(trains):
            Initializes a new passenger with a random position not occupied by trains or wagons.
        get_random_position(trains, screen_size=600, grid_size=20):
            Generates a random position on the grid that is not occupied by trains or wagons.
        respawn(trains):
            Respawns the passenger at a new random position not occupied by trains or wagons.
    """



    def __init__(self, trains):
        self.position = self.get_random_position(trains)
    
    def get_random_position(self, trains, screen_size=600, grid_size=20):
        wagon_positions = [train.wagon for train in trains]
        trains_positions = [(train.get_position) for train in trains]
        while True:
            x = random.randint(0, screen_size // grid_size - 1) * grid_size
            y = random.randint(0, screen_size // grid_size - 1) * grid_size
            if (x, y) not in wagon_positions and (x, y) not in trains_positions:
                return (x, y)
    
    def respawn(self, trains):
        self.position = self.get_random_position(trains)