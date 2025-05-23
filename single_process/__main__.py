import sys
from client.client import Client
from common.config import Config
from server.server import Server


def main():
    # Both, the client and server need to run on the main thread for different reasons:
    # - the server sets up signal handlers
    # - the client uses pygame
    #
    # For now, we keep both on the main thread and don't call server.run()
    # which we can fix later if it becomes an issue.

    # Load the config file
    config_file = "config.json"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    config = Config.load(config_file)

    # Override clients_per_room. The alternative would be to launch clients_per_room clients
    # but that might be too chaotic
    config.server.nb_clients_per_room = 1

    # Enables setting breakpoints and resuming the runtime without considering the client as disconnected
    config.server.client_timeout_seconds = 86400  # 86400 seconds == 1 day
    config.client.server_timeout_seconds = 86400  # 86400 seconds == 1 day
    config.server.waiting_time_before_bots_seconds = 0
    Server(config)

    client = Client(config)
    client.run()


main()
