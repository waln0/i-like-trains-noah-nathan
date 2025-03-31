import random
import logging
from base_agent import BaseAgent
from network import NetworkManager


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("game_debug.log"), logging.StreamHandler()],
)

BASE_DIRECTIONS = [
    (0, -1),  # Up
    (1, 0),  # Right
    (0, 1),  # Down
    (-1, 0),  # Left
]


class Agent(BaseAgent):
    def __init__(
        self,
        agent_name: str,
        network: NetworkManager,
        logger: str = "client.agent",
        is_dead: bool = True,
    ):
        """
        Initialize the agent
        Args:
            agent_name (str): The name of the agent
            network (NetworkManager): The network object to handle communication
            logger (str): The logger name
            is_dead (bool): Whether the agent is dead
        """
        super().__init__(agent_name, network, logger, is_dead)

        self.logger.info(f"Agent {self.agent_name} initialized")

    def get_direction(self):
        """
        This method is regularly called by the client to get the next direction of the train.
        """
        return random.choice(BASE_DIRECTIONS)