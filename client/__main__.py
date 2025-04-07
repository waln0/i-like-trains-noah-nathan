import sys
from common.config import Config
from client.client import Client

# Load the config file
config_file = "config.json"
if len(sys.argv) > 1:
    config_file = sys.argv[1]
config = Config.load(config_file)

# TODO(alok): move this logger.into inside network, the connection isn't established here
# so this log doesn't belong here

# Create the client, agent, and start the client
client = Client(config)
client.run()