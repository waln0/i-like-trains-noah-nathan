"""
Game class for the game "I Like Trains"
"""
from pickle import FALSE
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
logger = logging.getLogger("server.game")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
DARK_GREEN = (0, 100, 0)

ORIGINAL_GAME_WIDTH = 200
ORIGINAL_GAME_HEIGHT = 200

TRAINS_PASSENGER_RATIO = 1  # Number of trains per passenger

GAME_SIZE_INCREMENT_RATIO = 0.05  # Increment per train, the bigger the number, the bigger the screen grows

GRID_SIZE = int(ORIGINAL_GAME_WIDTH/20)

GAME_SIZE_INCREMENT = int(((ORIGINAL_GAME_WIDTH+ORIGINAL_GAME_HEIGHT)/2)*GAME_SIZE_INCREMENT_RATIO)  # Increment per train

TICK_RATE = 60

SPAWN_SAFE_ZONE = 3
SAFE_PADDING = 3

RESPAWN_COOLDOWN = 10.0

def generate_random_non_blue_color():
    """Generate a random RGB color avoiding blue nuances"""
    while True:
        r = random.randint(100, 230)  # Lighter for the trains
        g = random.randint(100, 230)
        b = random.randint(0, 150)  # Limit the blue

        # If it's not a blue nuance (more red or green than blue)
        if r > b + 50 or g > b + 50:
            return (r, g, b)

