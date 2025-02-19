import pygame
import random
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game_debug.log'),
        logging.StreamHandler()
    ]
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

INITIAL_SPEED = 300 # max 380
SPEED_DECREMENT_COEFFICIENT = 0.95

def generate_random_non_blue_color():
    """Generate a random RGB color avoiding blue nuances"""
    while True:
        r = random.randint(100, 255)  # Lighter for the trains
        g = random.randint(100, 255)
        b = random.randint(0, 100)    # Limit the blue
        
        # If it's not a blue nuance (more red or green than blue)
        if r > b + 50 or g > b + 50:
            return (r, g, b)

class Train:

    def __init__(self, x, y, agent_name):
        self.position = (x, y)
        self.wagons = []
        self.direction = (1, 0)  # Starts right
        self.alive = True
        self.previous_direction = (1, 0)  # Starts with the same direction
        self.agent_name = agent_name
        self.move_timer = 0
        self.speed = INITIAL_SPEED
        self.last_position = (x, y)
        self.color = generate_random_non_blue_color()  # Train color
        self.wagon_color = tuple(min(c + 50, 255) for c in self.color)  # Wagons lighter
        # Use both server and client loggers
        self.server_logger = logging.getLogger('server.train')
        self.client_logger = logging.getLogger('client.train')
        self.server_logger.debug(f"Initializing train at position: {x}, {y} with color {self.color}")

    def get_position(self):
        return self.position

    def get_opposite_direction(self, direction):
        """Return the opposite direction"""
        return (-direction[0], -direction[1])

    def is_opposite_direction(self, new_direction):
        """Check if the new direction is opposite to the previous direction"""
        opposite = (-self.previous_direction[0], -self.previous_direction[1])
        # self.server_logger.debug(f"Previous direction: {self.previous_direction}")
        # self.server_logger.debug(f"Opposite direction: {opposite}")
        return tuple(new_direction) == opposite

    def change_direction(self, new_direction):
        """Change the direction of the train if possible"""
        current_direction = self.direction
        # self.server_logger.debug(f"Attempting to change direction from {current_direction} to {new_direction}")
        
        # Convert new_direction to tuple for comparison
        new_direction = tuple(new_direction)
        
        # Check if it's an opposite direction
        if self.is_opposite_direction(new_direction):
            self.server_logger.debug("Cannot change direction: would be opposite direction")
            return False
            
        # If the direction is the same, no need to change
        if new_direction == current_direction:
            # self.server_logger.debug("Already moving in this direction")
            return True
            
        # Apply the direction change
        # self.server_logger.debug(f"Changing direction to: {new_direction}")
        self.direction = new_direction
        return True

    def update(self, passengers, trains, screen_width, screen_height, grid_size):
        """Update the train position"""
            
        self.move_timer += 1
        # if self.move_timer >= self.move_interval:
        if self.move_timer >= 1000/self.speed:
            self.move_timer = 0
            old_position = self.position
            self.move(passengers, trains, screen_width, screen_height, grid_size)
            if self.position != old_position:
                self.last_position = old_position
                # self.server_logger.debug(f"Train moved from {old_position} to {self.position}")

    def add_wagon(self, position):
        self.speed = self.speed * SPEED_DECREMENT_COEFFICIENT
        self.wagons.append(position)

    def move(self, passengers, trains, screen_width, screen_height, grid_size):
        """Regular interval movement"""
        # self.server_logger.debug(f"Moving train from {self.position} in direction {self.direction}")
        
        # Save the last position of the last wagon for a possible new wagon
        last_wagon_position = self.wagons[-1] if self.wagons else self.position
        
        # Update the previous direction before movement
        self.previous_direction = self.direction
        
        # Move the wagons
        if self.wagons:
            for i in range(len(self.wagons) - 1, 0, -1):
                self.wagons[i] = self.wagons[i - 1]
            self.wagons[0] = self.position
        
        # Move the locomotive
        new_position = (
            self.position[0] + self.direction[0] * grid_size,
            self.position[1] + self.direction[1] * grid_size
        )

        self.check_collisions(new_position, trains)
        self.check_out_of_bounds(new_position, screen_width, screen_height)
        
        self.last_position = self.position
        self.position = new_position
        
        # self.server_logger.debug(f"Train moved to {self.position}")
        
        # Check collision with passenger
        for passenger in passengers:
            if self.position == passenger.position:
                self.add_wagon(last_wagon_position)
                passenger.respawn()
                break

    def serialize(self):
        """
        Convert the train state to a serializable format for sending to the client
        """
        return {
            "position": self.position,
            "wagons": self.wagons,
            "direction": self.direction,
            "previous_direction": self.previous_direction,
            "name": self.agent_name,
            "color": self.color,
            "wagon_color": self.wagon_color
        }

    def check_collisions(self, new_position, all_trains):
        for wagon_pos in self.wagons:
            if new_position == wagon_pos:
                collision_msg = f"Train {self.agent_name} collided with its own wagon at {wagon_pos}"
                self.server_logger.info(collision_msg)
                self.client_logger.info(collision_msg)
                self.alive = False
                return True

        for train in all_trains.values():
            if train.agent_name == self.agent_name:
                continue
            
            if new_position == train.position:                
                collision_msg = f"Train {self.agent_name} collided with stationary train {train.agent_name}"
                self.server_logger.info(collision_msg)
                self.client_logger.info(collision_msg)
                self.alive = False  # Seul le train en mouvement meurt
                return True
            
            # Check collision with wagons
            for wagon_pos in train.wagons:
                if self.position == wagon_pos:
                    collision_msg = f"Train {self.agent_name} collided with wagon of train {train.agent_name}"
                    self.server_logger.info(collision_msg)
                    self.client_logger.info(collision_msg)
                    self.alive = False
                    return True
        
        return False

    def check_out_of_bounds(self, new_position, screen_width, screen_height):
        """Check if the train is out of the screen"""
        x, y = new_position
        if (x < 0 or x >= screen_width or y < 0 or y >= screen_height):
            self.server_logger.warning(f"Train {self.agent_name} is dead: out of the screen. Coordinates: {new_position}")
            self.alive = False
            return True
        return False