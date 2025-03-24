# I Like Trains

![Thumbnail](img/thumbnail_2.png)

## Overview

I Like Trains is a multiplayer game where players take on the role of train operators, navigating a shared game world to collect passengers, strategically expand their trains, and skillfully avoid collisions. Built with Python and Pygame, the game employs a client-server architecture to enable networked gameplay, offering a blend of strategic decision-making and real-time reactions.

The student's objective will be to modify the agent.py file (and only this one) to remotely control a train managed by a server according to his environment.
The agent must make travel decisions for the train, as well as the game board with the Pygam Library.
The student will also have to edit the draw_passengers() and draw_trains() functions in client/renderer to display the passengers and trains.

## Project Structure

The project is divided into two main parts:

### 1. Server (folder `server/`)
The server is responsible for managing client connections and game synchronization. It is executed on a distant machine which the student is connecting to.
The server files are included here so the student can have a better understanding of how the management of the game works. 

- `server.py` : Manages client connections and game synchronization
- `game.py` : Contains the main game logic
- `train.py` : Defines the Train class and its behaviors
- `passenger.py` : Manages passenger logic
- `ai_client.py` : Manages AI clients
- `delivery_zone.py` : Manages delivery zones

### 2. Client (folder `client/`)
The client is responsible for managing the game display and user interactions. It is executed on the student's machine when executing `main.py`.

- `client.py` : Manages server connection and the main game loop
- `network.py` : Manages network communication with the server
- `renderer.py` : Responsible for the graphical display of the game
- `event_handler.py` : Manages events (keyboard, mouse)
- `game_state.py` : Maintains the game state on the client side
- `agent.py` : Controls the player's train behavior
- `ui.py` : Manages the user interface to enter train name and sciper

## Client-Server Communication

Communication between the client and server is done via TCP/IP sockets:
1. The client connects to the distant server (by default on localhost:5555)
2. The client sends its train name and sciper to the server
3. The server regularly sends the game state to clients
4. Clients send their actions (change direction or drop wagon) to the server
5. The server updates the game state and the cycle continues

## Implementation Tasks

As a student, you must implement two main components:

### 1. Intelligent Agent (agent.py)

You must implement an intelligent agent that controls your train. The main method to implement is:

```python
def get_direction(self, game_width, game_height):
    """
    This method is regularly called by the client to get the next direction of the train.
    It must return a valid direction that avoids walls and collisions.
    """
```

The running client regularly calls the agent's `update_agent` method to update the agent's state (information from the server about the game, like the trains positions, the passengers, the delivery zones, etc.). The `update_agent` method then calls the method `get_direction` to dynamicaly get the next direction of the train (determined by the agent according to the game state) and transfer it to the server (`self.network.send_direction_change(direction)`).

You can use such following methods (not mandatory):
- `will_hit_wall()` : To check if the next position will hit a wall
- `will_hit_train_or_wagon()` : To check if the direction leads to a collision
- `get_target_position()` : To take a decision between targetting a passenger or a delivery zone
- `get_direction_to_target()` : To determine the best direction to reach a target

The agent can also call the method `self.network.send_drop_wagon_request()` to send a request to the server to drop a wagon.
The train will then get a 0.25sec *1.5 speed boost and enter a 10sec boost cooldown. Calling this method will drop one wagon from the train (costing 1 point from the train's score).

The class Agent is initialized with the following attributes:

- `self.agent_name` : The name of the agent
- `self.logger` : The logger object
- `self.is_dead` : Whether the agent/train is currently dead or alive
- `self.directions` : A list of possible directions
- `self.death_time` : The time when the agent last died
- `self.respawn_cooldown` : The cooldown time before respawning
- `self.waiting_for_respawn` : Whether the agent is waiting for respawn
- `self.game_width` and `self.game_height` are initialized later by the server but are still accessible in the program. They are the width and height of the game grid.

### 2. Graphical Rendering (renderer.py)

You must implement the display of trains and passengers in the renderer. The two methods to implement are:

```python
def draw_trains(self):
    """
    Draws all trains and their wagons.
    Tip: Use train_data.get("position", (0, 0)) to access a train's position
    """

def draw_passengers(self):
    """
    Draws all passengers on the grid.
    Tip: Use passenger["position"] to access a passenger's position
    """
```


## Implementation Tips

1. For the agent:
   - Display the available information in the logger (trains, passengers, delivery zones, etc.)
   - Start with a simple strategy (e.g., go towards the closest passenger)
   - Gradually add obstacle avoidance (other trains and wagons)
   - Consider handling cases where the direct path is blocked

2. For the renderer:
   - Ensure trains and passengers should be clearly visible
   - Consider the orientation of trains based on their direction
   - Each train has a color by default, consider using dark blue to display yours (not used by default)

### Other tools in client.py

Some constants are available in the client for debugging:

- `MANUAL_SPAWN`: Automatic respawn when available. False by default, otherwise the player has to press the space bar.
- `ACTIVATE_AGENT`: Activate the agent. True by default. If set to False, the agent will not be used.
- `MANUAL_CONTROL`: Activate manual control. False by default, otherwise the player can use the keyboard arrows to control the train.

## Requirements

*   \> Python 3.10

## Setup Instructions

Follow these steps to set up and run the game:

### 1. Create a virtual environment 

After cloning the project and entering the folder with `cd .\i_like_trains\`, enter:

```bash
python -m venv venv
```

### 2. Activate the virtual environment (every time before starting the project)

#### On Windows

```bash
.\venv\Scripts\activate
```

#### On macOS/Linux

```bash
source venv/bin/activate
```

### 3. Install the necessary dependencies

After activating the virtual environment, install the necessary dependencies:

```bash
pip install -r requirements.txt
```

### 4. (Optionnal) Start a local server for testing

The student can start a local server by executing `python server/server.py`. This will start a server on the default port (5555) of his computer.
The student can then open another terminal, go to the project folder, enter the virtual environment, and execute `python main.py` to connect to the local server. This is optional, but recommended for testing before connecting to the distant server.

### 5. Execute the client

To execute the client and connect to the server. Replace `<ip_adress>` with the IP address of the server (do not enter an IP address if you are connecting to the local server hosted on your machine).

```bash
python main.py <ip_adress>
```

## How to Play

1. Launch your client: `python main.py <ip_adress>`
2. Enter your player name and sciper
3. Wait in the waiting room until all players are connected
4. Press SPACE to start the game when all players are ready if it is not automatic
5. Your agent will automatically control your train
6. The goal is to collect as many passengers (your number of wagons will increase) and then deliver them to the delivery zone

## Logging System

The game uses Python's built-in logging system to help with debugging and monitoring. Change the logging level in the `logging.basicConfig` function at the beginning of each file from which you want to follow the logs.

Available log levels (from most to least verbose):

- DEBUG: Detailed information for debugging
- INFO: General information about game operation
- WARNING: Indicates potential issues
- ERROR: Serious problems that need attention
- CRITICAL: Critical errors that prevent the game from running

Logs are displayed in the console and include timestamps, module name, and log level.
