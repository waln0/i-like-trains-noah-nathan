"""
Train class for the game "I Like Trains"
"""
import logging
from passenger import MAX_POINTS_VALUE
from math import *

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
# INITIAL_SPEED = 60  # Initial speed in pixels per second
INITIAL_SPEED = 30  # Initial speed in pixels per second
SPEED_DECREMENT_COEFFICIENT = 0.95  # Speed reduction coefficient for each wagon
ACTIVATE_SPEED_BOOST = True  # Activate speed boost
BOOST_DURATION = 0.25  # Duration of speed boost in seconds
BOOST_COOLDOWN_DURATION = 10.0  # Cooldown duration for speed boost

TICK_RATE = 60  # Ticks per second


class Train:

    def __init__(self, x, y, agent_name, color, handle_train_death):
        self.position = (x, y)
        self.wagons = []
        self.new_direction = (1, 0)
        self.direction = (1, 0)  # Starts right
        self.previous_direction = (1, 0)
        self.agent_name = agent_name
        self.alive = True
        self.score = 0
        self.color = color
        self.handle_death = handle_train_death
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
            "alive": True,
            "speed": True,
            "speed_boost": True,
            "boost_cooldown": True
        }
        # Use both server and client loggers
        self.server_logger = logging.getLogger("server.train")
        self.client_logger = logging.getLogger("client.train")
        self.server_logger.debug(
            f"Initializing train at position: {x}, {y} with color {self.color}"
        )
        # Speed boost properties
        self.speed_boost_active = False
        self.speed_boost_timer = 0
        self.boost_cooldown_active = False
        self.boost_cooldown_timer = 0
        self.normal_speed = INITIAL_SPEED  # Store normal speed for after boost ends

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

    def update(self, trains, screen_width, screen_height, grid_size):
        """Update the train position"""
        if not self.alive:
            return

        # Manage speed boost timer
        if self.speed_boost_active:
            self.speed_boost_timer -= 1/TICK_RATE  # Decrement by seconds (assuming TICK_RATE ticks per second)
            if self.speed_boost_timer <= 0:
                # Reset speed boost
                self.speed_boost_active = False
                self.speed = self.normal_speed
                self._dirty["speed"] = True
                
                # Start cooldown
                self.boost_cooldown_active = True
                self.boost_cooldown_timer = BOOST_COOLDOWN_DURATION
        
        # Manage boost cooldown timer
        if self.boost_cooldown_active:
            self.boost_cooldown_timer -= 1/TICK_RATE  # Decrement by seconds
            if self.boost_cooldown_timer <= 0:
                # Reset cooldown
                self.boost_cooldown_active = False

        # Increment movement timer
        self.move_timer += 1

        # Check if it's time to move
        if self.move_timer >= TICK_RATE / self.speed:  # TICK_RATE ticks per second
            self.move_timer = 0
            self.set_direction(self.new_direction)
            self.move(trains, screen_width, screen_height, grid_size)

    def add_wagon(self):
        """Add a wagon to the train"""
        self.wagons.append(self.last_position)
        self._dirty["wagons"] = True
        # Reduce speed with each wagon
        self.update_speed()

    def drop_passenger(self):
        """Drop the last wagon from the train and return its position"""
        if not self.alive:
            return None
        
        # Apply speed boost if enabled and not in cooldown
        if ACTIVATE_SPEED_BOOST and not self.boost_cooldown_active and not self.speed_boost_active and self.score >= 1:
            
            # Get the last wagon position
            last_wagon_pos = self.wagons[-1]

            # Reduce score based on wagon drop cost
            self.update_score(self.score - 1)
            # Store current normal speed before boost
            self.normal_speed = self.speed
            # Apply boost (e.g., double the current speed)
            self.speed *= 1.5
            self.speed_boost_active = True
            self.speed_boost_timer = BOOST_DURATION  # 1 second boost
            self._dirty["speed"] = True
            
            return last_wagon_pos
        else:
            return None

    def update_speed(self):
        self.speed = INITIAL_SPEED * SPEED_DECREMENT_COEFFICIENT ** len(self.wagons)
        self._dirty["speed"] = True 

    def update_wagons(self):
        desired_number_of_wagons = ceil((self.score)/MAX_POINTS_VALUE)
        current_number_of_wagons = len(self.wagons)

        # Drop wagons if we have too many
        while current_number_of_wagons > desired_number_of_wagons:
            self.wagons.pop()
            self._dirty["wagons"] = True
            current_number_of_wagons = len(self.wagons)


        while current_number_of_wagons < desired_number_of_wagons:
            self.add_wagon()
            self._dirty["wagons"] = True
            current_number_of_wagons = len(self.wagons)

    def move(self, trains, screen_width, screen_height, grid_size):
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
            self.handle_death(self.agent_name)
            self.reset()
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
            "speed": self.speed,
        }

    def to_dict(self):
        # self.server_logger.debug(f"Converting train {self.agent_name} to dictionary")
        """Convert train to dictionary, returning only modified data"""
        data = {}
        if self._dirty["position"]:
            data["position"] = self.position
            self._dirty["position"] = False
        if self._dirty["wagons"]:
            # Vérifier que tous les wagons ont des positions valides
            valid_wagons = []
            for wagon in self.wagons:
                if wagon is not None and len(wagon) == 2 and None not in wagon:
                    valid_wagons.append(wagon)
            data["wagons"] = valid_wagons
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
            # self.server_logger.debug(f"Setting alive to {self.alive}")
            data["alive"] = self.alive
            self._dirty["alive"] = False
        if self._dirty["speed"]:
            data["speed"] = self.speed
            self._dirty["speed"] = False
        
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

        # Update speed
        self.update_wagons()
        self.update_speed()

    def set_alive(self, alive):
        """Update train alive status"""
        if self.alive != alive:
            self.alive = alive
            self._dirty["alive"] = True

    def check_collisions(self, new_position, all_trains):
        for wagon_pos in self.wagons:
            if new_position == wagon_pos:
                collision_msg = f"Train {self.agent_name} collided with its own wagon at {wagon_pos}"
                self.server_logger.info(collision_msg)
                self.client_logger.info(collision_msg)
                self.set_alive(False)
                return True

        for train in all_trains.values():
            # If the train we are checking is dead or the train is ours, skip
            if train.agent_name == self.agent_name or not train.alive:
                continue

            if new_position == train.position:
                collision_msg = f"Train {self.agent_name} collided with stationary train {train.agent_name}"
                self.server_logger.info(collision_msg)
                self.client_logger.info(collision_msg)
                self.set_alive(False)  # Seul le train en mouvement meurt
                return True

            # Check collision with wagons
            for wagon_pos in train.wagons:
                if self.position == wagon_pos:
                    collision_msg = f"Train {self.agent_name} collided with wagon of train {train.agent_name}"
                    self.server_logger.info(collision_msg)
                    self.client_logger.info(collision_msg)
                    self.set_alive(False)
                    return True

        return False

    def check_out_of_bounds(self, new_position, screen_width, screen_height):
        """Check if the train is out of the screen"""
        x, y = new_position
        # self.server_logger.debug(f"Position: {x}, {y}=. Screen size: {screen_width}, {screen_height}. New position: {new_position}")
        if x < 0 or x >= screen_width or y < 0 or y >= screen_height:
            self.server_logger.info(
                f"Train {self.agent_name} is dead: out of the screen. Coordinates: {new_position}"
            )
            self.set_alive(False)
            return True
        return False

    def reset(self):
        # Set position to a valid coordinate outside the visible area
        # This avoids the 'position' error in broadcast_game_state
        self.position = (-1, -1)  # Use an off-screen position instead of None
        self.wagons = []
        # Reset direction to a valid value
        self.direction = (1, 0)
        self.new_direction = (1, 0)
        self.previous_direction = (1, 0)
        self._dirty = {
            "position": True,
            "wagons": True,
            "direction": True,
            "score": True,
            "color": True,
            "alive": True,
            "speed": True,
            "speed_boost": True,
            "boost_cooldown": True
        }