import random
from base_agent import BaseAgent
from network import NetworkManager


BASE_DIRECTIONS = [
    (0, -1),  # Up
    (1, 0),  # Right
    (0, 1),  # Down
    (-1, 0),  # Left
]


class Agent(BaseAgent):
    def get_direction(self):
        """
        This method is regularly called by the client to get the next direction of the train.
        """
        return random.choice(BASE_DIRECTIONS)  # Replace this with your own logic
