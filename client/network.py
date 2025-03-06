"""
Network manager class for the game "I Like Trains"
Handles all network communications between client and server
"""
import socket
import json
import logging
import threading
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("client.network")

class NetworkManager:
    """Class responsible for client network communications"""
    
    def __init__(self, client, host, port=5555):
        """Initialize network manager with client reference"""
        self.client = client
        self.host = host
        self.port = port
        self.socket = None
        self.running = True
        self.receive_thread = None
        
    def connect(self):
        """Establish connection with server"""
        try:
            # Create TCP/IP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            logger.info(f"Connected to server at {self.host}:{self.port}")
            
            # Start receive thread
            self.receive_thread = threading.Thread(target=self.receive_game_state)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            return False
            
    def disconnect(self):
        """Close connection with server"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
                logger.info("Disconnected from server")
            except Exception as e:
                logger.error(f"Error disconnecting from server: {e}")
                
    def send_message(self, message):
        """Send message to server"""
        if not self.socket:
            logger.error("Cannot send message: not connected to server")
            return False
            
        try:
            # Serialize message to JSON and send
            serialized = json.dumps(message) + "\n"
            self.socket.sendall(serialized.encode())
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
            
    def receive_game_state(self):
        """Thread that receives game state updates"""
        buffer = ""
        logger.debug("Starting receive_game_state thread")
        while self.running:
            try:
                # Receive data from server
                data = self.socket.recv(4096).decode()
                if not data:
                    logger.warning("Server closed connection")
                    self.running = False
                    break
                
                # Add data to buffer
                buffer += data

                # Process complete messages
                while "\n" in buffer:
                    # Extract complete message
                    message, buffer = buffer.split("\n", 1)
                    if not message:
                        logger.debug("Empty message, skipping")
                        continue

                    try:
                        # Parse JSON message
                        message_data = json.loads(message)

                        # Check message type
                        if "type" in message_data:
                            message_type = message_data["type"]
                            
                            # Handle different message types
                            if message_type == "state":
                                self.client.handle_state_data(message_data["data"])
                            elif message_type == "respawn":
                                logger.debug(f"Received respawn data: {message_data}")
                                self.client.handle_respawn_data(message_data["data"])
                            elif message_type == "respawn_success":
                                logger.info("Player respawned successfully")
                            elif message_type == "game_started_success":
                                logger.info("Game has started")
                                self.client.in_waiting_room = False
                            elif message_type == "game_status":
                                # logger.debug(f"\n\nReceived: {message_data}")
                                self.client.handle_game_status(message_data)
                            elif message_type == "leaderboard":
                                self.client.handle_leaderboard_data(message_data["data"])
                            elif message_type == "waiting_room":
                                self.client.handle_waiting_room_data(message_data["data"])
                            elif message_type == "name_check":
                                logger.debug(f"Received name_check response: {message_data}")
                                # Store name check result
                                self.client.name_check_result = message_data.get("available", False)
                                self.client.name_check_received = True
                                logger.debug(f"Name check response received, available: {self.client.name_check_result}")
                            elif message_type == "cooldown":
                                self.client.handle_cooldown_data(message_data)
                            elif message_type == "error":
                                logger.error(f"Received error from server: {message_data.get('message', 'Unknown error')}")
                            else:
                                logger.warning(f"Unknown message type: {message_type}")
                        else:
                            # If message has no type, treat it as game state
                            self.client.handle_game_state(message_data)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse message as JSON: {message}")
                    except Exception as e:
                        logger.error(f"Error handling message: {e}")
            except ConnectionResetError:
                logger.error("Connection reset by server")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error receiving data: {e}")
                self.running = False
                break
                
    def send_agent_name(self, agent_name):
        """Send agent name to server"""
        message = {"agent_name": agent_name}
        return self.send_message(message)
        
    def check_name_availability(self, name):
        """Check if a name is available on the server
        
        Returns True if name is available, False otherwise.
        """
        logger.info(f"Checking name availability for '{name}'")
        # Reset check variables
        self.client.name_check_received = False
        self.client.name_check_result = False
        
        # Send check request
        message = {"action": "check_name", "agent_name": name}
        success = self.send_message(message)
        
        if not success:
            logger.error(f"Failed to send name check request for '{name}'")
            return False
            
        # Wait for server response (with timeout)
        timeout = 5.0  # 5 second timeout
        start_time = time.time()
        
        logger.debug(f"Waiting for response with timeout of {timeout} seconds...")
        
        while not self.client.name_check_received and time.time() - start_time < timeout:
            time.sleep(0.1)
            
        if not self.client.name_check_received:
            logger.warning(f"Timeout waiting for name check response for '{name}'")
            return False
            
        logger.info(f"Name '{name}' availability result: {self.client.name_check_result}")
        return self.client.name_check_result
        
    def send_direction(self, direction):
        """Send direction to server"""
        message = {"action": "direction", "direction": direction}
        return self.send_message(message)
        
    def send_respawn_request(self):
        """Send respawn request to server"""
        message = {"action": "respawn"}
        current_time = time.time()
        if hasattr(self, 'last_respawn_request') and current_time - self.last_respawn_request < 1.0:
            logger.debug("Ignoring respawn request - too soon after previous request")
            return False
            
        logger.debug("Sending respawn request")
        
        success = self.send_message(message)
        if success:
            # Mark that we are waiting for server response
            self.client.agent.waiting_for_respawn = True
            
            # Record the time of this request
            self.last_respawn_request = current_time
            
            # If this was the first spawn, mark it as done
            if self.client.first_spawn:
                self.client.first_spawn = False
                logger.info("First spawn completed")
        return success
        
    def send_start_game_request(self):
        """Send request to start the game"""
        # Check if we've recently sent a start game request
        current_time = time.time()
        if hasattr(self, 'last_start_game_request') and current_time - self.last_start_game_request < 1.0:
            logger.debug("Ignoring start game request - too soon after previous request")
            return False
            
        logger.debug("Sending start game request")
        message = {"action": "start_game"}
        
        success = self.send_message(message)
        if success:
            logger.info("Requested game start")
            # Record the time of this request
            self.last_start_game_request = current_time
        return success
        
    def request_leaderboard(self):
        """Request leaderboard data from server"""
        # Create a message to request the leaderboard data
        message = {"action": "get_leaderboard"}
        
        # Send the message to the server
        success = self.send_message(message)
        
        # If the message was sent successfully, log a success message and indicate that we want to show the separate leaderboard
        if success:
            logger.info("Requested leaderboard data")
            self.client.show_separate_leaderboard = True  # Indicate that we want to show separate leaderboard
            
        # Return whether the request was successful
        return success
