import socket
import json
import threading
import time

from game import Game
import logging

#   
def setup_server_logger():
    # Delete existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Create a handler for the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # Define the format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Configure the main server logger
    server_logger = logging.getLogger('server')
    server_logger.setLevel(logging.DEBUG)
    server_logger.propagate = False
    server_logger.addHandler(console_handler)
    
    # Configure the loggers of the sub-modules
    modules = ['server.game', 'server.train', 'server.passenger']
    for module in modules:
        logger = logging.getLogger(module)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        logger.addHandler(console_handler)
    
    return server_logger

# Configure the server logger
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

MAX_FREQUENCY = 30 # Transfer frequency


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
        
        # Add the tick counter
        # self.tick_counter = 0
        
        # Start a thread dedicated to accepting clients
        threading.Thread(target=self.accept_clients).start()
        logger.warning("Server started on localhost:5555")

    def accept_clients(self):
        """Thread that waits for new connections"""
        while self.running:
            try:
                # Accept a new connection
                client_socket, addr = self.server_socket.accept()
                logger.warning(f"New client connected: {addr}")
                # Create a new thread to handle this client
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()
            except Exception as e:
                logger.error(f"Error accepting client: {e}")

    def handle_client(self, client_socket):
        """Thread dedicated to a specific client"""
        try:
            # First communication: the client sends its name
            agent_name = client_socket.recv(1024).decode().strip()
            logger.warning(f"Attempting to connect for agent: {agent_name}")

            with self.lock:
                # Check if the agent name already exists
                if any(name == agent_name for name in self.clients.values()):
                    logger.warning(f"Agent name already exists: {agent_name}")
                    error_message = json.dumps({"error": "Agent name already exists"}) + "\n"
                    client_socket.sendall(error_message.encode())
                    client_socket.close()
                    return
                
                # If the name is available, send a confirmation
                client_socket.sendall(json.dumps({"status": "ok"}).encode())

                # Add the client WITHOUT creating a train
                self.clients[client_socket] = agent_name
                logger.debug(f"Client {agent_name} connected, waiting for spawn request")

            buffer = ""
            while self.running:
                try:
                    data = client_socket.recv(1024).decode()
                    if not data:
                        break
                    
                    buffer += data
                    
                    while "\n" in buffer:
                        message, buffer = buffer.split("\n", 1)
                        if message:
                            try:
                                command = json.loads(message)
                                self.handle_client_message(client_socket, command)
                            except json.JSONDecodeError as e:
                                logger.warning(f"Invalid JSON from {agent_name}: {e}")
                            
                except Exception as e:
                    logger.warning(f"Error receiving from {agent_name}: {e}")
                    break

        finally:
            with self.lock:
                if client_socket in self.clients:
                    agent_name = self.clients[client_socket]
                    if agent_name in self.game.trains:  # Check if the train exists
                        self.game.remove_train(agent_name)
                    del self.clients[client_socket]
                    logger.warning(f"Client disconnected: {agent_name}")
            client_socket.close()

    def handle_client_message(self, client_socket, message):
        """Handles messages received from the client"""
        agent_name = self.clients[client_socket]
        
        if message.get("action") == "respawn":
            logger.debug(f"Received respawn request from {agent_name}")
            cooldown = self.game.get_train_cooldown(agent_name)
            
            if cooldown > 0:
                # Informer le client du temps de cooldown restant
                response = {
                    "type": "cooldown",
                    "remaining": cooldown
                }
                try:
                    client_socket.sendall((json.dumps(response) + "\n").encode())
                except:
                    logger.warning(f"Failed to send cooldown to {agent_name}")
            else:
                # Tenter le spawn
                if self.game.add_train(agent_name):
                    logger.info(f"Train {agent_name} respawned")
                else:
                    logger.warning(f"Failed to spawn train {agent_name}")
        
        elif message.get("action") == "direction":
            if agent_name in self.game.trains:
                self.game.trains[agent_name].change_direction(message["direction"])
            else:
                logger.warning(f"Train {agent_name} not found")

    def broadcast(self):
        if not self.clients:  # Broadcast only if there are clients
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
        if serialize_time > 0.01:  # Log if more than 10ms
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
                logger.warning(f"Client disconnected: {agent_name}")
                with self.lock:
                    self.clients.pop(client_socket, None)
                    self.game.remove_train(agent_name)

    def run_game(self):
        last_update = time.time()
        update_interval = 1.0 / self.game.tick_rate

        while self.running:
            current_time = time.time()
            elapsed = current_time - last_update

            # Update the game only if there are trains
            if elapsed >= update_interval and self.game.trains:
                self.game.update()
                last_update = current_time
                
                # Broadcast only if there are clients
                if self.clients:
                    self.broadcast()
            
            time.sleep(1/MAX_FREQUENCY)

if __name__ == "__main__":
    server = Server()
    # Start the game in a separate thread
    game_thread = threading.Thread(target=server.game.run)
    game_thread.start()
    
    # Main server loop
    while True:
        server.broadcast()
        time.sleep(1/MAX_FREQUENCY)