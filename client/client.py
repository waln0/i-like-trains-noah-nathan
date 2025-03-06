"""
Main module for the game "I Like Trains"
"""
import pygame
import sys
import logging
import time
import json
import threading
import socket
from .network import NetworkManager
from .renderer import Renderer
from .event_handler import EventHandler
from .game_state import GameState
from .ui import UI
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("client")

# Constants
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5555
SCREEN_WIDTH = 600  # Reduce screen width
SCREEN_HEIGHT = 400
GRID_SIZE = 20
LEADERBOARD_WIDTH = 300  # Width of the leaderboard on the right
MANUAL_RESPAWN = False  # Enable manual respawn


class Client:
    """Main client class"""
    
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT):
        """Initialize the client"""
        self.host = host
        self.port = port
        
        # Initialize state variables
        self.running = True
        self.is_initialized = False
        self.in_waiting_room = True
        self.first_spawn = True
        self.manual_respawn = MANUAL_RESPAWN
        
        # Name verification variables
        self.name_check_received = False
        self.name_check_result = False
        
        # Game data
        self.agent_name = ""
        self.trains = {}
        self.passengers = []
        self.grid_size = GRID_SIZE
        self.game_width = 200  # Initial game area width
        self.game_height = 200  # Initial game area height
        self.game_screen_padding = 20  # Space between game area and leaderboard
        self.leaderboard_width = LEADERBOARD_WIDTH
        self.leaderboard_data = []
        self.waiting_room_data = None

        # Calculate screen dimensions based on game area and leaderboard
        self.screen_width = SCREEN_WIDTH
        self.screen_height = SCREEN_HEIGHT
        
        # Initialize pygame
        pygame.init()
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("I Like Trains")
        self.is_initialized = True
        
        # Initialize components
        self.network = NetworkManager(self, host, port)
        self.renderer = Renderer(self)
        self.event_handler = EventHandler(self)
        self.game_state = GameState(self)
        self.ui = UI(self)
        
        # Reference to the agent (will be initialized later)
        self.agent = None
        
    def set_agent(self, agent):
        """Set the agent used by the client"""
        self.agent = agent
        self.agent_name = agent.agent_name
        
    def run(self):
        """Main client loop"""
        # Connect to server
        if not self.network.connect():
            logger.error("Failed to connect to server")
            return

        logger.info(f"self.screen_width : {self.screen_width}, self.screen_height : {self.screen_height}")
        logger.info(f"Grid size: {self.grid_size}")
            
        # Ask player to enter their name
        player_name = self.ui.get_player_name()
        
        # Update agent name
        self.agent.agent_name = player_name
        self.agent_name = player_name
        
        # Update window title
        pygame.display.set_caption(f"I Like Trains - {player_name}")
            
        # Send agent name to server
        if not self.network.send_agent_name(self.agent_name):
            logger.error("Failed to send agent name to server")
            return

        # Main loop
        clock = pygame.time.Clock()
        logger.info(f"Running client loop: {self.running}")
        while self.running:
            # Handle events
            self.event_handler.handle_events()
            
            # Draw the game
            self.renderer.draw_game()
            
            # Limit FPS
            clock.tick(60)
            
        # Close connection
        self.network.disconnect()
        pygame.quit()
        
    def handle_state_data(self, data):
        """Handle state data received from server"""
        self.game_state.handle_state_data(data)

    def handle_cooldown_data(self, data):
        """Handle cooldown data received from server"""
        self.game_state.handle_cooldown_data(data)
        
    def handle_game_state(self, state):
        """Handle complete game state received directly from server"""
        self.game_state.handle_game_state(state)

    def handle_game_status(self, data):
        """Handle game status received from server"""
        self.game_state.handle_game_status(data)
        
    def handle_respawn_data(self, data):
        """Handle respawn data received from server"""
        self.game_state.handle_respawn_data(data)
        
    def handle_leaderboard_data(self, data):
        """Handle leaderboard data received from server"""
        self.game_state.handle_leaderboard_data(data)
        
    def handle_waiting_room_data(self, data):
        """Handle waiting room data received from server"""
        self.game_state.handle_waiting_room_data(data)