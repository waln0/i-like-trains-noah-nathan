# I Like Trains Game

![Thumbnail](img/thumbnail_2.png)

## Overview

I Like Trains Game is a multiplayer game where players take on the role of train operators, navigating a shared game world to collect passengers, strategically expand their trains, and skillfully avoid collisions. Built with Python and Pygame, the game employs a client-server architecture to enable networked gameplay, offering a blend of strategic decision-making and real-time reactions.

The student's objective will be to modify the agent.py file (and only this one) to remotely control a train managed by a server according to his environment.
The agent must make travel decisions for the train, as well as the game board with the Pygam Library.
The student will also have to edit the draw_passengers() and draw_trains() functions in client/renderer to display the passengers and trains.

## Project Structure

The project is divided into two main parts:

### 1. Server (folder `server/`)
- `server.py` : Manages client connections and game synchronization
- `game.py` : Contains the main game logic
- `train.py` : Defines the Train class and its behaviors
- `passenger.py` : Manages passenger logic

### 2. Client (folder `client/`)
- `client.py` : Manages server connection and the main game loop
- `network.py` : Manages network communication with the server
- `renderer.py` : Responsible for the graphical display of the game
- `event_handler.py` : Manages events (keyboard, mouse)
- `game_state.py` : Maintains the game state on the client side
- `agent.py` : Controls the player's train behavior
- `ui.py` : Manages the user interface

## Client-Server Communication

Communication between the client and server is done via TCP/IP sockets:
1. The client connects to the server (by default on localhost:5555)
2. The client sends its agent name to the server
3. The server regularly sends the game state to clients
4. Clients send their actions (directions) to the server
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

Helper functions are available in the Agent class:
- `will_hit_wall()` : Checks if the next position will hit a wall
- `will_hit_train_or_wagon()` : Checks if the direction leads to a collision
- `get_closest_passenger()` : Finds the closest passenger
- `get_direction_to_target()` : Determines the best direction to reach a target

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

## Game Parameters

- Screen size: 600x400 pixel
- Game screen size: 200x200 pixel
- Grid size: 20 pixels
- Possible directions: Up, Right, Down, Left
- Automatic respawn after collision (configurable)
- Scoreboard displayed on the right side of the screen

## Implementation Tips

1. For the agent:
   - Start with a simple strategy (e.g., go towards the closest passenger)
   - Gradually add obstacle avoidance (other trains and wagons)
   - Consider handling cases where the direct path is blocked

2. For the renderer:
   - Ensure trains and passengers are clearly visible
   - Consider the orientation of trains based on their direction
   - Each train has a color by default, consider using dark blue to display yours (not used by default)

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

### 4. Execute the client

To execute the client and connect to the server. Replace `<ip_adress>` with the IP address of the server.

```bash
python main.py <ip_adress>
```

## How to Play

1. Launch the client: `python main.py <ip_adress>`
2. Enter your player name
3. Wait in the waiting room until all players are connected
4. Press SPACE to start the game when all players are ready
5. Your agent will automatically control your train
6. The goal is to collect as many passengers as possible while avoiding collisions

## Logging System

The game uses Python's built-in logging system to help with debugging and monitoring. Change the logging level in the `logging.basicConfig` function at the beginning of each file from which you want to follow the logs.

Available log levels (from most to least verbose):

- DEBUG: Detailed information for debugging
- INFO: General information about game operation
- WARNING: Indicates potential issues
- ERROR: Serious problems that need attention
- CRITICAL: Critical errors that prevent the game from running

Logs are displayed in the console and include timestamps, module name, and log level.