class Game:
    def __init__(self):
        self.game_width = ORIGINAL_GAME_WIDTH
        self.game_height = ORIGINAL_GAME_HEIGHT
        self.new_game_width = self.game_width
        self.new_game_height = self.game_height
        self.grid_size = GRID_SIZE
        self.running = True
        self.trains = {}
        self.train_colors = {}  # {agent_name: (train_color, wagon_color)}
        self.passengers = []
        self.dead_trains = {}  # {agent_name: death_time}
        self.lock = threading.Lock()
        self.last_update = time.time()
        self.game_started = False  # Track if game has started
        # Dirty flags for the game
        self._dirty = {
            "size": True,
            "grid_size": True,
            "passengers": True
        }
        logger.info(f"Game initialized with tick rate: {TICK_RATE}")

    def get_state(self):
        """Return game state with only modified data"""
        state = {}
        
        # Add game dimensions if modified
        if self._dirty["size"]:
            # logger.debug(f"Game state: size added")
            state["game_width"] = self.game_width
            state["game_height"] = self.game_height
            self._dirty["size"] = False
        # else:
            # logger.debug(f"Game state: size not added")
            
        # Add grid size if modified
        if self._dirty["grid_size"]:
            # logger.debug(f"Game state: grid size added")
            state["grid_size"] = self.grid_size
            self._dirty["grid_size"] = False
        # else:
            # logger.debug(f"Game state: grid size not added")
            
        # Add passengers if modified
        if self._dirty["passengers"]:
            state["passengers"] = [p.position for p in self.passengers]
            self._dirty["passengers"] = FALSE
            
        # Add modified trains
        trains_data = {}
        for name, train in self.trains.items():
            train_data = train.to_dict()
            if train_data:  # Only add if data has changed
                trains_data[name] = train_data
        if trains_data:
            state["trains"] = trains_data
            
        return state

    def run(self):
        logger.info("Game loop started")
        while self.running:
            self.update()
            import time
            time.sleep(1 / TICK_RATE)

    def is_position_safe(self, x, y):
        """Check if a position is safe for spawning"""
        # Check the borders
        safe_distance = self.grid_size * SPAWN_SAFE_ZONE
        if (
            x < safe_distance
            or y < safe_distance
            or x > self.game_width - safe_distance
            or y > self.game_height - safe_distance
        ):
            return False

        # Check other trains and wagons
        for train in self.trains.values():
            # Distance to the train
            train_x, train_y = train.position
            if abs(train_x - x) < safe_distance and abs(train_y - y) < safe_distance:
                return False

            # Distance to wagons
            for wagon_x, wagon_y in train.wagons:
                if (
                    abs(wagon_x - x) < safe_distance
                    and abs(wagon_y - y) < safe_distance
                ):
                    return False

        return True

    def get_safe_spawn_position(self, max_attempts=100):
        """Find a safe position for spawning"""
        for _ in range(max_attempts):
            # Position aligned on the grid
            x = (
                random.randint(
                    SPAWN_SAFE_ZONE,
                    (self.game_width // self.grid_size) - SPAWN_SAFE_ZONE,
                )
                * self.grid_size
            )
            y = (
                random.randint(
                    SPAWN_SAFE_ZONE,
                    (self.game_height // self.grid_size) - SPAWN_SAFE_ZONE,
                )
                * self.grid_size
            )

            if self.is_position_safe(x, y):
                logger.debug(f"Found safe spawn position at ({x}, {y})")
                return x, y

        # Default position at the center
        center_x = (self.game_width // 2) // self.grid_size * self.grid_size
        center_y = (self.game_height // 2) // self.grid_size * self.grid_size
        logger.warning(f"Using default center position: ({center_x}, {center_y})")
        return center_x, center_y

    def update_passengers_count(self):
        """Update the number of passengers based on the number of trains"""
        desired_passengers = (len(self.trains)) // TRAINS_PASSENGER_RATIO

        logger.debug(
            f"Updating passengers count. Current: {len(self.passengers)}, Desired: {desired_passengers}"
        )

        # Add or remove passengers if necessary
        changed = False
        while len(self.passengers) < desired_passengers:
            new_passenger = Passenger(self)
            self.passengers.append(new_passenger)
            changed = True
            logger.debug("Added new passenger")

        while len(self.passengers) > desired_passengers:
            self.passengers.pop()
            changed = True
            logger.debug("Removed passenger")
            
        if changed:
            self._dirty["passengers"] = True

    def start_game(self, num_clients):
        """Initialize game size based on number of connected clients"""
        if not self.game_started:
            # Calculate initial game size based on number of clients
            self.game_width = ORIGINAL_GAME_WIDTH + (num_clients * GAME_SIZE_INCREMENT)
            self.game_height = ORIGINAL_GAME_HEIGHT + (num_clients * GAME_SIZE_INCREMENT)
            self.new_game_width = self.game_width
            self.new_game_height = self.game_height
            self._dirty["size"] = True
            self._dirty["grid_size"] = True
            self.game_started = True
            logger.info(f"Game started with size {self.game_width}x{self.game_height} for {num_clients} clients")

    def add_train(self, agent_name):
        """Add a new train to the game"""
        # Check the cooldown
        if agent_name in self.dead_trains:
            elapsed = time.time() - self.dead_trains[agent_name]
            if elapsed < RESPAWN_COOLDOWN:
                logger.debug(
                    f"Train {agent_name} still in cooldown for {RESPAWN_COOLDOWN - elapsed:.1f}s"
                )
                return False
            else:
                del self.dead_trains[agent_name]

        # Create the new train
        logger.debug(f"Adding train for agent: {agent_name}")
        spawn_pos = self.get_safe_spawn_position()
        if spawn_pos:
            # If the agent name is in the train_colors dictionary, use the color, otherwise generate a random color
            if agent_name in self.train_colors:
                train_color = self.train_colors[agent_name]
            else:
                train_color = generate_random_non_blue_color()

            self.trains[agent_name] = Train(spawn_pos[0], spawn_pos[1], agent_name, train_color)
            logger.info(f"Train {agent_name} was added to the game")
            self.update_passengers_count()
            logger.info(f"Train {agent_name} spawned at position {spawn_pos}")
            return True
        return False

    def remove_train(self, agent_name):
        """Remove a train and update game size"""
        if agent_name in self.trains:
            # Register the death time
            self.dead_trains[agent_name] = time.time()
            logger.info(f"Train {agent_name} entered {RESPAWN_COOLDOWN}s cooldown")

            # Notify the client of the cooldown
            if hasattr(self, 'server') and self.server:
                self.server.send_cooldown_notification(agent_name, RESPAWN_COOLDOWN)

            # Delete the train
            del self.trains[agent_name]
            
            # Update game state
            self.update_passengers_count()
            if not self.trains:
                logger.debug("No active trains, passengers list reset")
                self.passengers.clear()
                self._dirty["passengers"] = True

    def get_train_cooldown(self, agent_name):
        """Get remaining cooldown time for a train"""
        if agent_name in self.dead_trains:
            elapsed = time.time() - self.dead_trains[agent_name]
            remaining = max(0, RESPAWN_COOLDOWN - elapsed)
            return remaining
        return 0

    def update(self):
        """Update game state"""
        if not self.trains:  # Update only if there are trains
            return
        
        with self.lock:
            # Update all trains and check for death conditions
            trains_to_remove = []
            for train_name, train in self.trains.items():
                # logger.debug(f"Updating train {train_name} at position {train.position} with direction {train.direction}")
                train.update(
                    self.passengers,
                    self.trains,
                    self.game_width,
                    self.game_height,
                    self.grid_size,
                )

                # Check for passenger collisions
                for passenger in self.passengers:
                    if train.position == passenger.position:
                        # Increase train score
                        train.update_score(train.score + 1)
                        train.add_wagon()
                        # Respawn passenger at a new safe location
                        passenger.respawn()
                        # logger.debug(f"Train {train_name} collected passenger, score: {train.score}")

                # Check the death conditions
                if not train.alive:
                    trains_to_remove.append(train_name)

            # Remove the dead trains
            for train_name in trains_to_remove:
                self.remove_train(train_name)