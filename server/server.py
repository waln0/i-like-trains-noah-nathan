import socket
import json
import threading
import time
import sys
import logging
import uuid
import os
import signal
import random

from passenger import Passenger
from room import Room, load_best_scores


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
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", 5555))
DEFAULT_NB_PLAYERS_PER_ROOM: int = int(os.getenv("NB_PLAYERS_PER_ROOM", "2"))
ALLOW_MULTIPLE_CONNECTIONS: bool = bool(os.getenv("ALLOW_MULTIPLE_CONNECTIONS", "True"))

CONFIG_PATH = "config.json"
try:
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
except FileNotFoundError:
    logging.error(f"ERROR: Configuration file {CONFIG_PATH} not found. Exiting.")
    sys.exit(1)
except json.JSONDecodeError:
    logging.error(f"ERROR: Error decoding JSON from {CONFIG_PATH}. Exiting.")
    sys.exit(1)

GAME_MODE = config.get("game_mode", "online")  # Default to online
DEFAULT_PORT = config.get("default_port", 5555)
ONLINE_AGENT_CONFIG = config.get("online_agent", {})
LOCAL_AGENTS_CONFIG = config.get("local_agents", [])
DEFAULT_NB_PLAYERS_PER_ROOM = config.get("default_nb_players_per_room", 2)
ALLOW_MULTIPLE_CONNECTIONS = config.get("allow_multiple_connections", True)
WAITING_TIME_BEFORE_BOTS = config.get("waiting_time_before_bots", 20)

# Default host determination based on game mode
if GAME_MODE == "local_evaluation":
    HOST: str = "localhost"
    DEFAULT_NB_PLAYERS_PER_ROOM = 1
    logging.info(
        f"Game mode: local_evaluation. Host: {HOST}, Room Size: {DEFAULT_NB_PLAYERS_PER_ROOM}"
    )
else:  # online mode
    HOST: str = "0.0.0.0"
    logging.info(
        f"Game mode: online. Host: {HOST}, Default Room Size: {DEFAULT_NB_PLAYERS_PER_ROOM}"
    )

PORT: int = int(os.getenv("PORT", DEFAULT_PORT))


# Client timeout in seconds (how long to wait before considering a client disconnected)
CLIENT_TIMEOUT = 2.0

# --- Command Line Argument Overrides (Optional) ---
# Check if an IP address has been supplied in argument
if len(sys.argv) > 1:
    HOST = sys.argv[1]
    logging.warning(f"Overriding host with command line argument: {HOST}")

# Check if port is provided as second argument
if len(sys.argv) > 2:
    try:
        PORT = int(sys.argv[2])
        logging.warning(f"Overriding port with command line argument: {PORT}")
    except ValueError:
        logging.error(
            f"Invalid port value from command line: {sys.argv[2]}. Using default: {PORT}"
        )

# Check if max players per room is provided as third argument (Only relevant for online mode)
if GAME_MODE == "online" and len(sys.argv) > 3:
    try:
        DEFAULT_NB_PLAYERS_PER_ROOM = int(sys.argv[3])
        logging.warning(
            f"Overriding default players per room with command line argument: {DEFAULT_NB_PLAYERS_PER_ROOM}"
        )
    except ValueError:
        logging.error(
            f"Invalid number of players value from command line: {sys.argv[3]}. Using default: {DEFAULT_NB_PLAYERS_PER_ROOM}"
        )

if len(sys.argv) > 4:
    try:
        ALLOW_MULTIPLE_CONNECTIONS = bool(int(sys.argv[4]))
        logging.warning(
            f"Overriding multiple connections with command line argument: {ALLOW_MULTIPLE_CONNECTIONS}"
        )
    except ValueError:
        logging.error(
            f"Invalid multiple connections value from command line: {sys.argv[4]}. Using default: {ALLOW_MULTIPLE_CONNECTIONS}"
        )

# -------------------------------------------------


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
    modules = [
        "server.roomserver.game",
        "server.train",
        "server.passenger",
        "server.delivery_zone",
        "server.ai_client",
        "server.ai_agent",
    ]
    for module in modules:
        logger = logging.getLogger(module)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        logger.addHandler(console_handler)

    return server_logger


# Configure the server logger
logger = setup_server_logger()
logger.info(f"The server starts on {HOST} on port {PORT}")


