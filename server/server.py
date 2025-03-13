import socket
import json
import threading
import time
import sys
import logging
import uuid

from game import Game
from passenger import Passenger

# Transfer frequency
MAX_FREQUENCY = 30

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

# Default host
HOST = "localhost"
ALLOW_MULTIPLE_CONNECTIONS = True
DEFAULT_NB_PLAYERS_PER_ROOM = 0  # Default max players per room

# Check if an IP address has argued in argument
if len(sys.argv) > 1:
    HOST = sys.argv[1]

# Check if max players per room is provided as second argument
if len(sys.argv) > 2:
    try:
        DEFAULT_NB_PLAYERS_PER_ROOM = int(sys.argv[2])
    except ValueError:
        print(f"Invalid number of players value: {sys.argv[2]}. Using default: {DEFAULT_NB_PLAYERS_PER_ROOM}")


def setup_server_logger():
    # Delete existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Create a handler for the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # Define the format
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)

    # Configure the main server logger
    server_logger = logging.getLogger("server")
    server_logger.setLevel(logging.DEBUG)
    server_logger.propagate = False
    server_logger.addHandler(console_handler)

    # Configure the loggers of the sub-modules
    modules = ["server.game", "server.train", "server.passenger"]
    for module in modules:
        logger = logging.getLogger(module)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        logger.addHandler(console_handler)

    return server_logger


# Configure the server logger
logger = setup_server_logger()
logger.info(f"The server starts on {HOST}")


class Room:
    def __init__(self, room_id, nb_players, running, server):
        self.id = room_id
        self.nb_players = nb_players
        self.game = Game(server.send_cooldown_notification)
        self.game.room_id = room_id  # Store the room ID in the Game object
        self.game.server = server  # Give a reference to the server
        self.clients = {}  # {socket: agent_name}
        self.game_thread = None
        self.running = running  # The room is active by default
        self.waiting_room_thread = threading.Thread(target=self.broadcast_waiting_room)
        self.waiting_room_thread.daemon = True
        self.waiting_room_thread.start()
        logger.info(f"Room {room_id} created with number of players {nb_players}")

    def start_game(self):
        self.state_thread = threading.Thread(target=self.broadcast_game_state)
        self.state_thread.daemon = True
        self.state_thread.start()

        logger.info(f"\nStarting game for room {self.id}")
        if not self.game_thread:
            # Initialize game size based on connected players
            self.game.start_game(len(self.clients))

            # Start the game thread
            self.game_thread = threading.Thread(target=self.game.run)
            self.game_thread.daemon = True
            self.game_thread.start()

            response = {"type": "game_started_success"}
            # Send response to all clients
            for client_socket in list(self.clients.keys()):
                try:
                    client_socket.sendall((json.dumps(response) + "\n").encode())
                except Exception as e:
                    logger.error(f"Error sending start success to client: {e}")

            logger.info(f"Game started in room {self.id} with {len(self.clients)} players")

    def is_full(self):
        # logger.debug(f"Room {self.id} has {len(self.clients)} clients and {self.nb_players} max players")
        return len(self.clients) >= self.nb_players

    def get_player_count(self):
        return len(self.clients)

    def broadcast_waiting_room(self):
        """Broadcast waiting room data to all clients"""
        last_update = time.time()
        while self.running:
            try:
                if self.clients and not self.game_thread:
                    current_time = time.time()
                    if current_time - last_update >= 1.0 / MAX_FREQUENCY:  # Limit to MAX_FREQUENCY Hz
                        if self.clients:
                            waiting_room_data = {
                                "type": "waiting_room",
                                "data": {
                                    "room_id": self.id,
                                    "players": list(self.clients.values()),
                                    "nb_players": self.nb_players,
                                    "game_started": self.game_thread is not None
                                }
                            }

                            state_json = json.dumps(waiting_room_data) + "\n"
                            for client_socket in list(self.clients.keys()):
                                try:
                                    client_socket.sendall(state_json.encode())
                                except Exception as e:
                                    logger.error(f"Error sending waiting room data to client: {e}")

                        last_update = current_time

                time.sleep(1.0 / (MAX_FREQUENCY * 2))  # Sleep for half the period
            except Exception as e:
                logger.error(f"Error in broadcast_waiting_room: {e}")
                time.sleep(1.0 / MAX_FREQUENCY)

    def broadcast_game_state(self):
        """Thread that periodically sends the game state to clients"""
        last_update = time.time()
        while self.running:
            try:
                # Calculate the time elapsed since the last update
                current_time = time.time()
                elapsed = current_time - last_update

                # If enough time has passed
                if elapsed >= 1.0 / MAX_FREQUENCY:
                    # Get the game state with only the modified data
                    state = self.game.get_state()
                    if state:  # If data has been modified
                        # Create the data packet
                        state_data = {
                            "type": "state",
                            "data": state
                        }

                        # Send the state to all clients
                        state_json = json.dumps(state_data) + "\n"
                        for client_socket in self.clients:
                            try:
                                client_socket.sendall(state_json.encode())
                            except Exception as e:
                                logger.error(f"Error sending state to client: {e}")

                    last_update = current_time

                # Wait a bit to avoid overloading the CPU
                time.sleep(1.0 / (MAX_FREQUENCY * 2))
            except Exception as e:
                logger.error(f"Error in broadcast_game_state: {e}")
                time.sleep(1.0 / MAX_FREQUENCY)


