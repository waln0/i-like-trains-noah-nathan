import pygame
import random
import os
import importlib
import socket
import json
import threading
from agent import Agent
import logging

HOST = "localhost"
AUTO_SPAWN = True

# Logger configuration for the customer and agent
def setup_client_logger():
    # Delete existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Configure the main logger
    logger = logging.getLogger('client')
    logger.setLevel(logging.DEBUG)
    
    # Ensure logs are propagated to parents
    logger.propagate = False
    
    # Create a handler for the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # Define the format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add the handler to the logger
    logger.addHandler(console_handler)
    
    # Also configure the agent logger
    agent_logger = logging.getLogger('client.agent')
    agent_logger.setLevel(logging.DEBUG)
    agent_logger.addHandler(console_handler)
    agent_logger.propagate = False
    
    return logger

# Configure the logger before creating the agent
logger = setup_client_logger()

class Client:

    # HOST = "128.179.179.187"

    def __init__(self, agent_name, server_host=HOST, server_port=5555, auto_spawn=AUTO_SPAWN):
        self.agent_name = agent_name
        self.agent = Agent(agent_name, self.send_action, auto_spawn)
        self.server_host = server_host
        self.server_port = server_port
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
            
            # Wait for the server response to check if the name is accepted
            response = self.socket.recv(1024).decode()
            try:
                response_data = json.loads(response)
                if "error" in response_data:
                    logger.error(f"Connection error: {response_data['error']}")
                    self.socket.close()
                    pygame.quit()
                    print(f"Error: {response_data['error']}")
                    exit(1)
                elif response_data.get("status") == "ok":
                    logger.info("Connection accepted")
                    threading.Thread(target=self.receive_game_state).start()
                    self.init_game()
            except json.JSONDecodeError as e:
                logger.error(f"Server response decoding error: {e}")
                self.socket.close()
                raise
            
        except ConnectionRefusedError as e:
            logger.error(f"Unable to connect to server {self.server_host}:{self.server_port}")
            logger.error(str(e))
            raise
        except Exception as e:
            logger.error(f"An error occurred while trying to connect: {e}")
            raise

    def init_game(self):
        pygame.init()
        self.clock = pygame.time.Clock()

    def receive_game_state(self):
        buffer = ""
        self.socket.settimeout(None)  # No timeout for reception
        while self.running:
            try:
                # Receive the data
                data = self.socket.recv(4096).decode()
                if not data:
                    break
                
                # Add to the buffer
                buffer += data
                
                # Process each complete message (delimited by \n)
                messages = buffer.split("\n")
                # Keep the last incomplete message in the buffer
                buffer = messages[-1]
                
                # Process only the last complete message
                if len(messages) > 1:
                    try:
                        state = json.loads(messages[-2])  # Take the last complete message

                        # Update the game data
                        self.trains = state["trains"]
                        self.passengers = state["passengers"]
                        self.grid_size = state["grid_size"]
                        self.screen_width = state.get("screen_width", 800)
                        self.screen_height = state.get("screen_height", 800)
                        
                        # Update the agent if the train is alive
                        self.agent.update(self.trains, self.passengers, self.grid_size, self.screen_width, self.screen_height)
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON: {e}")
                
            except socket.timeout:
                continue  # Continue the loop in case of timeout
            except Exception as e:
                logger.error(f"Error in receive_game_state: {e}")
                break
        
        logger.warning("Stopped receiving game state")
        self.running = False

    def send_action(self, direction):
        try:
            # If it's a dictionary (case of respawn), send it directly
            if isinstance(direction, dict):
                action = direction
            else:
                action = {
                    "action": "direction",
                    "direction": list(direction)
                }
            self.socket.sendall((json.dumps(action) + "\n").encode())
        except Exception as e:
            logger.error(f"Error sending action: {e}")

    def run(self):
        pygame.init()  # Pygame initialization
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))  # Default window
        pygame.display.set_caption(f"Train Game - {self.agent_name}")
        
        while self.running:
            # Process events first
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                # Ignore window active/inactive events
                elif event.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWMOVED, 
                                  pygame.WINDOWENTER, pygame.WINDOWLEAVE):
                    continue
            
            # Update the screen size if necessary
            if self.screen_width != self.screen.get_width() or self.screen_height != self.screen.get_height():
                self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
            
            # Call the game rendering via the agent
            self.agent.draw_gui(self.screen, self.grid_size)
            
            # Small delay to avoid excessive CPU usage
            pygame.time.delay(1)
        
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