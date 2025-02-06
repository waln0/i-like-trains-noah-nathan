import pygame
import random
import os
import importlib
import socket
import json
import threading

from train import Train
from passenger import Passenger


# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

class Game:
    """
    A class to represent the game.
    Attributes
    ----------
    screen_with_x : int
        The width of the game screen.
    screen_with_y : int
        The height of the game screen.
    grid_size : int
        The size of the grid cells.
    tick_rate : int
        The frame rate of the game.
    screen : pygame.Surface
        The display surface of the game.
    clock : pygame.time.Clock
        The clock object to control the frame rate.
    running : bool
        A flag to indicate if the game is running.
    trains : dict
        A dictionary to store the trains with agent names as keys.
    passengers : list
        A list to store the passengers.
    Methods
    -------
    __init__():
        Initializes the game.
    run():
        Runs the game loop.
    add_train(agent_name):
        Adds a train to the game.
    remove_train(agent_name):
        Removes a train from the game.
    handle_events():
        Handles the game events.
    update():
        Updates the game state.
    draw():
        Draws the game elements on the screen.
    """



    def __init__(self):
        pygame.init()
        self.screen_with_x = 800
        self.screen_with_y = 800
        self.grid_size = 20
        self.tick_rate = 10
        self.screen = pygame.display.set_mode((self.screen_with_x, self.screen_with_y))
        self.clock = pygame.time.Clock()
        self.running = True
        self.trains = {} # {agent_name: Train}
        self.passengers = []
        self.screen_padding = 100
    
    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(self.tick_rate)
        pygame.quit()

    def add_train(self, agent_name):
        self.trains[agent_name] = Train(random.randint(0, self.screen_with_x), random.randint(0, self.screen_with_y), RED, agent_name)
        self.update_screen_size()
        
    def remove_train(self, agent_name):
        self.trains.pop(agent_name)
        self.update_screen_size()
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    def can_reduce_padding(self):
        for train in self.trains.values():
            x, y = train["position"]
            if x >= self.screen_with_x - self.screen_padding - 50 or y >= self.screen_with_y - self.screen_padding - 50:
                return False
            for wagon in train["wagons"]:
                x, y = wagon
                if x >= self.screen_with_x - self.screen_padding - 50 or y >= self.screen_with_y - self.screen_padding - 50:
                    return False
        return True

    def reduce_padding(self):
        if self.can_reduce_padding():
            self.screen_with_x -= self.screen_padding
            self.screen_with_y -= self.screen_padding
    
    def update(self):
        for train in self.trains:
            train.update(self.passengers)
            

    def update_screen_size(self):
        self.screen_with_x += self.screen_padding
        self.screen_with_y += self.screen_padding
    
    def draw(self):
        self.screen.fill(WHITE)
        for train in self.trains:
            train.draw(self.screen)
        for passenger in self.passengers:
            passenger.draw(self.screen)
        pygame.display.flip()