import random
import logging
import time
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("game_debug.log"), logging.StreamHandler()],
)

class BaseAgent(ABC):
    """Base class for all agents, enforcing the implementation of get_direction()."""

    def __init__(self, agent_name, network, logger="client.agent", is_dead=True):
        """
        Initialize the base agent
        
        Args:
            agent_name (str): The name of the agent
            network (Network): The network object to handle communication
            logger (str): The logger name
            is_dead (bool): Whether the agent is dead
        """
        self.logger = logging.getLogger(logger)
        self.agent_name = agent_name
        self.network = network

        self.directions = [
            (0, -1),  # Up
            (1, 0),   # Right
            (0, 1),   # Down
            (-1, 0)   # Left
        ]

        self.death_time = time.time()
        self.respawn_cooldown = 0
        self.is_dead = is_dead
        self.waiting_for_respawn = True

        self.logger.info(f"Agent {self.agent_name} initialized")
        
        self.max_wagons_before_drop = random.randint(3, 8) # Remove it in the template
        
    @abstractmethod
    def get_direction(self, game_width, game_height):
        """
        Abstract method to be implemented by subclasses.
        Must return a valid movement direction.
        """
        pass

    def update_agent(self):
        """Update the agent's state. Not supposed to be modified"""
        start_time = time.time()

        if self.agent_name in self.all_trains and not self.is_dead:
            try:
                train_data = self.all_trains.get(self.agent_name, None)
                
                if isinstance(train_data, dict):
                    self.x, self.y = train_data.get("position", (0, 0))
                    self.direction = train_data.get("direction", (1, 0))
            except Exception as e:
                self.logger.error(f"Error updating agent position: {e}")
        
        if not self.is_dead:
            try:
                direction = self.get_direction(self.game_width, self.game_height)
                if direction != self.direction:
                    self.network.send_direction_change(direction)
            except Exception as e:
                self.logger.error(f"Error making agent decision: {e}")

        update_time = time.time() - start_time
        if update_time > 0.1:
            self.logger.warning("Agent update took " + str(update_time * 1000) + "ms")