"""
Module for handling events for the I Like Trains client
"""
import pygame
import logging
import sys

# Configure the logger
logger = logging.getLogger("client.event_handler")

class EventHandler:
    """Class responsible for handling client events"""
    
    def __init__(self, client):
        """Initialize the event handler with a reference to the client"""
        self.client = client
        
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.client.running = False
                return
                
            elif event.type == pygame.KEYDOWN:
                # If the agent is dead and the space key is pressed, request a respawn
                if event.key == pygame.K_SPACE:
                    # logger.debug("Pressed space")
                    # logger.debug(f"Agent is dead: {self.client.agent.is_dead}, waiting for respawn: {self.client.agent.waiting_for_respawn}")
                    if self.client.agent.is_dead and self.client.agent.waiting_for_respawn:
                        # logger.debug("Sending respawn request")
                        self.client.network.send_respawn_request()
                    # logger.debug(f"In waiting room: {self.client.in_waiting_room}")
                    if self.client.in_waiting_room:
                        # If we are in the waiting room, request the start of the game
                        # logger.debug("Sending start game request")
                        self.client.network.send_start_game_request()
                
                # # Change the train's direction based on the pressed keys
                # elif event.key == pygame.K_UP:
                #     self.client.network.send_direction((0, -1))
                # elif event.key == pygame.K_DOWN:
                #     self.client.network.send_direction((0, 1))
                # elif event.key == pygame.K_LEFT:
                #     self.client.network.send_direction((-1, 0))
                # elif event.key == pygame.K_RIGHT:
                #     self.client.network.send_direction((1, 0))
                
                # Quit the game if the Escape key is pressed
                elif event.key == pygame.K_ESCAPE:
                    self.client.running = False
                    return
