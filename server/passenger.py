import pygame
import random
import logging

logger = logging.getLogger(__name__)

# Colors
RED = (255, 0, 0)

class Passenger:

    def __init__(self, game):
        self.game = game
        self.position = self.get_safe_spawn_position()
    
    def get_safe_spawn_position(self):
        """Find a safe spawn position, far from trains and other passengers"""
        max_attempts = 100
        grid_size = self.game.grid_size
        
        for _ in range(max_attempts):
            # Position aligned on the grid
            x = random.randint(0, (self.game.screen_width // grid_size) - 1) * grid_size
            y = random.randint(0, (self.game.screen_height // grid_size) - 1) * grid_size
            
            position_is_safe = True
            
            # Check collision with trains and their wagons
            for train in self.game.trains.values():
                if (x, y) == train.position:
                    position_is_safe = False
                    break
                    
                for wagon_pos in train.wagons:
                    if (x, y) == wagon_pos:
                        position_is_safe = False
                        break
                        
                if not position_is_safe:
                    break
                    
            # Check collision with other passengers
            for passenger in self.game.passengers:
                if passenger != self and (x, y) == passenger.position:
                    position_is_safe = False
                    break
                    
            if position_is_safe:
                logger.debug(f"Passenger spawned at position {(x, y)}")
                return (x, y)
                
        # Default position if no safe position is found
        logger.warning("No safe position found for passenger spawn")
        return (0, 0)
    
    def respawn(self):
        """Move the passenger to a new safe position or remove it if there are too many passengers"""
        # Check if there are more passengers than trains
        if len(self.game.passengers) > len(self.game.trains):
            # Remove this passenger from the list
            if self in self.game.passengers:
                self.game.passengers.remove(self)
                logger.debug(f"Passenger removed because there are too many passengers ({len(self.game.passengers)}) compared to the number of trains ({len(self.game.trains)})")
        else:
            # Otherwise, respawn normally
            self.position = self.get_safe_spawn_position()
            logger.debug(f"Passenger respawned at position {self.position}")