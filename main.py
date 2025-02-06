import pygame
import os
import importlib

from train import Train
from passenger import Passenger


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



class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_SIZE, SCREEN_SIZE))
        self.clock = pygame.time.Clock()
        self.running = True
        self.trains = []
        self.passengers = [Passenger([])]
        self.load_agents()
    
    def load_agents(self):
        agents_folder = "agents"
        if not os.path.exists(agents_folder):
            os.makedirs(agents_folder)
        for filename in os.listdir(agents_folder):
            if filename.endswith(".py"):
                module_name = filename[:-3]
                module = importlib.import_module(f"agents.{module_name}")
                agent_instance = module.Agent()
                self.trains.append(Train(100, 100, BLUE, agent_instance))
    
    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(TICK_RATE)
        pygame.quit()
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
    
    def update(self):
        for train in self.trains:
            train.update(self.passengers)
    
    def draw(self):
        self.screen.fill(WHITE)
        for train in self.trains:
            train.draw(self.screen)
        for passenger in self.passengers:
            passenger.draw(self.screen)
        pygame.display.flip()

if __name__ == "__main__":
    Game().run()
