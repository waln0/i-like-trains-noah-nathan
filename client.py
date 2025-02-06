import pygame
import random
import os
import importlib
import socket
import json
import threading
from agent import Agent

class Client:
    """
    A client class to connect to a server, receive game state updates, and send actions.
    Attributes:
        agent_name (str): The name of the agent.
        agent (Agent): An instance of the Agent class.
        server_host (str): The server host address.
        server_port (int): The server port number.
        tick_rate (int): The tick rate for the game loop.
        running (bool): A flag to indicate if the client is running.
        trains (list): A list of trains in the game state.
        passengers (list): A list of passengers in the game state.
        grid_size (int): The size of the game grid.
        screen_with_x (int): The width of the game screen.
        screen_with_y (int): The height of the game screen.
        socket (socket.socket): The socket object for server communication.
        screen (pygame.Surface): The pygame screen surface.
        clock (pygame.time.Clock): The pygame clock object.
    Methods:
        __init__(agent_name, screen_with_x, screen_with_y, tick_rate, server_host="localhost", server_port=5555):
            Initializes the Client instance with the given parameters.
        init_connection():
            Initializes the connection to the server and starts the game state receiving thread.
        init_game():
            Initializes the pygame screen and clock.
        receive_game_state():
            Receives the game state from the server and updates the client state.
        send_action(direction):
            Sends an action to the server.
        run():
            Runs the main game loop, handling events and updating the screen.
        handle_events():
            Handles pygame events, including quitting the game.
    """



    def __init__(self, agent_name, screen_with_x, screen_with_y, tick_rate, server_host="localhost", server_port=5555):
        self.agent_name = agent_name
        self.agent = Agent()
        self.server_host = server_host
        self.server_port = server_port
        self.tick_rate = tick_rate
        self.running = True
        self.trains = []
        self.passengers = []
        self.grid_size = 0
        self.screen_with_x = 0
        self.screen_with_y = 0

        self.init_connection()

    def init_connection(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.server_host, self.server_port))
        self.socket.sendall(self.agent_name.encode())
        threading.Thread(target=self.receive_game_state).start()
        self.init_game()

    def init_game(self):
        pygame.init()
        self.screen = pygame.display.set_mode((self.screen_with_x, self.screen_with_y))
        self.clock = pygame.time.Clock()

    def receive_game_state(self):
        while self.running:
            try:
                data = self.socket.recv(1024).decode()
                state = json.loads(data)
                self.trains = state["trains"]
                self.passengers = state["passengers"]
                self.grid_size = state["grid_size"]
                self.screen_with_x = state["screen_width_x"]
                self.screen_with_y = state["screen_width_y"]
                self.agent.update(self.trains, self.passengers)
            except:
                break

    def send_action(self, direction):
        action = json.dumps({"direction": direction})
        self.socket.sendall(action.encode())

    def run(self):
        while self.running:
            self.handle_events()
            draw_gui()
            self.clock.tick(self.tick_rate)
        self.socket.close()
        pygame.quit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

if __name__ == "__main__":
    agent_name = input("Enter agent name: ")
    client = Client(agent_name)
    client.run()