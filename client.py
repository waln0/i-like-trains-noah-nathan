import pygame
import random
import os
import importlib
import socket
import json
import threading
from agent import Agent
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


class Client:

    HOST = "localhost"
    # HOST = "128.179.179.187"

    def __init__(self, agent_name, server_host=HOST, server_port=5555):
        self.agent_name = agent_name
        self.agent = Agent(agent_name, self.send_action)
        self.server_host = server_host
        self.server_port = server_port

        self.tick_rate = 10
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
            threading.Thread(target=self.receive_game_state).start()
            self.init_game()
        except ConnectionRefusedError:
            logger.warning(f"Impossible de se connecter au serveur {self.server_host}:{self.server_port}")
            logger.warning("Vérifiez que le serveur est en cours d'exécution et que l'adresse/port sont corrects")
            raise
        except Exception as e:
            logger.warning(f"Une erreur est survenue lors de la tentative de connexion: {e}")
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
                        
                        # Mise à jour de l'agent
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
        """Envoie une action au serveur après conversion en format JSON"""
        try:
            # Convertir le tuple en liste pour le JSON et ajouter un délimiteur
            action = json.dumps({"direction": list(direction)}) + "\n"
            self.socket.sendall(action.encode())
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'action: {e}")

    def run(self):
        pygame.init()  # Initialisation de Pygame
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))  # Fenêtre par défaut
        pygame.display.set_caption(f"Train Game - {self.agent_name}")
        
        while self.running:
            self.handle_events()
            
            # Mise à jour de la taille de l'écran si nécessaire
            if self.screen_width != self.screen.get_width() or self.screen_height != self.screen.get_height():
                self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
            
            # Appel du rendu du jeu via l'agent
            self.agent.draw_gui(self.screen, self.grid_size)
            self.clock.tick(self.tick_rate)
            
        logger.warning("Client stopped")
        self.socket.close()
        pygame.quit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

if __name__ == "__main__":
    while True:
        agent_name = input("Enter agent name: ")
        if agent_name:
            break
        else:
            logger.warning("Agent name cannot be empty")
    client = Client(agent_name)
    client.run()