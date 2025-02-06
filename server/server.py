import socket
import json
import threading

from game import Game

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

HOST = "128.178.17.112/24"

class Server:
    """
    A class to represent a server for a multiplayer game.
    Attributes
    ----------
    host : str
        The hostname or IP address to bind the server to.
    port : int
        The port number to bind the server to.
    running : bool
        A flag to indicate if the server is running.
    game : Game
        An instance of the Game class to manage game state.
    clients : list
        A list to store connected client sockets.
    lock : threading.Lock
        A lock to synchronize access to shared resources.
    Methods
    -------
    __init__(host="localhost", port=5555):
        Initializes the server with the given host and port.
    start_server():
        Starts the server and begins listening for client connections.
    accept_clients():
        Accepts incoming client connections and starts a new thread to handle each client.
    handle_client(client_socket):
        Handles communication with a connected client.
    update():
        Updates the game state and broadcasts it to all connected clients.
    broadcast():
        Broadcasts the current game state to all connected clients.
    """


    def __init__(self, host=HOST, port=5555):
        self.host = host
        self.port = port
        self.running = True
        self.game = Game()
        self.clients = []
        self.lock = threading.Lock()
        self.start_server()

    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        print(f"Server started on {self.host}:{self.port}")
        threading.Thread(target=self.accept_clients).start()

    def accept_clients(self):
        while self.running:
            client_socket, addr = self.server_socket.accept()
            print(f"New client connected: {addr}")
            self.clients.append(client_socket)
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def handle_client(self, client_socket):
        agent_name = client_socket.recv(1024).decode()
        client_ip = client_socket.getpeername()[0]

        with self.lock:
            # Check if the name of the agent already exists
            if agent_name in self.game.trains:
                error_message = json.dumps({"error": "Agent name already exists"})
                client_socket.sendall(error_message.encode())
                client_socket.close()
                return

            # Check if the IP address is already connected
            for client in self.clients:
                if client.getpeername()[0] == client_ip:
                    error_message = json.dumps({"error": "IP address already connected"})
                    client_socket.sendall(error_message.encode())
                    client_socket.close()
                    return

            self.game.add_train(agent_name)
            self.clients.append(client_socket)

        while self.running:
            try:
                data = client_socket.recv(1024).decode()
                if not data:
                    break
                action = json.loads(data)
                if agent_name in self.trains:
                    self.game.change_direction_of_train(agent_name, (action["direction"]))
            except:
                break

    def update(self):
        self.game.update()
        self.broadcast()

    def broadcast(self):
        # Serialize the game state
        state = {"trains": {name: train.serialize() for name, train in self.game.trains.items()},
                 "passengers": [p.position for p in self.game.passengers], "grid_size": self.game.grid_size, "screen_with_x": self.game.screen_with_x, "screen_with_y": self.game.screen_with_y}
        data = json.dumps(state)
        for client in self.clients:
            try:
                client.sendall(data.encode())
            except:
                self.clients.remove(client)


if __name__ == "__main__":
    server = Server()
    while True:
        server.update()