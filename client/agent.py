import random
import logging
from base_agent import BaseAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("game_debug.log"), logging.StreamHandler()],
)


class Agent(BaseAgent):
    # =========================================
    # Required method
    # =========================================
    def get_direction(self, game_width, game_height):
        """
        Return a valid random direction that does not lead to a wall or a collision.
        This function is periodically called by the client to get a new decision.
        """
        return random.choice(self.directions)

    # =========================================
    # Helper methods (can be removed or completed)
    # =========================================
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

    def is_opposite_direction(self, new_direction):
        """Check if the new direction is opposite to the current direction"""
        return