def display_high_scores(scores, limit=10):
    """Display the current high scores"""
    if not scores:
        logger.info("No high scores available yet")
        return

    # Sort scores in descending order
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    logger.info("===== HIGH SCORES =====")
    for i, (player, score) in enumerate(sorted_scores[:limit], 1):
        logger.info(f"{i}. {player}: {score}")
    logger.info("======================")


class Server:
    def __init__(self):
        self.game_mode = GAME_MODE
        logger.debug(f"Initializing server in {self.game_mode} mode.")
        self.rooms = {}  # {room_id: Room}
        self.lock = threading.Lock()

        # Load player scores from file
        self.best_scores = load_best_scores()

        # Display high scores
        display_high_scores(self.best_scores)

        # Create UDP socket with proper error handling
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((HOST, PORT))
            logger.info(f"UDP socket created and bound to {HOST}:{PORT}")
        except Exception as e:
            logger.error(f"Error creating UDP socket: {e}")
            raise

        self.running = True
        self.nb_clients_per_room = (
            DEFAULT_NB_PLAYERS_PER_ROOM if self.game_mode == "online" else 1
        )
        self.addr_to_name = {}  # Maps client addresses to agent names
        self.addr_to_sciper = {}  # Maps client addresses to scipers
        self.sciper_to_addr = {}  # Maps scipers to client addresses
        self.client_last_activity = {}  # Maps client addresses to last activity timestamp
        self.disconnected_clients = (
            set()
        )  # Track disconnected clients by full address tuple (IP, port)
        self.threads = []  # Initialize threads attribute

        # Client activity tracking for disconnection detection
        self.client_timeout = CLIENT_TIMEOUT

        # Ping tracking for active connection checking
        self.ping_interval = self.client_timeout / 2
        self.ping_responses = {}  # Track which clients have responded to pings

        # Start the ping thread (handles all client timeouts)
        self.ping_thread = threading.Thread(target=self.ping_clients)
        self.ping_thread.daemon = True
        self.ping_thread.start()

        # Create the first room
        self.create_room(True)

        # Start accepting clients
        accept_thread = threading.Thread(target=self.accept_clients, daemon=True)
        accept_thread.start()
        logger.info(f"Server started on {HOST}:{PORT}")

    def create_room(self, running):
        """Create a new room with specified number of clients"""
        room_id = str(uuid.uuid4())[:8]

        new_room = Room(
            room_id,
            self.nb_clients_per_room,
            running,
            self.game_mode,
            LOCAL_AGENTS_CONFIG,
            self.send_cooldown_notification,
            self.get_best_scores,
            self.addr_to_sciper,
            self.remove_room,
            self.server_socket,
            WAITING_TIME_BEFORE_BOTS,
        )
        logger.info(f"Created new room {room_id} with {self.nb_clients_per_room} clients")
        self.rooms[room_id] = new_room
        return new_room

    def get_available_room(self, nb_clients):
        """Get an available room or create a new one if needed"""
        # First try to find a non-full room
        for room in self.rooms.values():
            if (
                room.nb_clients_max == nb_clients
                and not room.is_full()
                and not room.game_thread
            ):
                return room
        logger.debug(f"No suitable room found for {nb_clients} clients")
        # If no suitable room found, create a new one
        return self.create_room(True)

    def accept_clients(self):
        """Thread that waits for new connections"""
        logger.info("Server is listening for UDP packets")
        error_count = {}  # Track error count per client

        while self.running:
            # TODO RESTORE
            try:
                # Receive data from any client
                data, addr = self.server_socket.recvfrom(1024)

                # If we successfully received data from this client, reset their error count
                if addr in error_count:
                    error_count[addr] = 0

                if not data:
                    continue

                data_str = data.decode()

                # Process the incoming message
                if data_str:
                    # Handle multiple messages in one packet
                    messages = data_str.split("\n")
                    for message_str in messages:
                        if not message_str:
                            continue

                        # try: // TODO RESTORE
                        message = json.loads(message_str)
                        # Process the message
                        self.process_message(message, addr)
                        # except json.JSONDecodeError:
                        #     logger.warning(
                        #         f"Invalid JSON received from {addr}: {message_str}"
                        #     )
                        # except Exception as e:
                        #     logger.error(f"Error processing message from {addr}: {e}")
            except socket.error as e:
                # For UDP, we don't know which client caused the error
                # So we only log the error and don't mark any client as disconnected
                if "10054" in str(e):
                    # This is a connection reset error, which is expected in UDP
                    # We'll just log it at a lower level or not at all
                    pass  # Don't log connection reset errors at all
                else:
                    logger.error(f"Socket error: {e}")
                # Add a small delay to avoid high CPU usage on error
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in accept_clients: {e}")
                # Add a small delay to avoid high CPU usage on error
                time.sleep(0.1)

    def find_client_room(self, agent_sciper):
        for room in self.rooms.values():
            for addr in room.clients:
                if addr in self.addr_to_sciper and self.addr_to_sciper[addr] == agent_sciper:
                    return room
        return None

    def process_message(self, message, addr):
        """Process incoming messages from clients"""
        if addr in self.disconnected_clients:
            # Remove the client from the disconnected clients list
            self.disconnected_clients.remove(addr)

        # Check if we need to handle agent initialization
        if self.game_mode == "online":
            if (
                "type" in message
                and message["type"] == "agent_ids"
                and "agent_name" in message
                and "agent_sciper" in message
            and addr not in self.addr_to_name
            ):
                # use handle_name_check and handle_sciper_check to check if the name and sciper are available
                logger.debug(
                    f"Checking name and sciper availability for {message['agent_name']} ({message['agent_sciper']})"
                )
                if self.handle_name_check(message, None) and self.handle_sciper_check(
                    message, None
                ):
                    self.handle_new_client(message, addr)
                else:
                    # ask the client to disconnect
                    self.send_disconnect(addr, "Name or sciper not available or invalid")
                    logger.warning(f"Name or sciper not available or invalid for {addr}")

        # In local_evaluation mode, the only client connecting is the observer, handle it directly
        elif self.game_mode == "local_evaluation":
            self.client_last_activity[addr] = time.time()
            # Assuming the first message in local_evaluation is implicitly a connection request
            # We might need a specific message type later if this assumption is wrong
            if addr not in self.addr_to_sciper:  # Only handle if it's a new client address
                self.handle_new_client(message, addr)

        # Handle ping responses for everyone
        if "type" in message and message["type"] == "pong":
            self.client_last_activity[addr] = time.time()
            # Client has responded to a ping, update the ping responses dictionary
            if addr in self.ping_responses:
                del self.ping_responses[addr]  # Remove from pending responses
            return

        # Handle ping messages from unknown clients (for connection verification)
        if "type" in message and message["type"] == "ping":
            # Send a pong response even to unknown clients for connection verification
            pong_message = {"type": "pong"}
            try:
                self.server_socket.sendto((json.dumps(pong_message) + "\n\n").encode(), addr)
                return
            except Exception as e:
                logger.error(f"Error sending pong to {addr}: {e}")
                return

        agent_sciper = self.addr_to_sciper.get(addr)

        if agent_sciper:
            # Find which room this client belongs to
            client_room = self.find_client_room(agent_sciper)
            if client_room:
                self.handle_client_message(addr, message, client_room)
            else:
                logger.warning(
                    f"Received message from {addr} ({agent_sciper}) but client not in any room. Message: {message}"
                )
        else:
                # This is an unknown client sending a message that's not a common type
                logger.debug(f"Received message from unknown client {addr}: {message}")
                # Send a disconnect request to the client
                self.send_disconnect(addr, "Unknown client")
                logger.info(f"Sent disconnect request to unknown client {addr}")

    def send_disconnect(self, addr, message="Unknown client or invalid message format"):
        """Disconnect a client from the server"""
        # ask the client to disconnect
        disconnect_message = {
            "type": "disconnect",
            "reason": message,
        }
        try:
            self.server_socket.sendto(
                (json.dumps(disconnect_message) + "\n").encode(), addr
            )
            logger.info(f"Sent disconnect request to unknown client {addr}")
        except Exception as e:
            logger.error(f"Error sending disconnect request to {addr}: {e}")

    def handle_high_scores_request(self, addr):
        """Handle a request for high scores"""
        # Sort scores in descending order
        sorted_scores = sorted(
            self.best_scores.items(), key=lambda x: x[1], reverse=True
        )
        top_scores = sorted_scores[:10]  # Get top 10 scores

        # Create response
        response = {
            "type": "high_scores",
            "scores": [
                {"name": player, "score": score} for player, score in top_scores
            ],
        }

        try:
            self.server_socket.sendto((json.dumps(response) + "\n").encode(), addr)
            logger.info(f"Sent high scores to client at {addr}")
        except Exception as e:
            logger.error(f"Error sending high scores: {e}")

    def get_best_scores(self, limit=10):
        """Get the top scores from the scores file"""
        sorted_scores = sorted(
            self.best_scores.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_scores[:limit]

    def handle_name_check(self, message, addr):
        """Handle name check requests"""

        name_to_check = message.get("agent_name", "")
        if addr:
            if not name_to_check or len(name_to_check) == 0:
                # Empty name, considered as not available
                response = {"type": "name_check", "available": False}

                try:
                    self.server_socket.sendto(
                        (json.dumps(response) + "\n").encode(), addr
                    )
                except Exception as e:
                    logger.error(f"Error sending name check response: {e}")
                return False

        # Check if the name exists in any room
        name_available = True
        room = None  # Initialize room to None to avoid reference error
        
        for room_id, current_room in self.rooms.items():
            room = current_room  # Keep a reference to the last room
            for client_addr, client_name in current_room.clients.items():
                if client_name == name_to_check:
                    # Check if the client with this name is in disconnected_clients
                    if client_addr in self.disconnected_clients:
                        # Client is disconnected, name can be reused
                        logger.debug(f"Name '{name_to_check}' found in room {room_id} but client is disconnected, considering it available")
                        continue
                    # Client is connected, name is not available
                    name_available = False
                    logger.debug(f"Name '{name_to_check}' found in room {room_id}")
                    break
            if not name_available:
                break

        # Check if name not in the ai names (only if we have at least one room)
        if room and name_available and name_to_check in room.AI_NAMES:
            name_available = False

        # Check if name starts with "Bot " (invalid)
        if name_available and name_to_check.startswith("Bot "):
            name_available = False
            logger.debug(f"Name '{name_to_check}' starts with 'Bot ', not available")

        if addr:
            # Prepare the response with best score if available
            response = {"type": "name_check", "available": name_available}

            try:
                self.server_socket.sendto((json.dumps(response) + "\n").encode(), addr)
            except Exception as e:
                logger.error(f"Error sending name check response: {e}")

        return name_available

    def handle_sciper_check(self, message, addr):
        """Handle sciper check requests"""
        # Update client activity timestamp
        # self.client_last_activity[addr] = time.time()
        logger.debug(f"Checking sciper availability for {message['agent_sciper']}")

        sciper_to_check = message.get("agent_sciper", "")

        # Check if the sciper is empty or not an int
        if (
            not sciper_to_check
            or len(sciper_to_check) != 6
            or not sciper_to_check.isdigit()
        ):
            if addr:
                # Empty sciper, considered as not available
                response = {"type": "sciper_check", "available": False}
                try:
                    self.server_socket.sendto(
                        (json.dumps(response) + "\n").encode(), addr
                    )
                except Exception as e:
                    logger.error(f"Error sending sciper check response: {e}")
                return False
            else:
                return False

        # Check if the sciper exists in our mapping
        sciper_available = sciper_to_check not in self.sciper_to_addr
        
        # If sciper is not available, check if the associated address is in disconnected_clients
        if not sciper_available and sciper_to_check in self.sciper_to_addr:
            old_addr = self.sciper_to_addr[sciper_to_check]
            if old_addr in self.disconnected_clients:
                # If the address is in disconnected_clients, consider the sciper as available
                sciper_available = True
                logger.info(f"Sciper {sciper_to_check} found but associated address {old_addr} is disconnected, considering it available")

        if addr:
            # Prepare the response with best score if available
            response = {"type": "sciper_check", "available": sciper_available}

            # Include best score if the player has played before
            if sciper_to_check in self.best_scores:
                response["best_score"] = self.best_scores[sciper_to_check]
                logger.info(
                    f"Player with sciper '{sciper_to_check}' has a best score of {self.best_scores[sciper_to_check]}"
                )

            try:
                self.server_socket.sendto((json.dumps(response) + "\n").encode(), addr)
                logger.info(
                    f"Sciper check for '{sciper_to_check}': {'available' if sciper_available else 'not available'}"
                )
            except Exception as e:
                logger.error(f"Error sending sciper check response: {e}")

        return sciper_available

    def handle_new_client(self, message, addr):
        """Handle new client connection"""

        agent_name = message.get("agent_name", "")
        agent_sciper = message.get("agent_sciper", "")

        if self.game_mode == "local_evaluation":
            logger.info(f"New client connected in local_evaluation mode: {addr}")
            self.client_last_activity[addr] = time.time()

            # generate a random name and sciper
            agent_name = f"Observer_{random.randint(1000, 9999)}"
            agent_sciper = str(random.randint(100000, 999999))

        elif self.game_mode == "online":
            if not agent_name:
                logger.warning("No agent name provided")
                return

            if not agent_sciper:
                logger.warning("No agent sciper provided")
                return
            
            logger.info(f"\nNew client {agent_name} (sciper: {agent_sciper}) connecting from {addr}")

            # Initialize client activity tracking
            self.client_last_activity[addr] = time.time()

            # Log new client connection
            logger.info(
                f"New client {agent_name} (sciper: {agent_sciper}) connecting from {addr}"
            )

        # Check if this sciper was previously connected and clean up any old references
        if agent_sciper in self.sciper_to_addr:
            old_addr = self.sciper_to_addr[agent_sciper]
            if old_addr != addr:  # Only if it's a different address
                logger.info(f"Cleaning up previous connection for sciper {agent_sciper} at {old_addr}")
                # Remove from disconnected_clients if present
                if old_addr in self.disconnected_clients:
                    self.disconnected_clients.remove(old_addr)
                # Clean up other mappings
                if old_addr in self.addr_to_name:
                    del self.addr_to_name[old_addr]
                if old_addr in self.addr_to_sciper:
                    del self.addr_to_sciper[old_addr]
                if old_addr in self.client_last_activity:
                    del self.client_last_activity[old_addr]
                if old_addr in self.ping_responses:
                    del self.ping_responses[old_addr]

        # Associate address with name and sciper
        self.addr_to_name[addr] = agent_name
        self.addr_to_sciper[addr] = agent_sciper
        self.sciper_to_addr[agent_sciper] = addr

        # Remove from disconnected_clients if present (just in case)
        if addr in self.disconnected_clients:
            self.disconnected_clients.remove(addr)

        # Assign to a room
        selected_room = self.get_available_room(self.nb_clients_per_room)
        selected_room.clients[addr] = agent_name

        # Mark the room as having at least one human player
        selected_room.has_clients = True

        # Record the time the first client joined this room
        if selected_room.first_client_join_time is None:
            selected_room.first_client_join_time = time.time()

        logger.info(
            f"Agent {agent_name} (sciper: {agent_sciper}) joined room {selected_room.id}"
        )

        # Send join success response immediately
        response = {
            "type": "join_success",
            "data": {
                "room_id": selected_room.id,
                "current_players": len(selected_room.clients),
                "max_players": selected_room.nb_clients_max,
            },
        }
        self.server_socket.sendto((json.dumps(response) + "\n").encode(), addr)

        if self.game_mode == "online":
            # Send initial game state immediately
            game_status = {
                "type": "waiting_room",
                "data": {
                    "room_id": selected_room.id,
                    "players": list(selected_room.clients.values()),
                    "nb_players": selected_room.nb_clients_max,
                    "game_started": selected_room.game_thread is not None,
                    "waiting_time": int(
                        max(
                            0,
                            WAITING_TIME_BEFORE_BOTS
                            - (time.time() - selected_room.room_creation_time),
                        )
                    )
                    if selected_room.has_clients
                    else 0,
                },
            }
            self.server_socket.sendto((json.dumps(game_status) + "\n").encode(), addr)

        # If room is now full, start the game automatically
        # if selected_room.is_full():
            # if not room.game_thread or not room.game_thread.is_alive():
            #     if (
            #         room.get_player_count() >= self.nb_clients
            #     ):
            #         logger.info(
            #             f"Starting game as number of players: {room.get_player_count()} and number of players: {self.nb_clients}"
            #         )
            #         room.start_game()
                    # logger.info(f"Game started by {agent_name}")
            #     else:
            #         return
            # selected_room.complete_with_bots()
            # selected_room.start_game()

    def handle_client_message(self, addr, message, room):
        """Handles messages received from the client"""
        try:
            # Update client activity timestamp

            agent_name = room.clients.get(addr)
            if message.get("action") == "check_name":
                self.handle_name_check(message, addr)
                return

            if message.get("action") == "check_sciper":
                self.handle_sciper_check(message, addr)
                return

            self.client_last_activity[addr] = time.time()

            if message.get("action") == "respawn":
                # Check if the game is over
                if room.game_over:
                    logger.info(
                        f"Ignoring respawn request from {agent_name} as the game is over"
                    )
                    response = {"type": "respawn_failed", "message": "Game is over"}
                    self.server_socket.sendto(
                        (json.dumps(response) + "\n").encode(), addr
                    )
                    return

                cooldown = room.game.get_train_cooldown(agent_name)

                if cooldown > 0:
                    # Inform the client of the remaining cooldown
                    response = {"type": "death", "remaining": cooldown}
                    self.server_socket.sendto(
                        (json.dumps(response) + "\n").encode(), addr
                    )
                    return

                # Add the train to the game
                if room.game.add_train(agent_name):
                    response = {"type": "spawn_success", "agent_name": agent_name}
                    self.server_socket.sendto(
                        (json.dumps(response) + "\n").encode(), addr
                    )
                else:
                    logger.warning(f"Failed to spawn train {agent_name}")
                    # Inform the client of the failure
                    response = {
                        "type": "respawn_failed",
                        "message": "Failed to spawn train",
                    }
                    self.server_socket.sendto(
                        (json.dumps(response) + "\n").encode(), addr
                    )

            elif message.get("action") == "direction":
                if agent_name in room.game.trains and room.game.is_train_alive(
                    agent_name
                ):
                    room.game.trains[agent_name].change_direction(message["direction"])
                # else:
                #     logger.warning(f"Failed to change direction for train {agent_name}")

            elif message.get("action") == "drop_wagon":
                if agent_name in room.game.trains and room.game.is_train_alive(
                    agent_name
                ):
                    last_wagon_position = room.game.trains[agent_name].drop_wagon()
                    if last_wagon_position:
                        # Create a new passenger at the position of the dropped wagon
                        new_passenger = Passenger(room.game)
                        new_passenger.position = last_wagon_position
                        new_passenger.value = 1
                        room.game.passengers.append(new_passenger)
                        room.game._dirty["passengers"] = True

                        # Send a confirmation to the client
                        response = {
                            "type": "drop_wagon_success",
                            "agent_name": agent_name,
                            "position": last_wagon_position,
                        }
                        self.server_socket.sendto(
                            (json.dumps(response) + "\n").encode(), addr
                        )
                    else:
                        response = {
                            "type": "drop_wagon_failed",
                            "message": "Failed to drop wagon",
                        }
                        self.server_socket.sendto(
                            (json.dumps(response) + "\n").encode(), addr
                        )
            
            # For high scores request
            if "type" in message and message["type"] == "high_scores":
                self.handle_high_scores_request(addr)
                return

        except Exception as e:
            logger.error(f"Error handling client message: {e}")

    def send_cooldown_notification(self, agent_name, cooldown):
        """Send a cooldown notification to a specific client"""
        for room in self.rooms.values():
            for addr, name in room.clients.items():
                if name == agent_name:
                    try:
                        # Skip AI clients - they don't need network messages
                        if (
                            isinstance(addr, tuple)
                            and len(addr) == 2
                            and addr[0] == "AI"
                        ):
                            return

                        response = {"type": "death", "remaining": cooldown}
                        self.server_socket.sendto(
                            (json.dumps(response) + "\n").encode(), addr
                        )
                        return
                    except Exception as e:
                        logger.error(
                            f"Error sending cooldown notification to {agent_name}: {e}"
                        )
                        return

    def ping_clients(self):
        """Thread that sends ping messages to all clients and checks for timeouts"""
        while self.running:
            try:
                current_time = time.time()

                # PART 1: Check all clients for timeouts
                for addr, last_activity in list(self.client_last_activity.items()):
                    # Skip clients that are already marked as disconnected
                    if addr in self.disconnected_clients:
                        continue

                    # Check if client has timed out
                    if current_time - last_activity > self.client_timeout:
                        # Client has timed out, handle disconnection
                        self.handle_client_disconnection(addr, "timeout")

                # PART 2: Send pings to clients in rooms
                clients_to_ping = set()
                for room in self.rooms.values():
                    for addr in room.clients.keys():
                        clients_to_ping.add(addr)

                # Send pings to all active clients in rooms
                for addr in clients_to_ping:
                    # Skip clients that are already marked as disconnected
                    if addr in self.disconnected_clients:
                        continue

                    # Skip AI clients - they don't need network messages
                    if isinstance(addr, tuple) and len(addr) == 2 and addr[0] == "AI":
                        continue

                    # Send a ping message to the client
                    ping_message = {"type": "ping"}
                    try:
                        self.server_socket.sendto(
                            (json.dumps(ping_message) + "\n").encode(), addr
                        )
                        # Add the client to the ping responses dictionary with the current time
                        self.ping_responses[addr] = current_time
                    except Exception as e:
                        logger.debug(f"Error sending ping to client {addr}: {e}")

                # Wait for responses (half the ping interval)
                time.sleep(self.ping_interval / 2)

                # PART 3: Check for clients that haven't responded to pings
                for addr, ping_time in list(self.ping_responses.items()):
                    # If the ping was sent more than ping_interval ago and no response was received
                    if current_time - ping_time > self.ping_interval:
                        # Skip clients that are already marked as disconnected
                        if addr in self.disconnected_clients:
                            del self.ping_responses[addr]
                            continue

                        # Client hasn't responded to ping, mark as disconnected
                        self.handle_client_disconnection(addr, "ping timeout")

                # Sleep for the remaining time of the ping interval
                time.sleep(self.ping_interval / 2)
            except Exception as e:
                logger.error(f"Error in ping_clients: {e}")
                # Sleep on error to avoid high CPU usage
                time.sleep(self.ping_interval)

    def handle_client_disconnection(self, addr, reason="unknown"):
        """Handle client disconnection - centralized method to avoid code duplication"""
        # Check if client is already marked as disconnected
        if addr in self.disconnected_clients:
            # Already disconnected, no need to process again
            return

        # Mark client as disconnected
        self.disconnected_clients.add(addr)

        agent_name = self.addr_to_name.get(addr, "Unknown client")

        # Only log at INFO level if this is a known client
        if agent_name != "Unknown client":
            logger.info(f"Client {agent_name} disconnected due to {reason}: {addr}")

            # Find the room this client is in and create an AI to control their train
            for room in self.rooms.values():
                if addr in room.clients:
                    # Store the name before removing the client
                    original_train_name = room.clients[addr]
                    logger.info(f"Removing {original_train_name} from room {room.id}")

                    # Remove the client from the room's client list first
                    del room.clients[addr]

                    # Now, check if any human clients remain
                    human_clients_count = 0
                    for client_addr_check in room.clients.keys():
                        # Count only human clients (not AI clients)
                        if not (
                            isinstance(client_addr_check, tuple)
                            and len(client_addr_check) == 2
                            and client_addr_check[0] == "AI"
                        ):
                            human_clients_count += 1

                    if human_clients_count == 0:
                        # Last human left, close the room. No need to create AI.
                        logger.info(
                            f"Last human client {original_train_name} left room {room.id}, closing room"
                        )
                        # remove_room handles setting flags, stopping threads, and cleanup
                        self.remove_room(room.id)
                    else:
                        # Other human players remain. Create an AI for the disconnecting player's train if it exists.
                        if original_train_name in room.game.trains:
                            logger.info(
                                f"Creating AI client for train {original_train_name}"
                            )
                            room.create_ai_for_train(original_train_name)
                        # else: Train might not exist or is already AI, log if necessary for debug

                    break  # Exit the room loop as we found and processed the client

        else:
            # Log at debug level for unknown clients to reduce spam
            logger.debug(f"Unknown client disconnected due to {reason}: {addr}")

        # Common cleanup for the disconnected client's address info - moved outside the room loop
        # to ensure it happens even if client is not found in a room
        if addr in self.addr_to_name:
            del self.addr_to_name[addr]
            
        # Clean up sciper information
        if addr in self.addr_to_sciper:
            sciper = self.addr_to_sciper[addr]
            if sciper in self.sciper_to_addr:
                del self.sciper_to_addr[sciper]
            del self.addr_to_sciper[addr]
            
        if addr in self.client_last_activity:
            del self.client_last_activity[addr]
            
        if addr in self.ping_responses:
            del self.ping_responses[addr]

    def remove_room(self, room_id):
        """Remove a room from the server"""
        if room_id in self.rooms:
            logger.info(f"Removing room {room_id}")
            room = self.rooms[room_id]

            # 1. Signal the game to stop (if it exists and is running)
            if room.game and room.game.running:
                logger.debug(f"Signaling game in room {room_id} to stop.")
                room.game.running = False

            # 2. Signal the room's threads to stop
            if room.running:
                logger.debug(f"Signaling room {room_id} threads to stop.")
                room.running = False

            # 3. Wait for the game thread to finish if it's running
            if room.game_thread and room.game_thread.is_alive():
                logger.info(
                    f"Waiting for game thread in room {room_id} to terminate before removal"
                )
                room.game_thread.join(timeout=2.0)  # Wait a bit
                if room.game_thread.is_alive():
                    logger.warning(
                        f"Game thread for room {room_id} did not terminate gracefully."
                    )

            # 4. Stop and clean up AI clients associated with this room
            ai_to_remove = []
            # Use list() to avoid modification during iteration if necessary, although it might not be strictly needed here
            for ai_name, ai_client in list(self.rooms[room_id].ai_clients.items()):
                # Check if ai_client.room exists before accessing id
                if ai_client.room and ai_client.room.id == room_id:
                    logger.debug(f"Stopping AI client {ai_name} in room {room_id}")
                    ai_client.stop()
                    ai_to_remove.append(ai_name)

            for ai_name in ai_to_remove:
                if ai_name in self.rooms[room_id].ai_clients:
                    del self.rooms[room_id].ai_clients[ai_name]
                if ai_name in self.rooms[room_id].used_ai_names:
                    # Use discard to avoid KeyError if name somehow already removed
                    self.rooms[room_id].used_ai_names.discard(ai_name)

            # 5. Now remove the room itself
            del self.rooms[room_id]
            logger.info(f"Room {room_id} removed successfully")
        else:
            logger.warning(f"Attempted to remove non-existent room {room_id}")

    def run(self):
        """Main game loop"""

        def signal_handler(sig, frame):
            # Only set the running flag to false. Cleanup happens after the main loop.
            logger.info("Shutdown signal received. Initiating graceful shutdown...")
            self.running = False
            # Removed direct cleanup and sys.exit from here

        # Register signal handler for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        logger.info("Server running. Press Ctrl+C to stop.")

        while self.running:
            # Main loop waits for running flag to become false
            try:
                # Use a timeout to allow checking self.running more frequently
                # and prevent blocking indefinitely if no other activity occurs.
                time.sleep(0.5)
            except InterruptedError:
                # Catch potential interruption if sleep is interrupted by signal
                continue  # Check self.running again

        # --- Shutdown sequence starts here, after the loop ---
        logger.info("Shutting down server...")

        # 1. Disconnect clients (must happen before closing the socket)
        client_addresses = list(self.addr_to_name.keys())  # Copy keys
        if client_addresses:
            logger.info(f"Disconnecting {len(client_addresses)} clients...")
            for addr in client_addresses:
                # Add try-except around send_disconnect in case socket is already bad
                try:
                    self.send_disconnect(addr, "Server shutting down")
                    # Optional small delay to increase chance of message delivery
                    time.sleep(0.01)
                except Exception as e:
                    logger.error(f"Error sending disconnect to {addr}: {e}")
        else:
            logger.info("No clients connected to disconnect.")

        threads_to_join = []
        if hasattr(self, "threads"):  # Check if attribute exists
            threads_to_join.extend(self.threads)
        if (
            hasattr(self, "ping_thread") and self.ping_thread is not None
        ):  # Check ping_thread exists and is not None
            threads_to_join.append(self.ping_thread)
        # Add other relevant threads if they exist and need joining, e.g., accept_clients thread if stored.

        active_threads = [
            t for t in threads_to_join if t and t.is_alive()
        ]  # Check for None threads too

        if active_threads:
            logger.info(f"Waiting for {len(active_threads)} threads to finish...")
            for thread in active_threads:
                try:
                    thread.join(timeout=1.0)  # Use timeout
                    if thread.is_alive():
                        logger.warning(
                            f"Thread {thread.name} did not finish within timeout."
                        )
                except Exception as e:
                    logger.error(f"Error joining thread {thread.name}: {e}")
        else:
            logger.info("No active threads found to join.")

        logger.info("Server shutdown complete")
        # No sys.exit(0) here, allow the function to return naturally


if __name__ == "__main__":
    server = Server()
    # Main server loop
    server.run()
