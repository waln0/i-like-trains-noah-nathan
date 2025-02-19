import pygame
import random
import os
import importlib
import socket
import json
import threading
import time

from train import Train
from passenger import Passenger
import logging

# Use the logger configured in server.py
logger = logging.getLogger('server.game')

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
DARK_GREEN = (0, 100, 0)

ORIGINAL_SCREEN_WIDTH = 200
ORIGINAL_SCREEN_HEIGHT = 200

PASSENGERS_RATIO = 0.5  # Number of passengers per train (can be decimal)

TICK_RATE = 60

class Game:
    def __init__(self):
        self.screen_width = ORIGINAL_SCREEN_WIDTH
        self.screen_height = ORIGINAL_SCREEN_HEIGHT
        self.grid_size = 20
        self.running = True
        self.trains = {}
        self.passengers = []
        self.screen_padding = 100
        self.lock = threading.Lock()
        self.spawn_safe_zone = 3  # Safe zone in number of cases
        self.last_update = time.time()
        self.dead_trains = {}  # {agent_name: death_time}
        self.respawn_cooldown = 10.0  # 10 secondes de cooldown
        # self.update_interval = 0.0 / self.tick_rate  # Intervalle fixe entre les updates
        logger.info(f"Game initialized with tick rate: {TICK_RATE}")
    
    def run(self):
        logger.info("Game loop started")
        while self.running:
            self.update()
            import time
            time.sleep(1/TICK_RATE)

    def is_position_safe(self, x, y):
        """
        Check if a position is safe for the spawn
        """
        # Check the borders
        safe_distance = self.grid_size * self.spawn_safe_zone
        if (x < safe_distance or 
            y < safe_distance or 
            x > self.screen_width - safe_distance or 
            y > self.screen_height - safe_distance):
            return False

        # Check the other trains and wagons
        for train in self.trains.values():
            # Distance to the train
            train_x, train_y = train.position
            if (abs(train_x - x) < safe_distance and 
                abs(train_y - y) < safe_distance):
                return False
            
            # Distance to the wagons
            for wagon_x, wagon_y in train.wagons:
                if (abs(wagon_x - x) < safe_distance and 
                    abs(wagon_y - y) < safe_distance):
                    return False

        return True

    def get_random_grid_position(self):
        """
        Return a random grid position
        """
        x = random.randint(0, (self.screen_width // self.grid_size) - 1) * self.grid_size
        y = random.randint(0, (self.screen_height // self.grid_size) - 1) * self.grid_size
        return x, y

    def get_safe_spawn_position(self, max_attempts=100):
        """
        Find a safe spawn position
        """
        for _ in range(max_attempts):
            # Position aligned on the grid
            x = random.randint(self.spawn_safe_zone, (self.screen_width // self.grid_size) - self.spawn_safe_zone) * self.grid_size
            y = random.randint(self.spawn_safe_zone, (self.screen_height // self.grid_size) - self.spawn_safe_zone) * self.grid_size
            
            if self.is_position_safe(x, y):
                logger.debug(f"Found safe spawn position at ({x}, {y})")
                return x, y

        # Default position at the center
        center_x = (self.screen_width // 2) // self.grid_size * self.grid_size
        center_y = (self.screen_height // 2) // self.grid_size * self.grid_size
        logger.warning(f"Using default center position: ({center_x}, {center_y})")
        return center_x, center_y

    def update_passengers_count(self):
        """Update the number of passengers based on the ratio"""
        desired_passengers = max(1, int(len(self.trains) * PASSENGERS_RATIO))
        current_passengers = len(self.passengers)
        
        logger.debug(f"Updating passengers count. Current: {current_passengers}, Desired: {desired_passengers}")
        
        # Add passengers if necessary
        while len(self.passengers) < desired_passengers:
            new_passenger = Passenger(self)
            self.passengers.append(new_passenger)
            logger.debug("Added new passenger")
            
        # Remove passengers if necessary
        while len(self.passengers) > desired_passengers:
            self.passengers.pop()
            logger.debug("Removed passenger")

    def add_train(self, agent_name):
        """Add a new train to the game"""
        # Vérifier si le train est en cooldown
        if agent_name in self.dead_trains:
            elapsed = time.time() - self.dead_trains[agent_name]
            if elapsed < self.respawn_cooldown:
                logger.debug(f"Train {agent_name} still in cooldown for {self.respawn_cooldown - elapsed:.1f}s")
                return False
            else:
                # Cooldown terminé, on peut retirer le train de la liste des morts
                del self.dead_trains[agent_name]
        
        # Créer le nouveau train
        logger.debug(f"Adding train for agent: {agent_name}")
        spawn_pos = self.get_safe_spawn_position()
        if spawn_pos:
            self.trains[agent_name] = Train(spawn_pos[0], spawn_pos[1], agent_name)
            self.update_passengers_count()
            self.update_screen_size()
            logger.info(f"Train {agent_name} spawned at position {spawn_pos}")
            return True
        return False

    def remove_train(self, agent_name):
        """Remove a train and start its cooldown"""
        logger.debug(f"Removing train for agent: {agent_name}")
        if agent_name in self.trains:
            # Enregistrer le temps de mort
            self.dead_trains[agent_name] = time.time()
            logger.info(f"Train {agent_name} entered {self.respawn_cooldown}s cooldown")
            
            # Supprimer le train
            del self.trains[agent_name]
            self.update_passengers_count()
            
            if not self.trains:
                logger.debug("No active trains, passengers list reset")
                self.passengers.clear()
            
            self.update_screen_size()
        
        logger.debug(f"Remaining trains: {len(self.trains)}, passengers: {len(self.passengers)}")

    def get_train_cooldown(self, agent_name):
        """Get remaining cooldown time for a train"""
        if agent_name in self.dead_trains:
            elapsed = time.time() - self.dead_trains[agent_name]
            remaining = max(0, self.respawn_cooldown - elapsed)
            return remaining
        return 0

    def can_reduce_padding(self):
        """Check if the screen size can be reduced"""
        logger.debug("Checking if padding can be reduced")
        for train in self.trains.values():
            x, y = train.position  # Direct access to the position attribute of the Train object

            if x >= self.screen_width - self.screen_padding - 50 or y >= self.screen_height - self.screen_padding - 50:
                return False
            for wagon_pos in train.wagons:  # Direct access to the wagons attribute
                x, y = wagon_pos
                if x >= self.screen_width - self.screen_padding - 50 or y >= self.screen_height - self.screen_padding - 50:
                    return False
        return True

    def reduce_padding(self):
        logger.debug("Reducing padding")
        if self.can_reduce_padding():
            self.screen_width -= self.screen_padding
            self.screen_height -= self.screen_padding

    def update(self):
        """Update game state"""
        if not self.trains:  # Update only if there are trains
            return
            
        with self.lock:
            # Update all trains and check for death conditions
            trains_to_remove = []
            for train_name, train in self.trains.items():
                train.update(self.passengers, self.grid_size)
                
                # Check the death conditions
                if (train.check_collisions(self.trains) or 
                    train.check_out_of_bounds(self.screen_width, self.screen_height) or
                    not train.alive):  # Add the check of the alive state
                    logger.info(f"Train {train_name} died!")
                    trains_to_remove.append(train_name)
            
            # Remove the dead trains
            for train_name in trains_to_remove:
                self.remove_train(train_name)

    def update_screen_size(self):
        logger.debug("Updating screen size")
        self.screen_width += self.screen_padding
        self.screen_height += self.screen_padding

    def change_direction_of_train(self, agent_name, new_direction):
        """
        Change the direction of a specific train
        """
        logger.debug(f"Changing direction of train {agent_name} to {new_direction}")
        if agent_name in self.trains:
            self.trains[agent_name].change_direction(new_direction)