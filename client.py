import pygame
import random
import os
import importlib
import socket
import json
import threading
from agent import Agent

class Client:
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