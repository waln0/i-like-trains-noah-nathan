import random
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("game_debug.log"), logging.StreamHandler()],
)


class Agent:
    def __init__(self, agent_name, network, logger="client.agent", is_dead=True):
        """
        Initialize the agent
        
        Args:
            agent_name (str): The name of the agent
            network (Network): The network object to handle communication
            logger (str): The logger name
            is_dead (bool): Whether the agent is dead
        """
        self.logger = logging.getLogger(logger)  # Customer's subcloger
        self.join_success = False
        self.agent_name = agent_name

        self.network = network

        self.directions = [
            (0, -1),
            (1, 0),
            (0, 1),
            (0, 1),
            (-1, 0),
        ]  # Possible directions (Up, Right, Down, Left)

        self.death_time = time.time()  # Initializing death time at startup
        self.respawn_cooldown = 0  # No cooldown at the first spawn
        self.is_dead = is_dead  # Start dead
        self.waiting_for_respawn = True

        # the self.game_width and self.game_height are initialized later by the server but are still accessible
        # self.game_width is the width of the game grid
        # self.game_height is the height of the game grid

        self.logger.info(f"Agent {self.agent_name} initialized")


    def update_agent(self):
        """Update the agent's state. Not supposed to be modified"""
        start_time = time.time()

        # If the agent is present in the trains, update its position and direction
        if self.agent_name in self.all_trains and not self.is_dead:
            try:
                train_data = self.all_trains.get(self.agent_name, None)
                
                # Check if the train data is in the new format (dictionary)
                if isinstance(train_data, dict):
                    # New format
                    train_position = train_data.get("position", (0, 0))
                    train_direction = train_data.get("direction", (1, 0))
                    
                    # Update the agent's position and direction
                    self.x, self.y = train_position
                    self.direction = train_direction
            except Exception as e:
                self.logger.error(f"Error updating agent position: {e}")
        
        if not self.is_dead:
            try:
                # Let the agent make a decision
                direction = self.get_direction(self.game_width, self.game_height)
            
                # If the direction has changed, send it to the server
                if direction != self.direction:
                    self.network.send_direction_change(direction)
            except Exception as e:
                self.logger.error(f"Error making agent decision: {e}")

        update_time = time.time() - start_time
        if update_time > 0.1:
            self.logger.warning("Agent update took " + str(update_time*1000) + "ms")

    def will_hit_wall(
        self, position, direction, grid_size, game_width, game_height
    ):
        """
        Check if the next position will hit a wall
        Args:
            position (tuple): The current position of the train
            direction (tuple): The direction of the train
            grid_size (int): The size of the grid
            game_width (int): The width of the game
            game_height (int): The height of the game
        Returns:
            bool: True if the next position will hit a wall, False otherwise
        """
        return

    def will_hit_train_or_wagon(self, position, direction):
        """Check if the direction leads to a collision with a train or wagon"""
        return

    def get_target_position(self, current_position):
        """Find the adapted target and return its position"""
        return

    def get_direction_to_target(self, current_position, target_position, valid_directions):
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