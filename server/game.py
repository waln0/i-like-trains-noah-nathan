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

ORIGINAL_SCREEN_WIDTH = 400
ORIGINAL_SCREEN_HEIGHT = 400
SCREEN_SIZE_INCREMENT = 50 # Increment per train

TRAINS_PASSENGER_RATIO = 2  # Number of train per passenger

TICK_RATE = 60

SPAWN_SAFE_ZONE = 3
SAFE_PADDING = 3

RESPAWN_COOLDOWN = 10.0

class Game:
    def __init__(self):
        self.screen_width = ORIGINAL_SCREEN_WIDTH
        self.screen_height = ORIGINAL_SCREEN_HEIGHT
        self.new_screen_width = self.screen_width
        self.new_screen_height = self.screen_height
        self.grid_size = 20
        self.running = True
        self.trains = {}
        self.passengers = []
        self.dead_trains = {}  # {agent_name: death_time}
        self.lock = threading.Lock()
        self.last_update = time.time()
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
        safe_distance = self.grid_size * SPAWN_SAFE_ZONE
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
            x = random.randint(SPAWN_SAFE_ZONE, (self.screen_width // self.grid_size) - SPAWN_SAFE_ZONE) * self.grid_size
            y = random.randint(SPAWN_SAFE_ZONE, (self.screen_height // self.grid_size) - SPAWN_SAFE_ZONE) * self.grid_size
            
            if self.is_position_safe(x, y):
                logger.debug(f"Found safe spawn position at ({x}, {y})")
                return x, y

        # Default position at the center
        center_x = (self.screen_width // 2) // self.grid_size * self.grid_size
        center_y = (self.screen_height // 2) // self.grid_size * self.grid_size
        logger.warning(f"Using default center position: ({center_x}, {center_y})")
        return center_x, center_y

    def update_passengers_count(self):
        """Update the number of passengers based on the number of trains"""
        desired_passengers = (len(self.trains) + 1) // TRAINS_PASSENGER_RATIO
        
        logger.debug(f"Updating passengers count. Current: {len(self.passengers)}, Desired: {desired_passengers}")
        
        # Add passengers if necessary
        while len(self.passengers) < desired_passengers:
            new_passenger = Passenger(self)
            self.passengers.append(new_passenger)
            logger.debug("Added new passenger")
            
        # Remove passengers if necessary
        while len(self.passengers) > desired_passengers:
            self.passengers.pop()
            logger.debug("Removed passenger")

    def update_screen_size(self):
        """Update screen size based on number of trains"""
        num_trains = len(self.trains)
        
        # Calculate the new size
        new_width = ORIGINAL_SCREEN_WIDTH + (num_trains * SCREEN_SIZE_INCREMENT)
        new_height = ORIGINAL_SCREEN_HEIGHT + (num_trains * SCREEN_SIZE_INCREMENT)
        
        # Update the dimensions
        if new_width != self.screen_width or new_height != self.screen_height:
            self.screen_width = new_width
            self.screen_height = new_height
            logger.debug(f"Screen size updated to: {self.screen_width}x{self.screen_height} for {num_trains} trains")

    def add_train(self, agent_name):
        """Add a new train to the game"""
        # Check the cooldown
        if agent_name in self.dead_trains:
            elapsed = time.time() - self.dead_trains[agent_name]
            if elapsed < RESPAWN_COOLDOWN:
                logger.debug(f"Train {agent_name} still in cooldown for {RESPAWN_COOLDOWN - elapsed:.1f}s")
                return False
            else:
                del self.dead_trains[agent_name]
        
        # Create the new train
        logger.debug(f"Adding train for agent: {agent_name}")
        spawn_pos = self.get_safe_spawn_position()
        if spawn_pos:
            self.trains[agent_name] = Train(spawn_pos[0], spawn_pos[1], agent_name)
            self.update_passengers_count()
            logger.info(f"Train {agent_name} spawned at position {spawn_pos}")
            return True
        return False

    def remove_train(self, agent_name):
        """Remove a train and update screen size"""
        logger.debug(f"Removing train for agent: {agent_name}")
        if agent_name in self.trains:
            # Register the death time
            self.dead_trains[agent_name] = time.time()
            logger.info(f"Train {agent_name} entered {RESPAWN_COOLDOWN}s cooldown")
            
            # Delete the train
            del self.trains[agent_name]
            
            logger.debug(f"New screen size set to: {self.screen_width}x{self.screen_height}")
            
            self.update_passengers_count()
            if not self.trains:
                logger.debug("No active trains, passengers list reset")
                self.passengers.clear()
        
        logger.debug(f"Remaining trains: {len(self.trains)}, passengers: {len(self.passengers)}")

    def get_train_cooldown(self, agent_name):
        """Get remaining cooldown time for a train"""
        if agent_name in self.dead_trains:
            elapsed = time.time() - self.dead_trains[agent_name]
            remaining = max(0, RESPAWN_COOLDOWN - elapsed)
            return remaining
        return 0

    def is_shrink_safe(self, screen_padding):
        """Check if the screen size can be reduced safely"""
        safe_zone = self.grid_size * SAFE_PADDING
        for train in self.trains.values():
            x, y = train.position
            if (x >= self.screen_width - screen_padding - safe_zone or 
                y >= self.screen_height - screen_padding - safe_zone):
                return False
            for wagon_x, wagon_y in train.wagons:
                if (wagon_x >= self.screen_width - screen_padding - safe_zone or 
                    wagon_y >= self.screen_height - screen_padding - safe_zone):
                    return False
        for passenger in self.passengers:
            x, y = passenger.position
            if (x >= self.screen_width - screen_padding - safe_zone or 
                y >= self.screen_height - screen_padding - safe_zone):
                return False
        return True

    def check_screen_size(self):
        """Check and update screen size if necessary"""

        # Update the screen size
        len_current_trains = len(self.trains)
        self.new_screen_width = ORIGINAL_SCREEN_WIDTH + (len_current_trains * SCREEN_SIZE_INCREMENT)
        self.new_screen_height = ORIGINAL_SCREEN_HEIGHT + (len_current_trains * SCREEN_SIZE_INCREMENT)

        if (self.new_screen_width < self.screen_width or 
            self.new_screen_height < self.screen_height):
            
            # Calculate the necessary padding
            screen_padding = self.screen_width - self.new_screen_width
            
            # Check if we can shrink safely
            if self.is_shrink_safe(screen_padding):
                self.screen_width = self.new_screen_width
                self.screen_height = self.new_screen_height
                logger.debug(f"Screen size safely reduced to: {self.screen_width}x{self.screen_height}")
            # If the zone can be reduced by grid_size, reduce the grid size
            elif self.is_shrink_safe(self.grid_size):
                self.screen_width = self.screen_width - self.grid_size
                self.screen_height = self.screen_height - self.grid_size
        elif self.new_screen_width > self.screen_width or self.new_screen_height > self.screen_height:
            self.screen_width = self.new_screen_width
            self.screen_height = self.new_screen_height
            logger.debug(f"Screen size increased to: {self.screen_width}x{self.screen_height}")

    def update(self):
        """Update game state"""
        if not self.trains:  # Update only if there are trains
            return
            
        with self.lock:
            # Update all trains and check for death conditions
            trains_to_remove = []
            for train_name, train in self.trains.items():
                train.update(self.passengers, self.trains, self.screen_width, self.screen_height, self.grid_size)
                
                # Check the death conditions
                # if (train.check_collisions(self.trains) or 
                if not train.alive:
                    trains_to_remove.append(train_name)
            
            # Remove the dead trains
            for train_name in trains_to_remove:
                self.remove_train(train_name)
            
            
            # Check and update the screen size if necessary
            self.check_screen_size()

    def change_direction_of_train(self, agent_name, new_direction):
        """
        Change the direction of a specific train
        """
        logger.debug(f"Changing direction of train {agent_name} to {new_direction}")
        if agent_name in self.trains:
            self.trains[agent_name].change_direction(new_direction)