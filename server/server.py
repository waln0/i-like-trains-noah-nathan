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

class Server:
    def __init__(self, host="0.0.0.0", port=5555):
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
        with self.lock:
            self.game.add_train(agent_name)
        
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
        
        with self.lock:
            self.game.remove_train(agent_name)
        client_socket.close()

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