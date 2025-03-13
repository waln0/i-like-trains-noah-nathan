import random
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
    def __init__(self, agent_name, drop_passenger):
        """
        Initialize the agent
        
        Args:
            agent_name (str): The name of the agent
            send_direction (function): Function to send direction changes
            send_drop_passenger (function): Function to send passenger drop requests
        """

        self.logger = logging.getLogger("client.agent")  # Customer's subcloger
        self.join_success = False
        self.all_trains = {}
        self.agent_name = agent_name

        self.drop_passenger = drop_passenger

        self.grid_size = 0
        self.game_width = 0
        self.game_height = 0
        self.passengers_data = []

        self.directions = [
            (0, -1),
            (1, 0),
            (0, 1),
            (0, 1),
            (-1, 0),
        ]  # Possible directions (Up, Right, Down, Left)
        self.current_direction_index = 1  # Start going to the right
        self.changing_direction = False

        self.death_time = time.time()  # Initializing death time at startup
        self.respawn_cooldown = 0  # No cooldown at the first spawn
        self.is_dead = True  # Start dead
        self.waiting_for_respawn = True

    def will_hit_wall(
        self, position, direction, grid_size, game_width, game_height
    ):
        """Check if the next position will hit a wall"""
        return

    def will_hit_train_or_wagon(self, position, direction):
        """Check if the direction leads to a collision with a train or wagon"""
        return

    def get_target_position(self, current_pos):
        """Find the closest passenger and return its position"""
        return

    def get_direction_to_target(self, current_pos, target_pos, valid_directions):
        """Determine the best direction among the valid ones to reach the target the fastest"""
        return

    def get_direction(self, game_width, game_height):
        """
        Return a valid random direction that does not lead to a wall or a collision.
        This function is periodically called by the client to get a new decision.
        """
        return random.choice(self.directions)

    def is_opposite_direction(self, new_direction):
        """Check if the new direction is opposite to the current direction"""
        return

    def update_agent(self, client):
        """
        Update the agent's state.
        The student can add their own code here if they wish but removing code from this function may cause issues with updating the agent's state.
        """
        start_time = time.time()
        
        # Update the agent's data
        self.all_trains = client.trains
        self.grid_size = client.grid_size
        self.game_width = client.game_width
        self.game_height = client.game_height
        self.passengers_data = client.passengers

        # If the agent is present in the trains, update its position and direction
        if client.agent_name in client.trains and not self.is_dead:
            train_data = client.trains.get(client.agent_name, None)
            
            # Check if the train data is in the new format (dictionary)
            if isinstance(train_data, dict):
                # New format
                train_position = train_data.get("position", (0, 0))
                train_direction = train_data.get("direction", (1, 0))
                
                # Update the agent's position and direction
                self.x, self.y = train_position
                self.direction = train_direction
        
        if not self.is_dead:
            decision_start = time.time()
            
            # Let the agent make a decision
            direction = self.get_direction(client.game_width, client.game_height)
        
            # If the direction has changed, send it to the server
            if direction != self.direction:
                client.network.send_direction(direction)
                
            decision_time = time.time() - decision_start
            if decision_time > 0.1:  # Log if decision takes more than 100ms
                logger.warning(f"Agent decision took {decision_time*1000:.1f}ms")

        update_time = time.time() - start_time
        if update_time > 0.1:
            self.logger.warning("Agent update took " + str(update_time*1000) + "ms")