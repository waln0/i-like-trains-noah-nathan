import pygame
import random
import os
import importlib
import socket
import json
import threading
from agent import Agent
import logging

# Configuration du logger pour le client et l'agent
def setup_client_logger():
    # Supprimer les handlers existants
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Configurer le logger principal
    logger = logging.getLogger('client')
    logger.setLevel(logging.DEBUG)
    
    # S'assurer que les logs sont propagés aux parents
    logger.propagate = False
    
    # Créer un handler pour la console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # Définir le format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Ajouter le handler au logger
    logger.addHandler(console_handler)
    
    # Configurer aussi le logger de l'agent
    agent_logger = logging.getLogger('client.agent')
    agent_logger.setLevel(logging.DEBUG)
    agent_logger.addHandler(console_handler)
    agent_logger.propagate = False
    
    return logger

# Configurer le logger avant de créer l'agent
logger = setup_client_logger()

class Client:

    HOST = "localhost"
    # HOST = "128.179.179.187"

    def __init__(self, agent_name, server_host=HOST, server_port=5555):
        self.agent_name = agent_name
        self.agent = Agent(agent_name, self.send_action)
        self.server_host = server_host
        self.server_port = server_port

        # self.tick_rate = 10
        self.running = True
        self.trains = []
        self.passengers = []

        self.grid_size = 0
        self.screen_width = 0
        self.screen_height = 0

        self.init_connection()

    def init_connection(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            self.socket.sendall(self.agent_name.encode())
            
            # Attendre la réponse du serveur pour vérifier si le nom est accepté
            response = self.socket.recv(1024).decode()
            try:
                response_data = json.loads(response)
                if "error" in response_data:
                    logger.error(f"Erreur de connexion: {response_data['error']}")
                    self.socket.close()
                    pygame.quit()
                    print(f"Erreur: {response_data['error']}")
                    exit(1)
                elif response_data.get("status") == "ok":
                    logger.info("Connexion acceptée")
                    threading.Thread(target=self.receive_game_state).start()
                    self.init_game()
            except json.JSONDecodeError as e:
                logger.error(f"Erreur de décodage de la réponse du serveur: {e}")
                self.socket.close()
                raise
            
        except ConnectionRefusedError as e:
            logger.error(f"Impossible de se connecter au serveur {self.server_host}:{self.server_port}")
            logger.error(str(e))
            raise
        except Exception as e:
            logger.error(f"Une erreur est survenue lors de la tentative de connexion: {e}")
            raise

    def init_game(self):
        pygame.init()
        self.clock = pygame.time.Clock()

    def receive_game_state(self):
        buffer = ""
        self.socket.settimeout(None)  # Pas de timeout pour la réception
        while self.running:
            try:
                # Recevoir les données
                data = self.socket.recv(4096).decode()
                if not data:
                    break
                
                # Ajouter au buffer
                buffer += data
                
                # Traiter chaque message complet (délimité par \n)
                messages = buffer.split("\n")
                # Garder le dernier message incomplet dans le buffer
                buffer = messages[-1]
                
                # Traiter uniquement le dernier message complet
                if len(messages) > 1:
                    try:
                        state = json.loads(messages[-2])  # Prendre le dernier message complet
                        # logger.debug(f"Updating game state")
                        
                        # Mise à jour des données du jeu
                        self.trains = state["trains"]
                        self.passengers = state["passengers"]
                        self.grid_size = state["grid_size"]
                        self.screen_width = state.get("screen_width", 800)
                        self.screen_height = state.get("screen_height", 800)
                        
                        # Mise à jour de l'agent si le train est vivant
                        self.agent.update(self.trains, self.passengers, self.grid_size, self.screen_width, self.screen_height)
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON: {e}")
                
            except socket.timeout:
                continue  # Continuer la boucle en cas de timeout
            except Exception as e:
                logger.error(f"Error in receive_game_state: {e}")
                break
        
        logger.warning("Stopped receiving game state")
        self.running = False

    def send_action(self, direction):
        try:
            # Ne pas envoyer d'action si le train est mort
            # if self.agent_name not in self.agent.all_trains:
            #     logger.debug("Train mort, pas d'envoi d'action")
            #     return
                
            # Si c'est un dictionnaire (cas du respawn), l'envoyer directement
            if isinstance(direction, dict):
                action = direction
            else:
                action = {
                    "action": "direction",
                    "direction": list(direction)
                }
            self.socket.sendall((json.dumps(action) + "\n").encode())
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'action: {e}")

    def run(self):
        pygame.init()  # Initialisation de Pygame
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))  # Fenêtre par défaut
        pygame.display.set_caption(f"Train Game - {self.agent_name}")
        
        while self.running:
            # Traiter les événements en premier
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                # Ignorer les événements de fenêtre active/inactive
                elif event.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWMOVED, 
                                  pygame.WINDOWENTER, pygame.WINDOWLEAVE):
                    continue
            
            # Mise à jour de la taille de l'écran si nécessaire
            if self.screen_width != self.screen.get_width() or self.screen_height != self.screen.get_height():
                self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
            
            # Appel du rendu du jeu via l'agent
            self.agent.draw_gui(self.screen, self.grid_size)
            
            # Petit délai pour éviter une utilisation CPU excessive
            pygame.time.delay(10)
        
        logger.warning("Client stopped")
        self.socket.close()
        pygame.quit()

if __name__ == "__main__":
    while True:
        agent_name = input("Enter agent name: ")
        if agent_name:
            break
        else:
            logger.warning("Agent name cannot be empty")
    client = Client(agent_name)
    client.run()