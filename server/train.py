import pygame
import random
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game_debug.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

# Directions
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

INITIAL_SPEED = 300 # max 380
SPEED_DECREMENT_COEFFICIENT = 0.95

def generate_random_non_blue_color():
    """Génère une couleur RGB aléatoire en évitant les nuances de bleu"""
    while True:
        r = random.randint(100, 255)  # Plus lumineux pour les trains
        g = random.randint(100, 255)
        b = random.randint(0, 100)    # Limiter le bleu
        
        # Si ce n'est pas une nuance de bleu (plus de rouge ou vert que de bleu)
        if r > b + 50 or g > b + 50:
            return (r, g, b)

class Train:

    def __init__(self, x, y, agent_name):
        self.position = (x, y)
        self.wagons = []
        self.direction = (1, 0)  # Commence vers la droite
        self.alive = True
        self.previous_direction = (1, 0)  # Commence avec la même direction
        self.agent_name = agent_name
        self.move_timer = 0
        self.speed = INITIAL_SPEED
        self.last_position = (x, y)
        self.color = generate_random_non_blue_color()  # Couleur du train
        self.wagon_color = tuple(min(c + 50, 255) for c in self.color)  # Wagons plus clairs
        # Utiliser à la fois le logger serveur et client
        self.server_logger = logging.getLogger('server.train')
        self.client_logger = logging.getLogger('client.train')
        self.server_logger.debug(f"Initializing train at position: {x}, {y} with color {self.color}")

    def get_position(self):
        return self.position

    def get_opposite_direction(self, direction):
        """Retourne la direction opposée"""
        return (-direction[0], -direction[1])

    def has_moved(self):
        """Vérifie si le train a bougé depuis sa dernière position"""
        has_moved = self.position != self.last_position
        # logger.debug(f"Has moved: {has_moved} (current: {self.position}, last: {self.last_position})")
        return has_moved

    def is_opposite_direction(self, new_direction):
        """Vérifie si la nouvelle direction est opposée à la direction précédente"""
        opposite = (-self.previous_direction[0], -self.previous_direction[1])
        # self.server_logger.debug(f"Previous direction: {self.previous_direction}")
        # self.server_logger.debug(f"Opposite direction: {opposite}")
        return tuple(new_direction) == opposite

    def change_direction(self, new_direction):
        """Change la direction du train si c'est possible"""
        current_direction = self.direction
        self.server_logger.debug(f"Attempting to change direction from {current_direction} to {new_direction}")
        
        # Convertir new_direction en tuple pour la comparaison
        new_direction = tuple(new_direction)
        
        # Vérifier si c'est une direction opposée
        if self.is_opposite_direction(new_direction):
            self.server_logger.debug("Cannot change direction: would be opposite direction")
            return False
            
        # Si la direction est la même, pas besoin de changer
        if new_direction == current_direction:
            # self.server_logger.debug("Already moving in this direction")
            return True
            
        # Appliquer le changement de direction
        # self.server_logger.debug(f"Changing direction to: {new_direction}")
        self.direction = new_direction
        return True

    def update(self, passengers, grid_size):
        """Met à jour la position du train"""
            
        self.move_timer += 1
        # if self.move_timer >= self.move_interval:
        if self.move_timer >= 1000/self.speed:
            self.move_timer = 0
            old_position = self.position
            self.move(grid_size, passengers)
            if self.position != old_position:
                self.last_position = old_position
                # self.server_logger.debug(f"Train moved from {old_position} to {self.position}")

    def add_wagon(self, position):
        self.speed = self.speed * SPEED_DECREMENT_COEFFICIENT
        self.wagons.append(position)

    def move(self, grid_size, passengers):
        """Déplacement à intervalle régulier"""
        # self.server_logger.debug(f"Moving train from {self.position} in direction {self.direction}")
        
        # Sauvegarder la dernière position du dernier wagon pour un possible nouveau wagon
        last_wagon_position = self.wagons[-1] if self.wagons else self.position
        
        # Mettre à jour la direction précédente avant le mouvement
        self.previous_direction = self.direction
        
        # Déplacer les wagons
        if self.wagons:
            for i in range(len(self.wagons) - 1, 0, -1):
                self.wagons[i] = self.wagons[i - 1]
            self.wagons[0] = self.position
        
        # Déplacer la locomotive
        new_position = (
            self.position[0] + self.direction[0] * grid_size,
            self.position[1] + self.direction[1] * grid_size
        )
        
        self.last_position = self.position
        self.position = new_position
        
        # self.server_logger.debug(f"Train moved to {self.position}")
        
        # Vérifier collision avec passager
        for passenger in passengers:
            if self.position == passenger.position:
                self.add_wagon(last_wagon_position)
                passenger.respawn()
                break

    def serialize(self):
        """
        Convertit l'état du train en un format sérialisable pour l'envoi au client
        """
        return {
            "position": self.position,
            "wagons": self.wagons,
            "direction": self.direction,
            "previous_direction": self.previous_direction,
            "name": self.agent_name,
            "color": self.color,
            "wagon_color": self.wagon_color
        }

    def check_collisions(self, all_trains):
        for wagon_pos in self.wagons:
            if self.position == wagon_pos:
                collision_msg = f"Train {self.agent_name} collided with its own wagon at {wagon_pos}"
                self.server_logger.warning(collision_msg)
                self.client_logger.warning(collision_msg)
                self.alive = False
                return True

        for train in all_trains.values():
            if train.agent_name == self.agent_name:
                continue
            
            # Vérifier la collision avec la tête du train
            if self.position == train.position:
                collision_msg = f"Train {self.agent_name} collided with train {train.agent_name}"
                self.server_logger.warning(collision_msg)
                self.client_logger.warning(collision_msg)
                self.alive = False
                train.alive = False  # Les deux trains meurent en collision frontale
                return True
            
            # Vérifier la collision avec les wagons
            for wagon_pos in train.wagons:
                if self.position == wagon_pos:
                    collision_msg = f"Train {self.agent_name} collided with wagon of train {train.agent_name}"
                    self.server_logger.warning(collision_msg)
                    self.client_logger.warning(collision_msg)
                    self.alive = False
                    return True
        
        return False

    def check_out_of_bounds(self, screen_width, screen_height):
        """Vérifie si le train est sorti de l'écran"""
        x, y = self.position
        if (x < 0 or x >= screen_width or y < 0 or y >= screen_height):
            self.server_logger.warning(f"Train {self.agent_name} est mort: sortie de l'écran. Coordonnées: {self.position}")
            self.alive = False
            return True
        return False