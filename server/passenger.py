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
        """Trouve une position sûre pour spawn, loin des trains et autres passagers"""
        max_attempts = 100
        grid_size = self.game.grid_size
        
        for _ in range(max_attempts):
            # Position alignée sur la grille
            x = random.randint(0, (self.game.screen_width // grid_size) - 1) * grid_size
            y = random.randint(0, (self.game.screen_height // grid_size) - 1) * grid_size
            
            position_is_safe = True
            
            # Vérifier collision avec les trains et leurs wagons
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
                    
            # Vérifier collision avec les autres passagers
            for passenger in self.game.passengers:
                if passenger != self and (x, y) == passenger.position:
                    position_is_safe = False
                    break
                    
            if position_is_safe:
                logger.debug(f"Passager spawné à la position {(x, y)}")
                return (x, y)
                
        # Position par défaut si aucune position sûre n'est trouvée
        logger.warning("Aucune position sûre trouvée pour le spawn du passager")
        return (0, 0)
    
    def respawn(self):
        """Déplace le passager à une nouvelle position sûre ou le supprime si trop de passagers"""
        # Vérifier s'il y a plus de passagers que de trains
        if len(self.game.passengers) > len(self.game.trains):
            # Supprimer ce passager de la liste
            if self in self.game.passengers:
                self.game.passengers.remove(self)
                logger.debug(f"Passager supprimé car trop de passagers ({len(self.game.passengers)}) par rapport aux trains ({len(self.game.trains)})")
        else:
            # Sinon, respawn normal
            self.position = self.get_safe_spawn_position()
            logger.debug(f"Passager respawné à la position {self.position}")