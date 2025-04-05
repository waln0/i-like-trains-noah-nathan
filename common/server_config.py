from pydantic import BaseModel


class ServerConfig(BaseModel):
    # Host should either be 127.0.0.1 if you only want to accept local connections
    # or 0.0.0.0 if you want to accept local and remote connections
    host: str = "0.0.0.0"

    # Port on which to listen
    port: int = 5555

    # Numbers of trains in each room
    players_per_room: int = 2

    # If True, allows multiple connections from the same IP address
    allow_multiple_connections: bool = True

    # When a train hits another train or the game edge, it dies. This controls
    # how much time the user must wait before they can respawn a new train.
    respawn_cooldown_seconds: int = 5
