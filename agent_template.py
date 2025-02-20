import random
import pygame
import logging
import time

# We use the customer logger
logger = logging.getLogger('client')

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game_debug.log'),
        logging.StreamHandler()
    ]
)

# Colors
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
LIGHT_BLUE = (100, 180, 255)  # New color for player wagons

RESPAWN_COOLDOWN = 10.0  # RESPAWN COOLDOWN in seconds, checked by the server :p
MANUAL_RESPAWN = True  # Set to False to respawn automatically

# DECISION_INTERVAL = 0  # Number of ticks between each decision

class Agent:
    def __init__(self, agent_name, send_action):
        self.logger = logging.getLogger('client.agent')  # Customer's subcloger
        self.all_trains = {}
        self.agent_name = agent_name
        self.all_passengers = []

        self.send_action = send_action

        self.grid_size = 0
        self.screen_width = None
        self.screen_height = None

        self.directions = [(0, -1), (1, 0), (0, 1), (-1, 0)] # Possible directions (Up, Right, Down, Left)
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

    def is_opposite_direction(self, new_direction):
        """Check if the new direction is opposite to the current direction"""
        return

    def draw_gui(self, screen, grid_size):
        """Draw the agent's GUI on the screen"""
        return

    def update(self, trains, passengers, grid_size, screen_width, screen_height):
        # self.logger.debug(f"Update de l'agent {self.agent_name}")
        start_time = time.time()
        
        self.all_trains = trains
        self.all_passengers = passengers
        self.grid_size = grid_size
        self.screen_width = screen_width
        self.screen_height = screen_height
        # self.is_dead = is_dead
        
        if self.agent_name not in self.all_trains and not self.waiting_for_respawn and not self.is_dead:
            # When the train dies
            self.logger.debug(f"Train {self.agent_name} not in the list of trains and not dead")
            self.is_dead = True
            self.death_time = time.time()
            self.respawn_cooldown = RESPAWN_COOLDOWN  # Define the Cooldown at 3 seconds after the first death
        
        if self.agent_name not in self.all_trains and self.is_dead  and not self.waiting_for_respawn:
            # When the train is already dead
            elapsed = time.time() - self.death_time
            remaining_time = max(0, self.respawn_cooldown - elapsed)

            if remaining_time == 0:
                if MANUAL_RESPAWN:
                    # Check if the space key is pressed
                    keys = pygame.key.get_pressed()
                    if keys[pygame.K_SPACE]:
                        # self.logger.info(f"Train {self.agent_name} requests a respawn")
                        self.logger.info(f"Train {self.agent_name} requests a respawn")
                        self.is_dead = False
                        self.waiting_for_respawn = True # Add this line
                        # self.death_time = None
                        self.send_action({"action": "respawn"})
                else:
                    # Respawn automatically
                    self.logger.info(f"Train {self.agent_name} requests a respawn")
                    self.is_dead = False
                    self.waiting_for_respawn = True # Add this line
                    # self.death_time = None
                    self.send_action({"action": "respawn"})
            
            return

        # If dead, do not send actions but continue the display
        if not self.is_dead and self.agent_name in self.all_trains:
            self.waiting_for_respawn = False # Add this line
            decision_start = time.time()
            direction = self.get_valid_direction(grid_size, screen_width, screen_height)
            # logger.debug(f"Train {self.agent_name} going {direction} from position {self.all_trains[self.agent_name]['position']}")
            decision_time = time.time() - decision_start
            if decision_time > 0.01:  # Log if more than 10ms
                self.logger.warning(f"Decision making took {decision_time*1000:.2f}ms")

            send_start = time.time()
            self.send_action(direction)

            # self.logger.debug(f"Train going {direction} from position {self.all_trains[self.agent_name]['position']}")

            send_time = time.time() - send_start
            if send_time > 0.01:
                self.logger.warning(f"Action sending took {send_time*1000:.2f}ms")

            total_time = time.time() - start_time
            if total_time > 0.05:  # Log if more than 50ms in total
                self.logger.warning(f"Total update took {total_time*1000:.2f}ms")
            # else:
                # self.logger.debug(f"Train {self.agent_name} is alive")