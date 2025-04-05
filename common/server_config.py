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
