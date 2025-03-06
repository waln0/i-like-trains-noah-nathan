import random
import pygame
import logging
import time

# We use the customer logger
logger = logging.getLogger("client")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("game_debug.log"), logging.StreamHandler()],
)

# Colors
WHITE = (255, 255, 255)  # Color for the background
GREEN = (0, 255, 0)  # Color for writing respawn message
BLACK = (0, 0, 0)  # Color for the passengers
RED = (255, 0, 0)  # Color for writing death message
BLUE = (0, 0, 255)  # Color for player train
LIGHT_BLUE = (100, 180, 255)  # Color for player wagons


class Agent:
    def __init__(self, agent_name, send_action):
        self.logger = logging.getLogger("client.agent")  # Customer's subcloger
        self.all_trains = {}
        self.agent_name = agent_name
        self.all_passengers = []

        self.send_action = send_action

        self.grid_size = 0
        self.screen_width = 0
        self.screen_height = 0

        self.directions = [
            (0, -1),
            (1, 0),
            (0, 1),
            (-1, 0),
        ]  # Possible directions (Up, Right, Down, Left)
        self.current_direction_index = 1  # Start going to the right
        self.changing_direction = False

        self.death_time = time.time()  # Initializing death time at startup
        self.respawn_cooldown = 0  # No cooldown at the first spawn
        self.is_dead = True  # Start dead
        self.waiting_for_respawn = True

    def will_hit_wall(self, position, direction, grid_size, game_width, game_height):
        """Check if the next position will hit a wall"""

    def will_hit_train_or_wagon(self, position, direction):
        """Check if the direction leads to a collision with a train or wagon"""

    def get_closest_passenger(self, current_pos):
        """Find the closest passenger and return its position"""

    def get_direction_to_target(self, current_pos, target_pos, valid_directions):
        """Determine the best direction among the valid ones to reach the target the fastest"""

    def get_direction(self, game_width, game_height): # The client regularly calls this method to get the next direction the agent chose
        """Return a valid random direction that does not lead to a wall or a collision"""

    def is_opposite_direction(self, new_direction):
        """Check if the new direction is opposite to the current direction"""