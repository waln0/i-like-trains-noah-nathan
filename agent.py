import random
import pygame
import logging
import time

# We use the customer logger
logger = logging.getLogger("client")

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
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

# DECISION_INTERVAL = 0  # Number of ticks between each decision


class Agent:
    """
    A class to represent an agent controlling a train in a grid environment.
    Attributes:
    -----------
    logger : logging.Logger
        Logger for the agent.
    all_trains : dict
        Dictionary to store all trains.
    agent_name : str
        Name of the agent.
    all_passengers : list
        List to store all passengers.
    send_action : function
        Function to send actions.
    grid_size : int
        Size of the grid.
    screen_width : int
        Width of the screen.
    screen_height : int
        Height of the screen.
    directions : list
        List of possible directions (Up, Right, Down, Left).
    current_direction_index : int
        Index of the current direction.
    changing_direction : bool
        Flag to indicate if the direction is changing.
    death_time : float
        Time of death.
    respawn_cooldown : int
        Cooldown time for respawn.
    is_dead : bool
        Flag to indicate if the agent is dead.
    waiting_for_respawn : bool
        Flag to indicate if the agent is waiting for respawn.
    """

    def __init__(self, agent_name, send_action, manual_respawn):
        self.logger = logging.getLogger("client.agent")  # Customer's subcloger
        self.all_trains = {}
        self.agent_name = agent_name
        self.all_passengers = []
        self.manual_respawn = manual_respawn

        self.send_action = send_action

        self.grid_size = 0
        self.screen_width = 400
        self.screen_height = 400

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
        self.waiting_for_respawn = False

    def will_hit_wall(self):
        """Check if the next position will hit a wall"""
        return

    def will_hit_train_or_wagon(self):
        """Check if the direction leads to a collision with a train or wagon"""
        return

    def get_closest_passenger(self):
        """Find the closest passenger and return its position"""
        return

    def get_direction_to_target(self):
        """Determine the best direction among the valid ones to reach the target the fastest"""
        return

    def get_valid_direction(self,):
        """Return a valid random direction that does not lead to a wall or a collision"""
        return

    def is_opposite_direction(self):
        """Check if the new direction is opposite to the current direction"""
        return

    def draw_gui(self):
        """Draw the agent's GUI on the screen"""
        return