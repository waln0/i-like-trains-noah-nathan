import socket
import json
import threading
import time

from game import Game
import logging

# Configuration du logger pour le serveur
def setup_server_logger():
    # Supprimer les handlers existants
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Configurer le logger du serveur
    logger = logging.getLogger('server')
    logger.setLevel(logging.DEBUG)
    
    # Important: désactiver la propagation vers le root logger
    logger.propagate = False
    
    # Créer un handler pour la console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # Définir le format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Ajouter le handler au logger
    logger.addHandler(console_handler)
    
    # Configurer aussi les loggers des sous-modules du serveur
    game_logger = logging.getLogger('server.game')
    game_logger.setLevel(logging.DEBUG)
    game_logger.propagate = False
    game_logger.addHandler(console_handler)
    
    train_logger = logging.getLogger('server.train')
    train_logger.setLevel(logging.DEBUG)
    train_logger.propagate = False
    train_logger.addHandler(console_handler)
    
    return logger

# Configurer le logger du serveur
logger = setup_server_logger()

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

MAX_FREQUENCY = 30 # Fréquence de transfert des données


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
        
        # Ajout du compteur de ticks
        # self.tick_counter = 0
        
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
            agent_name = client_socket.recv(1024).decode().strip()
            logger.warning(f"Tentative de connexion pour l'agent: {agent_name}")

            with self.lock:
                # Vérifier si le nom d'agent existe déjà
                if any(name == agent_name for name in self.clients.values()):
                    logger.warning(f"Agent name already exists: {agent_name}")
                    error_message = json.dumps({"error": "Agent name already exists"}) + "\n"
                    client_socket.sendall(error_message.encode())
                    client_socket.close()
                    return
                
                # Si le nom est disponible, envoyer une confirmation
                client_socket.sendall(json.dumps({"status": "ok"}).encode())

                # Ajouter le client et créer son train
                self.clients[client_socket] = agent_name
                logger.debug(f"Adding train for agent: {agent_name}")
                self.game.add_train(agent_name)

            buffer = ""  # Buffer pour accumuler les données
            while self.running:
                try:
                    data = client_socket.recv(1024).decode()
                    if not data:  # Client déconnecté
                        break
                    
                    buffer += data  # Ajouter les nouvelles données au buffer
                    
                    # Traiter tous les messages complets dans le buffer
                    while "\n" in buffer:
                        message, buffer = buffer.split("\n", 1)  # Séparer le premier message complet
                        if message:  # Ignorer les messages vides
                            try:
                                command = json.loads(message)
                                if "direction" in command:
                                    direction = tuple(command["direction"])
                                    self.game.change_direction_of_train(agent_name, direction)
                                elif "action" in command:
                                    self.handle_client_message(client_socket, command)
                            except json.JSONDecodeError as e:
                                logger.warning(f"Erreur de décodage JSON pour {agent_name}: {e}")
                            except Exception as e:
                                logger.warning(f"Erreur pour {agent_name}: {e}")
                            
                except Exception as e:
                    logger.warning(f"Erreur de connexion pour {agent_name}: {e}")
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

    def handle_client_message(self, client_socket, message):
        """Gère les messages reçus du client"""
        agent_name = self.clients[client_socket]  # Récupérer le nom de l'agent
        
        if message.get("action") == "respawn":
            logger.debug(f"Received respawn from {agent_name}")
            if agent_name not in self.game.trains:
                self.game.add_train(agent_name)
                logger.info(f"Train {agent_name} respawned")
        # elif message.get("action") == "direction":
        #     logger.debug(f"Received direction from {agent_name}: {message['direction']}")

    def broadcast(self):
        if not self.clients:  # Ne broadcast que s'il y a des clients
            return
            
        start_time = time.time()
        state = {
            "trains": {name: train.serialize() for name, train in self.game.trains.items()},
            "passengers": [p.position for p in self.game.passengers],
            "grid_size": self.game.grid_size,
            "screen_width": self.game.screen_width,
            "screen_height": self.game.screen_height
        }
        serialize_time = time.time() - start_time
        if serialize_time > 0.01:  # Log si plus de 10ms
            logger.warning(f"Serialization took {serialize_time*1000:.2f}ms")

        data = json.dumps(state) + "\n"
        json_time = time.time() - start_time - serialize_time
        if json_time > 0.01:
            logger.warning(f"JSON encoding took {json_time*1000:.2f}ms")

        with self.lock:
            clients_to_update = list(self.clients.items())
        
        for client_socket, agent_name in clients_to_update:
            send_start = time.time()
            try:
                client_socket.sendall(data.encode())
                send_time = time.time() - send_start
                if send_time > 0.01:
                    logger.warning(f"Sending to {agent_name} took {send_time*1000:.2f}ms")
            except:
                logger.warning(f"Client déconnecté: {agent_name}")
                with self.lock:
                    self.clients.pop(client_socket, None)
                    self.game.remove_train(agent_name)

    def run_game(self):
        last_update = time.time()
        update_interval = 1.0 / self.game.tick_rate

        while self.running:
            current_time = time.time()
            elapsed = current_time - last_update

            # Update le jeu seulement s'il y a des trains
            if elapsed >= update_interval and self.game.trains:
                self.game.update()
                last_update = current_time
                
                # Broadcast seulement s'il y a des clients
                if self.clients:
                    self.broadcast()
            
            time.sleep(1/MAX_FREQUENCY)

if __name__ == "__main__":
    server = Server()
    # Démarrer le jeu dans un thread séparé
    game_thread = threading.Thread(target=server.game.run)
    game_thread.start()
    
    # Boucle principale du serveur
    while True:
        server.broadcast()
        time.sleep(1/MAX_FREQUENCY)