import socket
import json
import threading

from game import Game
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

HOST = "localhost"


class Server:


    def __init__(self):
        self.game = Game()
        self.clients = {}  # {socket: agent_name}
        self.lock = threading.Lock()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('localhost', 5555))
        self.server_socket.listen(5)  # Accepte jusqu'à 5 connexions en attente
        self.running = True
        # Démarre un thread dédié à l'acceptation des clients
        threading.Thread(target=self.accept_clients).start()
        logger.warning("Server started on localhost:5555")

    def accept_clients(self):
        """Thread qui attend en permanence de nouvelles connexions"""
        while self.running:
            try:
                # Accepte une nouvelle connexion
                client_socket, addr = self.server_socket.accept()
                logger.warning(f"New client connected: {addr}")
                # Crée un nouveau thread pour gérer ce client
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()
            except Exception as e:
                logger.error(f"Error accepting client: {e}")

    def handle_client(self, client_socket):
        """Thread dédié à un client spécifique"""
        try:
            # Première communication : le client envoie son nom
            agent_name = client_socket.recv(1024).decode()
            logger.warning(f"Tentative de connexion pour l'agent: {agent_name}")

            with self.lock:
                # Vérifier si le nom d'agent existe déjà
                if any(name == agent_name for name in self.clients.values()):
                    logger.warning(f"Agent name already exists: {agent_name}")
                    error_message = json.dumps({"error": "Agent name already exists"}) + "\n"
                    client_socket.sendall(error_message.encode())
                    client_socket.close()
                    return

                # Ajouter le client et créer son train
                self.clients[client_socket] = agent_name
                logger.debug(f"Adding train for agent: {agent_name}")
                self.game.add_train(agent_name)

            # Boucle principale de réception des commandes du client
            while self.running:
                try:
                    data = client_socket.recv(1024).decode()
                    if not data:  # Client déconnecté
                        break
                    
                    # Traitement des commandes reçues (changement de direction)
                    command = json.loads(data)
                    if "direction" in command:
                        # Convertir la direction en tuple
                        direction = tuple(command["direction"])
                        self.game.change_direction_of_train(agent_name, direction)
                except json.JSONDecodeError as e:
                    logger.warning(f"Erreur de décodage JSON pour {agent_name}: {e}")
                    continue  # Continue instead of break to be more resilient
                except Exception as e:
                    logger.warning(f"Erreur pour {agent_name}: {e}")
                    break

        finally:
            # Nettoyage à la déconnexion du client
            with self.lock:
                if client_socket in self.clients:
                    agent_name = self.clients[client_socket]
                    self.game.remove_train(agent_name)
                    del self.clients[client_socket]
                    logger.warning(f"Déconnexion du client: {agent_name}")
            client_socket.close()

    def update(self):
        self.game.update()
        self.broadcast()

    def broadcast(self):
        state = {
            "trains": {name: train.serialize() for name, train in self.game.trains.items()},
            "passengers": [p.position for p in self.game.passengers],
            "grid_size": self.game.grid_size,
            "screen_width": self.game.screen_width,
            "screen_height": self.game.screen_height
        }
        data = json.dumps(state) + "\n"

        with self.lock:
            clients_to_update = list(self.clients.items())
        
        for client_socket, agent_name in clients_to_update:
            try:
                client_socket.sendall(data.encode())
            except:
                logger.warning(f"Client déconnecté: {agent_name}")
                with self.lock:
                    self.clients.pop(client_socket, None)
                    self.game.remove_train(agent_name)


if __name__ == "__main__":
    server = Server()
    # Démarrer le jeu dans un thread séparé
    game_thread = threading.Thread(target=server.game.run)
    game_thread.start()
    
    # Boucle principale du serveur
    while True:
        server.update()