from pydantic import BaseModel
from common.client_config import GameMode

class ServerConfig(BaseModel):
    # Host should either be 127.0.0.1 if you only want to accept local connections
    # or 0.0.0.0 if you want to accept local and remote connections.
    host: str = "0.0.0.0"

    # Port on which to listen.
    port: int = 5555

    # Numbers of trains in each room.
    nb_clients_per_room: int = 2

    # If True, allows multiple connections from the same IP address.
    allow_multiple_connections: bool = True

    # When a train hits another train or the game edge, it dies. This controls
    # how much time the user must wait before they can respawn a new train.
    respawn_cooldown_seconds: float = 5.0

    # How long to wait before considering a client as disconnected.
    client_timeout_seconds: float = 2.0

    # Controls the game speed (in frames per second). A lower speed could be
    # useful for debugging purpose.
    tick_rate: int = 60

    # Duration of each game.
    game_duration_seconds: int = 300  # 300 seconds == 5 minutes

    # Amount of time clients will waiting for other clients to join before the
    # game is started with bots replacing any missing clients.
    waiting_time_before_bots_seconds: int = 30

    # Path to the file where player scores are saved.
    high_score_filename : str = "player_scores.json"

    # Maximum number of passengers on a given square.
    max_passengers: int = 3

    # Controls how quickly passenger delivery happens. Depending on this value,
    # the size of the delivery zone, and the number of passengers, a train might
    # have to circle around to complete delivery of all their passengers.
    delivery_cooldown_seconds: float = 0.1

    # Path to an agent file. Change this path to point to one of your agents
    # to use when creating bots (when game_mode is "competitive" and a client 
    # disconnects).
    ai_agent_file_name: str = "ai_agent.py"

    # Local agents configuration, add or remove agents you want to evaluate as needed
    local_agents: list[dict[str, str]] = [
        {
            "nickname": "Agent1",
            "agent_file_name": "agent1.py"
        },
        {
            "nickname": "Agent2",
            "agent_file_name": "agent2.py"
        }
    ]

    # Game mode, "competitive" or "local_evaluation"
    game_mode: GameMode = GameMode.COMPETITIVE
