"""
Module for handling events for the I Like Trains client
"""
import pygame
import logging


# Configure the logger
logger = logging.getLogger("client.event_handler")

class EventHandler:
    """Class responsible for handling client events"""
    
    def __init__(self, client, activate_agent):
        """Initialize the event handler with a reference to the client"""
        self.client = client
        self.activate_agent = activate_agent
        
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.client.running = False
                return
                
            elif event.type == pygame.KEYDOWN:
                # If the agent is dead and the space key is pressed, request a respawn
                if event.key == pygame.K_SPACE:
                    if self.client.agent.is_dead and self.client.agent.waiting_for_respawn:
                        self.client.network.send_spawn_request()
                    if self.client.in_waiting_room:
                        self.client.network.send_start_game_request()
                
                if not self.activate_agent:
                    # Change the train's direction based on the pressed keys
                    if event.key == pygame.K_UP:
                        self.client.network.send_direction((0, -1))
                    elif event.key == pygame.K_DOWN:
                        self.client.network.send_direction((0, 1))
                    elif event.key == pygame.K_LEFT:
                        self.client.network.send_direction((-1, 0))
                    elif event.key == pygame.K_RIGHT:
                        self.client.network.send_direction((1, 0))
                    # key D drops a wagon
                    elif event.key == pygame.K_d:
                        self.client.network.send_drop_passenger()
                
                # Quit the game if the Escape key is pressed
                elif event.key == pygame.K_ESCAPE:
                    self.client.running = False
                    return
