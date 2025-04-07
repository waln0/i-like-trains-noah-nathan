from enum import Enum
from pydantic import BaseModel


class ControlMode(Enum):
    MANUAL = "manual"
    AGENT = "agent"


class GameMode(Enum):
    COMPETITIVE = "competitive"
    LOCAL_EVALUATION = "local_evaluation"


class ClientConfig(BaseModel):
    # Host we want to connect to. Use 127.0.0.1 if you want to connect to a local server.
    host: str = "127.0.0.1"

    # Port server is listening on.
    port: int = 5555

    # Size of game window in pixels
    screen_width: int = 500
    screen_height: int = 360

    # Size of leaderboard in pixels
    leaderboard_width: int = 280

    # When your train hits another train or the edge of the game, it dies.
    # It then automatically respawns after a period of time, unless manual_spawn
    # is set to True, in which case you have to hit "SPACE" to respawn.
    manual_spawn: bool = False

    # When control_mode is set to MANUAL, you control the train using the arrow keys + 'd'
    # to drop wagons.
    # When control_mode is set to AGENT, the agent code is called.
    control_mode: ControlMode = ControlMode.MANUAL

    # How long to wait before considering a server as disconnected.
    server_timeout_seconds: float = 2.0

    # Game mode
    game_mode: GameMode = GameMode.COMPETITIVE

    # Competitive agent configuration, change the sciper to yours, and the nickname to
    # your "nickname". Modify the agent_file_name to the agent file name you want to use
    # from the "agents" folder. 
    competitive_agent: dict[str, str] = {
        "sciper": "000000",
        "nickname": "Player",
        "agent_file_name": "agent.py"
    }