class Server:
    def __init__(self):
        self.rooms = {}  # {room_id: Room}
        self.lock = threading.Lock()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((HOST, 5555))
        self.server_socket.listen(5)  # Accept up to 5 pending connections
        self.running = True
        self.nb_players = DEFAULT_NB_PLAYERS_PER_ROOM

        # Get the number of players per room
        while True:
            try:
                player_input = input("Enter number of players per room: ").strip()
                if not player_input:
                    print("Please enter a valid number (minimum 1)")
                    continue
                self.nb_players = int(player_input)
                if self.nb_players < 1:
                    print("Number of players must be at least 1")
                    continue
                break
            except ValueError:
                print("Please enter a valid number (minimum 1)")

        # Create the first room
        self.create_room(self.nb_players, running=True)

        # Start accepting clients
        threading.Thread(target=self.accept_clients).start()
        logger.info(f"Server started on {HOST}")

    def create_room(self, nb_players, running):
        """Create a new room with specified number of players"""
        room_id = str(uuid.uuid4())[:8]
        new_room = Room(room_id, nb_players, running, server=self)
        logger.info(f"Created new room {room_id} with {nb_players} players")
        self.rooms[room_id] = new_room
        return new_room

    def get_available_room(self, nb_players):
        """Get an available room or create a new one if needed"""
        logger.debug(f"Getting available room for {nb_players} players")
        # First try to find a non-full room
        for room in self.rooms.values():
            logger.debug(f"Checking room {room.id} for {nb_players} players")
            if (room.nb_players == nb_players and 
                not room.is_full() and 
                not room.game_thread):
                return room
        logger.debug(f"No suitable room found for {nb_players} players")
        # If no suitable room found, create a new one
        return self.create_room(nb_players, running=True)

    def accept_clients(self):
        """Thread that waits for new connections"""
        while self.running:
            try:
                # Accept a new connection
                client_socket, addr = self.server_socket.accept()
                logger.info(f"New client connected: {addr}")
                # Create a new thread to handle this client
                threading.Thread(
                    target=self.handle_client, args=(client_socket,)
                ).start()
            except Exception as e:
                logger.error(f"Error accepting client: {e}")

    def initialize_name(self, client_socket, agent_name=None):
        # Receive the first message - may be a name check or an agent_name
        buffer = ""
        # Process messages until we get a valid agent_name
        while agent_name is None:
            logger.debug(f"Waiting for agent name confirmation")
            data = client_socket.recv(1024).decode()
            if not data:
                logger.warning("No data received from client")
                client_socket.close()
                return

            logger.debug(f"Received initial data from client: {data}")

            buffer += data
            # Process complete messages
            while "\n" in buffer:
                logger.debug(f"Trimming buffer")
                message_str, buffer = buffer.split("\n", 1)
                if not message_str:
                    continue

                try:
                    message = json.loads(message_str)

                    # Check the message type
                    if "action" in message and message["action"] == "check_name":
                        # It's a name check
                        logger.debug(f"Checking name availability for {message.get('agent_name')}")
                        name_to_check = message.get("agent_name", "")
                        if not name_to_check:
                            # Empty name, considered as not available
                            response = {
                                "type": "name_check",
                                "available": False
                            }
                            logger.debug(f"Empty name check, sending response: {response}")
                            try:
                                client_socket.sendall((json.dumps(response) + "\n").encode())
                                logger.debug("Response sent successfully for empty name check")
                            except Exception as e:
                                logger.error(f"Error sending name check response: {e}")
                            continue  # Continue waiting for another message

                        # Check if the name exists in any room
                        name_available = True
                        for room_id, room in self.rooms.items():
                            if name_to_check in room.clients.values():
                                name_available = False
                                logger.debug(f"Name '{name_to_check}' found in room {room_id}")
                                break

                        if name_available:
                            logger.debug(f"Name '{name_to_check}' is available across all rooms")

                        # Send the response to the client
                        response = {
                            "type": "name_check",
                            "available": name_available
                        }
                        logger.debug(f"Sending name check response: {response}")
                        try:
                            client_socket.sendall((json.dumps(response) + "\n").encode())
                            logger.info(f"Name check for '{name_to_check}': {'available' if name_available else 'not available'}")
                        except Exception as e:
                            logger.error(f"Error sending name check response: {e}")

                        # Continue waiting for another message (like agent_name)
                        continue

                    elif "agent_name" in message:
                        # It's an agent connection
                        agent_name = message["agent_name"]
                        if not agent_name:
                            logger.warning("No agent name provided")
                            client_socket.close()
                            return

                        logger.info(f"Agent {agent_name} attempting to connect")
                        # We have a valid agent_name, we can exit the loop
                        break
                    else:
                        logger.warning(f"Unknown initial message type: {message}")
                        continue  # Ignore and wait for another message

                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {message_str}")
                    continue  # Ignore and wait for another message

        logger.debug(f"Verified agent name: {agent_name}")

        # At this point, we have a valid agent_name
        with self.lock:
            logger.debug(f"Checking if agent {agent_name} already exists in a room")
            # Check if the name is already used
            name_exists = any(agent_name in room.clients.values()
                              for room in self.rooms.values())

            if name_exists:
                logger.debug(f"Agent {agent_name} already exists in a room")
                response = {
                    "type": "error",
                    "message": "Agent name already in use"
                }
                client_socket.sendall((json.dumps(response) + "\n").encode())
                client_socket.close()
                return

            logger.debug(f"Agent {agent_name} is available, proceeding to room selection")
            return agent_name

    def handle_client(self, client_socket):
        """Thread dedicated to a specific client"""
        selected_room = None
        agent_name = None

        try:
            # Initialize agent name
            agent_name = self.initialize_name(client_socket, agent_name)

            with self.lock:
                # Get or create a room
                selected_room = self.get_available_room(self.nb_players)
                # logger.debug(f"Selected room {selected_room.id} for {agent_name}")
                selected_room.clients[client_socket] = agent_name
                logger.info(f"Agent {agent_name} joined room {selected_room.id}")

                # Send join success response immediately
                response = {
                    "type": "join_success",
                    "data": {
                        "room_id": selected_room.id,
                        "current_players": len(selected_room.clients),
                        "max_players": selected_room.nb_players
                    }
                }
                client_socket.sendall((json.dumps(response) + "\n").encode())
                logger.debug(f"Sent join success response to {agent_name}")

                # Send initial game state immediately
                logger.debug(f"Sending initial game state to {agent_name}")
                game_status = {
                    "type": "waiting_room",
                    "data": {
                        "room_id": selected_room.id,
                        "players": list(selected_room.clients.values()),
                        "nb_players": selected_room.nb_players,
                        "game_started": selected_room.game_thread is not None
                    }
                }
                client_socket.sendall((json.dumps(game_status) + "\n").encode())

                

                # If room is now full, start the game automatically
                if selected_room.is_full():
                    selected_room.start_game()

                # Send confirmation to the client
                response = {"status": "ok", "message": f"Connected to room {selected_room.id}"}
                client_socket.sendall((json.dumps(response) + "\n").encode())


            # Listen for messages from the client
            buffer = ""
            while selected_room.running:
                try:
                    data = client_socket.recv(1024).decode()
                    if not data:
                        break

                    buffer += data
                    messages = buffer.split("\n")
                    buffer = messages[-1]

                    for i in range(len(messages) - 1):
                        try:
                            message = json.loads(messages[i])
                            self.handle_client_message(client_socket, message, selected_room)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON received: {messages[i]}")
                except Exception as e:
                    logger.error(f"Error receiving message from client: {e}")
                    break

        except Exception as e:
            logger.error(f"Error in handle_client: {e}")
        finally:
            # Cleanup when client disconnects
            if selected_room and client_socket in selected_room.clients:
                agent_name = selected_room.clients[client_socket]
                del selected_room.clients[client_socket]
                logger.info(f"Agent {agent_name} disconnected from room {selected_room.id}")

                # Remove the train
                if agent_name in selected_room.game.trains:
                    selected_room.game.remove_train(agent_name)

                # If the room is empty, remove it from the server
                if not selected_room.clients:
                    logger.info(f"Room {selected_room.id} is now empty, removing it")
                    self.remove_room(selected_room.id)

        # Close the client socket
        try:
            client_socket.close()
        except:
            pass

    def handle_client_message(self, client_socket, message, room):
        """Handles messages received from the client"""
        try:
            agent_name = room.clients.get(client_socket)

            # logger.debug(f"Received message from {agent_name}: {message}")

            if message.get("action") == "check_name":
                # Check if the name is available
                name_to_check = message.get("agent_name", "")
                if not name_to_check:
                    # Empty name, considered as not available
                    response = {
                        "type": "name_check",
                        "available": False
                    }
                    logger.debug(f"Empty name check, sending response: {response}")
                    try:
                        client_socket.sendall((json.dumps(response) + "\n").encode())
                        logger.debug("Response sent successfully")
                    except Exception as e:
                        logger.error(f"Error sending name check response: {e}")
                    return

                # Check if the name is already used only in this room (not all rooms)
                name_available = True
                if name_to_check in room.clients.values():
                    name_available = False
                    logger.debug(f"Name '{name_to_check}' found in room {room.id}")
                else:
                    logger.debug(f"Name '{name_to_check}' is available in room {room.id}")

                # Send the response to the client
                response = {
                    "type": "name_check",
                    "available": name_available
                }
                logger.debug(f"Sending name check response: {response}")
                try:
                    client_socket.sendall((json.dumps(response) + "\n").encode())
                    logger.info(f"Name check for '{name_to_check}': {'available' if name_available else 'not available'}")
                except Exception as e:
                    logger.error(f"Error sending name check response: {e}")
                return

            if message.get("action") == "respawn":
                # logger.debug(f"Received respawn request from {agent_name}")
                # Si le thread du jeu n'est pas actif ou si le train est vivant on ne peut pas respawn
                if not room.game_thread or not room.game_thread.is_alive() or room.game.is_train_alive(agent_name):
                    # logger.debug(f"Game thread not active, cannot respawn {agent_name}")
                    return

                cooldown = room.game.get_train_cooldown(agent_name)

                if cooldown > 0:
                    # Inform the client of the remaining cooldown
                    response = {"type": "death", "remaining": cooldown}
                    client_socket.sendall((json.dumps(response) + "\n").encode())
                else:
                    # Clear the cooldown if present
                    # room.game.clear_cooldown(agent_name)

                    # Try to spawn the train
                    if room.game.add_train(agent_name):
                        # logger.info(f"Train {agent_name} spawned")
                        # Send a confirmation to the client
                        response = {"type": "spawn_success", "agent_name": agent_name}
                        client_socket.sendall((json.dumps(response) + "\n").encode())
                    else:
                        logger.warning(f"Failed to spawn train {agent_name}")
                        # Inform the client of the failure
                        response = {"type": "respawn_failed", "message": "Failed to spawn train"}
                        client_socket.sendall((json.dumps(response) + "\n").encode())

            elif message.get("action") == "direction":
                if agent_name in room.game.trains and room.game.is_train_alive(agent_name):
                    room.game.trains[agent_name].change_direction(message["direction"])

            elif message.get("action") == "drop_passenger":
                if agent_name in room.game.trains and room.game.is_train_alive(agent_name):
                    last_wagon_position = room.game.trains[agent_name].drop_passenger()
                    if last_wagon_position:
                        # Create a new passenger at the position of the dropped wagon
                        new_passenger = Passenger(room.game)
                        new_passenger.position = last_wagon_position
                        new_passenger.value = 1
                        room.game.passengers.append(new_passenger)
                        room.game._dirty["passengers"] = True

                        # Send a confirmation to the client
                        response = {"type": "drop_passenger_success", "agent_name": agent_name, "position": last_wagon_position}
                        client_socket.sendall((json.dumps(response) + "\n").encode())
                    else:
                        response = {"type": "drop_passenger_failed", "message": "Failed to drop wagon"}
                        client_socket.sendall((json.dumps(response) + "\n").encode())

            elif message.get("action") == "start_game":
                # logger.info(f"Received start game request from {agent_name}")
                # Check if the game is already started
                if not room.game_thread or not room.game_thread.is_alive():
                    # If the game is not yet started and there are enough players, start it
                    if room.get_player_count() >= self.nb_players:  # Require at least 2 players
                        logger.info(f"Starting game as number of players: {room.get_player_count()} and number of players: {self.nb_players}")
                        room.start_game()
                        logger.info(f"Game started by {agent_name}")
                    else:
                        return
        except Exception as e:
            logger.error(f"Error handling client message: {e}")

    def send_cooldown_notification(self, agent_name, cooldown):
        """Send a cooldown notification to a specific client"""
        for room in self.rooms.values():
            for client_socket, name in room.clients.items():
                if name == agent_name:
                    try:
                        response = {"type": "death", "remaining": cooldown}
                        client_socket.sendall((json.dumps(response) + "\n").encode())
                        # logger.debug(f"Sent cooldown notification to {agent_name}: {cooldown}s")
                        return  # Once we have found and notified the client, we can exit
                    except Exception as e:
                        logger.error(f"Error sending cooldown notification to {agent_name}: {e}")
                        return

    def remove_room(self, room_id):
        """Remove a room from the server"""
        with self.lock:
            if room_id in self.rooms:
                room = self.rooms[room_id]
                # Stop all running threads
                room.running = False
                if room.game_thread and room.game_thread.is_alive():
                    # Just mark the game as not running, the thread will exit by itself
                    room.game.running = False
                
                # Remove the room from the dictionary
                del self.rooms[room_id]
                logger.info(f"Room {room_id} has been removed")

    def run_game(self):
        last_update = time.time()

        while self.running:
            current_time = time.time()
            elapsed = current_time - last_update

            # Broadcast to all rooms
            if elapsed >= 1.0 / MAX_FREQUENCY:
                last_update = current_time

            time.sleep(1 / MAX_FREQUENCY)


if __name__ == "__main__":
    server = Server()
    # Main server loop
    server.run_game()
