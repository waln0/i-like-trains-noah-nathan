"""
Module for managing the game state for the client "I Like Trains"
"""
import logging
import time
import json
import pygame

# Configure the logger
logger = logging.getLogger("client.game_state")

# Constants
# RESPAWN_COOLDOWN = 3  # Respawn cooldown time in seconds

class GameState:
    """Class responsible for managing the game state"""
    
    def __init__(self, client):
        """Initialize the game state manager with a reference to the client"""
        self.client = client
        
    def update_agent(self):
        """Update the agent's state."""
        start_time = time.time()
        
        # Update the agent's data
        self.client.agent.all_trains = self.client.trains
        # Convert passenger dictionaries to position tuples if needed
        passenger_positions = []
        for p in self.client.passengers:
            if isinstance(p, dict) and "position" in p:
                passenger_positions.append(tuple(p["position"]))
            else:
                passenger_positions.append(tuple(p))
        self.client.agent.all_passengers = passenger_positions
        self.client.agent.grid_size = self.client.grid_size
        self.client.agent.game_width = self.client.game_width
        self.client.agent.game_height = self.client.game_height
        
        # If the agent is dead but its train is present in the trains, mark it as alive
        if self.client.agent.is_dead and self.client.agent_name in self.client.trains:
            self.client.agent.is_dead = False
            self.client.agent.waiting_for_respawn = False
            logger.info("Agent " + str(self.client.agent_name) + " is now alive")

        # If the agent is not dead and its train is not present, mark it as dead
        if not self.client.agent.is_dead and self.client.agent_name not in self.client.trains and not self.client.agent.waiting_for_respawn:
            self.client.agent.is_dead = True
            self.client.agent.death_time = time.time()
            self.client.agent.waiting_for_respawn = True
            logger.info("Agent " + str(self.client.agent_name) + " is now dead")

        # Automatic respawn if MANUAL_RESPAWN is false
        if not self.client.manual_respawn and self.client.agent.is_dead and self.client.agent.waiting_for_respawn:
            elapsed = time.time() - self.client.agent.death_time
            if elapsed >= self.client.agent.respawn_cooldown:
                if self.client.in_waiting_room:
                    self.client.network.send_start_game_request()
                # logger.debug("Auto respawning agent " + str(self.client.agent_name))
                self.client.network.send_respawn_request()

        # If the agent is present in the trains, update its position and direction
        if self.client.agent_name in self.client.trains:
            train_data = self.client.trains[self.client.agent_name]
            
            # Check if the train data is in the new format (dictionary)
            if isinstance(train_data, dict):
                # New format
                train_position = train_data.get("position", (0, 0))
                train_direction = train_data.get("direction", (1, 0))
                
                # Update the agent's position and direction
                self.client.agent.x, self.client.agent.y = train_position
                self.client.agent.direction = train_direction
                # Store the previous direction
            else:
                # Old format (for compatibility)
                try:
                    train_x, train_y, direction = train_data
                    self.client.agent.x = train_x
                    self.client.agent.y = train_y
                    self.client.agent.direction = direction
                except ValueError as e:
                    logger.error("Error unpacking train data for agent: " + str(e) + ", data: " + str(train_data))
        
        if not self.client.agent.is_dead and self.client.agent_name in self.client.trains:
            self.client.agent.waiting_for_respawn = False
            decision_start = time.time()
            
            # Let the agent make a decision
            direction = self.client.agent.get_direction(self.client.game_width, self.client.game_height)
            # logger.debug(f"Agent {self.client.agent_name} decided to go {direction}")
            
            # If the direction has changed, send it to the server
            if direction != self.client.agent.direction:
                self.client.network.send_direction(direction)
                
            decision_time = time.time() - decision_start
            if decision_time > 0.1:
                self.client.agent.logger.warning("Decision took " + str(decision_time*1000) + "ms")
                
        update_time = time.time() - start_time
        if update_time > 0.1:
            self.client.agent.logger.warning("Agent update took " + str(update_time*1000) + "ms")
            
    def handle_state_data(self, data):
        """Handle game state data received from the server"""
        try:
            if not isinstance(data, dict):
                logger.warning("Received non-dictionary state data: " + str(data))
                return
                
            # If we receive state data, we are no longer in the waiting room
            # self.client.in_waiting_room = False
            # logger.info("Client not in waiting room because we received state data")
            
            # Update game data only if present in the packet
            if "trains" in data:
                # Update only the modified trains
                for train_name, train_data in data["trains"].items():
                    if train_name not in self.client.trains:
                        self.client.trains[train_name] = {}
                    # Update the modified attributes
                    self.client.trains[train_name].update(train_data)
                
            if "passengers" in data:
                # Adjust passenger positions to be in pixel coordinates
                self.client.passengers = [(p[0], p[1]) for p in data["passengers"]]
                
            if "grid_size" in data:
                self.client.grid_size = data["grid_size"]
                
            if "game_width" in data and "game_height" in data:
                self.client.game_width = data["game_width"]
                self.client.game_height = data["game_height"]
                
            # Update the agent's state
            self.update_agent()
        except Exception as e:
            logger.error("Error handling state data: " + str(e))
            
    def handle_game_state(self, state):
        """Handle the complete game state received directly from the server"""
        try:
            if not isinstance(state, dict):
                logger.warning("Received non-dictionary game state: " + str(state))
                return
            
            # Update trains
            if "trains" in state:
                trains_data = state["trains"]
                self.client.trains = {}
                
                for agent_name, train_data in trains_data.items():
                    position = tuple(train_data.get("position", (0, 0)))
                    direction = tuple(train_data.get("direction", (0, 0)))
                    wagons = [tuple(w) for w in train_data.get("wagons", [])]
                    score = train_data.get("score", 0)
                    color = train_data.get("color", (0, 255, 0))
                    
                    self.client.trains[agent_name] = {
                        "position": position,
                        "direction": direction,
                        "wagons": wagons,
                        "score": score,
                        "color": color
                    }
            
            # Update passengers
            if "passengers" in state:
                passengers_data = state["passengers"]
                passengers_adjusted = []
                
                for passenger_data in passengers_data:
                    position = tuple(passenger_data)
                    passengers_adjusted.append(position)
                    
                self.client.passengers = passengers_adjusted
                
            # Update the agent's state
            self.update_agent()
        except Exception as e:
            logger.error("Error handling game state: " + str(e))
            
    def handle_respawn_data(self, data):
        """Handle respawn data received from the server"""
        try:
            if not isinstance(data, dict):
                logger.error("Respawn data is not a dictionary: " + str(data))
                return
                
            # Check if the respawn was successful
            success = data.get("success", False)
            
            if success:
                # The respawn was successful, the agent is no longer dead
                self.client.agent.is_dead = False
                self.client.agent.waiting_for_respawn = False
                logger.info("Respawn successful")
            else:
                # The respawn failed, the agent is still dead
                reason = data.get("reason", "Unknown reason")
                cooldown = data.get("cooldown", 0)
                
                # Update the cooldown
                if cooldown > 0:
                    self.client.agent.respawn_cooldown = cooldown
                    self.client.agent.death_time = time.time()
                    
                logger.warning("Respawn failed: " + str(reason))
        except Exception as e:
            logger.error("Error handling respawn data: " + str(e))
            
    def handle_leaderboard_data(self, data):
        """Handle leaderboard data received from the server"""
        logger.info("Received leaderboard data")
        try:
            # Check if data is a string and try to parse it as JSON
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    logger.error("Failed to parse leaderboard data as JSON: " + str(data))
                    return
                    
            # Check that data is a list
            if not isinstance(data, list):
                logger.error("Leaderboard data is not a list: " + str(type(data)))
                return
                
            # Update leaderboard data
            self.client.leaderboard_data = data
            
            # Display the leaderboard in a separate window only if explicitly requested
            if hasattr(self.client, 'show_separate_leaderboard') and self.client.show_separate_leaderboard:
                self.client.renderer.show_leaderboard_window(data)
        except Exception as e:
            logger.error("Error handling leaderboard data: " + str(e))
            
    def handle_waiting_room_data(self, data):
        """Handle waiting room data received from the server"""
        try:
            if not isinstance(data, dict):
                logger.error("Waiting room data is not a dictionary: " + str(data))
                return
                
            # Update waiting room data
            self.client.waiting_room_data = data
            logger.debug("Waiting room data updated: ")
            
        except Exception as e:
            logger.error("Error handling waiting room data: " + str(e))

    def handle_cooldown_data(self, data):
        """Handle cooldown data received from the server"""
        try:
            if not isinstance(data, dict):
                logger.error("Cooldown data is not a dictionary: " + str(data))
                return
                
            # Update the agent's cooldown data
            self.client.agent.respawn_cooldown = data.get("remaining", 0)
            # logger.info("Cooldown updated: " + str(self.client.agent.respawn_cooldown) + "s")
        except Exception as e:
            logger.error("Error handling cooldown data: " + str(e))
            
    def handle_game_status(self, data):
        """Gère la réception du statut du jeu"""
        try:
            game_started = data.get("game_started", False)
            if game_started:
                self.client.in_waiting_room = False
                logger.info("Game already started - joining ongoing game")
            else:
                self.client.in_waiting_room = True
                logger.info("Game not started - entering waiting room")
        except Exception as e:
            logger.error("Error handling game status: " + str(e))
            
    def handle_server_message(self, message):
        """Gère les messages reçus du serveur"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "game_state":
                self.handle_game_state(data)
            elif message_type == "waiting_room":
                self.handle_waiting_room_data(data)
            elif message_type == "game_status":
                self.handle_game_status(data)
            else:
                logger.warning("Unknown message type received: " + str(message_type))
        except Exception as e:
            logger.error("Error handling server message: " + str(e))