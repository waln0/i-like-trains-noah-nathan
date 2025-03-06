"""
Train class for the game "I Like Trains"
"""
import pygame
import random
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("game_debug.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)

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

# Train settings
INITIAL_SPEED =10  # Initial speed in pixels per second
SPEED_DECREMENT_COEFFICIENT = 0.95  # Speed reduction coefficient for each wagon
TICK_RATE = 60  # Ticks per second


class Train:

    def __init__(self, x, y, agent_name, color):
        self.position = (x, y)
        self.wagons = []
        self.new_direction = (1, 0)
        self.direction = (1, 0)  # Starts right
        self.previous_direction = (1, 0)
        self.agent_name = agent_name
        self.alive = True
        self.score = 0
        self.color = color
        self.move_timer = 0
        self.speed = INITIAL_SPEED
        self.last_position = (x, y)
        # Dirty flags to track modifications
        self._dirty = {
            "position": True,
            "wagons": True,
            "direction": True,
            "score": True,
            "color": True,
            "alive": True
        }
        # Use both server and client loggers
        self.server_logger = logging.getLogger("server.train")
        self.client_logger = logging.getLogger("client.train")
        self.server_logger.debug(
            f"Initializing train at position: {x}, {y} with color {self.color}"
        )

    def get_position(self):
        """Return the train's position"""
        return self.position

    def is_opposite_direction(self, new_direction):
        """Check if the new direction is opposite to the previous direction"""
        # self.server_logger.debug(f"Checking if {new_direction} is opposite to {self.direction}: {new_direction == self.get_opposite_direction(self.direction)}")
        return new_direction[0] == -self.direction[0] and new_direction[1] == -self.direction[1]

    def change_direction(self, new_direction):
        """Change the train's direction if possible"""
        if not self.is_opposite_direction(new_direction):
            # self.server_logger.debug(f"Changing direction because {new_direction} is not opposite to {self.direction}")
            self.new_direction = new_direction

    def update(self, passengers, trains, screen_width, screen_height, grid_size):
        """Update the train position"""
        if not self.alive:
            return

        # Increment movement timer
        self.move_timer += 1

        # Check if it's time to move
        if self.move_timer >= TICK_RATE / self.speed:  # TICK_RATE ticks per second
            self.move_timer = 0
            self.set_direction(self.new_direction)
            self.move(passengers, trains, screen_width, screen_height, grid_size)

    def add_wagon(self):
        """Add a wagon to the train"""
        self.wagons.append(self.last_position)
        self._dirty["wagons"] = True
        # Reduce speed with each wagon
        self.speed *= SPEED_DECREMENT_COEFFICIENT

    def move(self, passengers, trains, screen_width, screen_height, grid_size):
        """Regular interval movement"""
        if not self.alive:
            return

        # Save current position
        self.last_position = self.position

        # Calculate new position
        new_x = self.position[0] + self.direction[0] * grid_size
        new_y = self.position[1] + self.direction[1] * grid_size
        new_position = (new_x, new_y)

        # Check collisions and bounds
        if (
            self.check_collisions(new_position, trains)
            or self.check_out_of_bounds(new_position, screen_width, screen_height)
        ):
            self.set_alive(False)
            return

        # Update wagons
        if self.wagons:
            self.wagons.insert(0, self.position)
            self.wagons.pop()
            self._dirty["wagons"] = True

        # Update position
        # self.server_logger.debug(f"Moving train to {new_position} in direction {self.direction}")
        self.set_position(new_position)

    def serialize(self):
        """
        Convert train state to a serializable format for sending to the client
        """
        return {
            "position": self.position,
            "wagons": self.wagons,
            "direction": self.direction,
            "score": self.score,
            "color": self.color,
            "alive": self.alive,
        }

    def to_dict(self):
        """Convert train to dictionary, returning only modified data"""
        data = {}
        if self._dirty["position"]:
            data["position"] = self.position
            self._dirty["position"] = False
        if self._dirty["wagons"]:
            data["wagons"] = self.wagons
            self._dirty["wagons"] = False
        if self._dirty["direction"]:
            data["direction"] = self.direction
            self._dirty["direction"] = False
        if self._dirty["score"]:
            data["score"] = self.score
            self._dirty["score"] = False
        if self._dirty["color"]:
            data["color"] = self.color
            self._dirty["color"] = False
        if self._dirty["alive"]:
            data["alive"] = self.alive
            self._dirty["alive"] = False
        return data

    def set_position(self, new_position):
        """Update train position"""
        if self.position != new_position:
            self.position = new_position
            self._dirty["position"] = True

    def set_direction(self, direction):
        """Change train direction"""
        if self.direction != direction:
            self.previous_direction = self.direction
            self.direction = direction
            self._dirty["direction"] = True

    def update_score(self, new_score):
        """Update train score"""
        if self.score != new_score:
            self.score = new_score
            self._dirty["score"] = True

    def set_alive(self, alive):
        """Update train alive status"""
        if self.alive != alive:
            self.alive = alive
            self._dirty["alive"] = True

    def check_collisions(self, new_position, all_trains):
        """Check collisions with other trains and their wagons"""
        for train in all_trains.values():
            # Skip self
            if train.agent_name == self.agent_name:
                continue

            # Check collision with train head
            if new_position == train.position:
                return True

            # Check collision with wagons
            if new_position in train.wagons:
                return True

        return False

    def check_out_of_bounds(self, new_position, screen_width, screen_height):
        """Check if the train is out of the screen"""
        x, y = new_position
        return x < 0 or x >= screen_width or y < 0 or y >= screen_height
