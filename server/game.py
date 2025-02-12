import pygame
import random
import os
import importlib
import socket
import json
import threading
import time

from train import Train
from passenger import Passenger
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
DARK_GREEN = (0, 100, 0)

class Game:
    def __init__(self):
        self.screen_width = 200
        self.screen_height = 200
        self.grid_size = 20
        self.tick_rate = 60  # Augmentation pour plus de fluidité
        self.running = True
        self.trains = {} # {agent_name: Train}
        self.passengers = []
        self.screen_padding = 100
        self.lock = threading.Lock()
        self.spawn_safe_zone = 4  # Zone de sécurité en nombre de cases
        self.last_update = time.time()
        self.update_interval = 1.0 / self.tick_rate  # Intervalle fixe entre les updates
        logger.debug(f"Game initialized with tick rate: {self.tick_rate}")
    
    def run(self):
        logger.info("Game loop started")
        while self.running:
            self.update()
            import time
            time.sleep(1/self.tick_rate)

    def is_position_safe(self, x, y):
        """
        Vérifie si une position est sûre pour le spawn
        """
        # Vérification des bordures
        safe_distance = self.grid_size * self.spawn_safe_zone
        if (x < safe_distance or 
            y < safe_distance or 
            x > self.screen_width - safe_distance or 
            y > self.screen_height - safe_distance):
            return False

        # Vérification des autres trains et wagons
        for train in self.trains.values():
            # Distance au train
            train_x, train_y = train.position
            if (abs(train_x - x) < safe_distance and 
                abs(train_y - y) < safe_distance):
                return False
            
            # Distance aux wagons
            for wagon_x, wagon_y in train.wagons:
                if (abs(wagon_x - x) < safe_distance and 
                    abs(wagon_y - y) < safe_distance):
                    return False

        return True

    def get_random_grid_position(self):
        """
        Retourne une position aléatoire alignée sur la grille
        """
        x = random.randint(0, (self.screen_width // self.grid_size) - 1) * self.grid_size
        y = random.randint(0, (self.screen_height // self.grid_size) - 1) * self.grid_size
        return x, y

    def get_safe_spawn_position(self, max_attempts=100):
        """
        Trouve une position de spawn sûre
        """
        for _ in range(max_attempts):
            # Position alignée sur la grille
            x = random.randint(2, (self.screen_width // self.grid_size) - 3) * self.grid_size
            y = random.randint(2, (self.screen_height // self.grid_size) - 3) * self.grid_size
            
            if self.is_position_safe(x, y):
                logger.debug(f"Found safe spawn position at ({x}, {y})")
                return x, y

        # Position par défaut au centre
        center_x = (self.screen_width // 2) // self.grid_size * self.grid_size
        center_y = (self.screen_height // 2) // self.grid_size * self.grid_size
        logger.warning(f"Using default center position: ({center_x}, {center_y})")
        return center_x, center_y

    def add_train(self, agent_name):
        with self.lock:
            logger.debug(f"Adding train for agent: {agent_name}")
            start_x, start_y = self.get_safe_spawn_position()
            self.trains[agent_name] = Train(
                x=start_x,
                y=start_y,
                agent_name=agent_name
            )
            
            # Créer un nouveau passager pour ce train
            new_passenger = Passenger(self)
            self.passengers.append(new_passenger)
            
        self.update_screen_size()
        
    def remove_train(self, agent_name):
        """Supprime un train"""
        logger.debug(f"Removing train for agent: {agent_name}")
        
        # Supprimer le train
        if agent_name in self.trains:
            self.trains.pop(agent_name)
        
        # Mettre à jour la taille de l'écran
        if len(self.trains) > 0:
            # Réduire la taille si possible
            if self.can_reduce_padding():
                self.reduce_padding()
        else:
            # Réinitialiser la taille si plus aucun train
            self.screen_width = 200  # Taille initiale
            self.screen_height = 200
        
        logger.debug(f"Remaining trains: {len(self.trains)}, passengers: {len(self.passengers)}")
        logger.debug(f"New screen size: {self.screen_width}x{self.screen_height}")

    def can_reduce_padding(self):
        """Vérifie si on peut réduire la taille de l'écran"""
        logger.debug("Checking if padding can be reduced")
        for train in self.trains.values():
            x, y = train.position  # Accès direct à l'attribut position de l'objet Train

            if x >= self.screen_width - self.screen_padding - 50 or y >= self.screen_height - self.screen_padding - 50:
                return False
            for wagon_pos in train.wagons:  # Accès direct à l'attribut wagons
                x, y = wagon_pos
                if x >= self.screen_width - self.screen_padding - 50 or y >= self.screen_height - self.screen_padding - 50:
                    return False
        return True

    def reduce_padding(self):
        logger.debug("Reducing padding")
        if self.can_reduce_padding():
            self.screen_width -= self.screen_padding
            self.screen_height -= self.screen_padding

    def update(self):
        current_time = time.time()
        elapsed = current_time - self.last_update

        # Si pas assez de temps écoulé, on attend
        if elapsed < self.update_interval:
            return

        self.last_update = current_time

        with self.lock:
            # Update all trains
            for train_name, train in self.trains.items():
                train.update(self.passengers, self.grid_size)
                
    def update_screen_size(self):
        logger.debug("Updating screen size")
        self.screen_width += self.screen_padding
        self.screen_height += self.screen_padding

    def change_direction_of_train(self, agent_name, new_direction):
        """
        Change la direction d'un train spécifique
        """
        logger.debug(f"Changing direction of train {agent_name} to {new_direction}")
        if agent_name in self.trains:
            self.trains[agent_name].change_direction(new_direction)
        else:
            logger.warning(f"Train {agent_name} not found")