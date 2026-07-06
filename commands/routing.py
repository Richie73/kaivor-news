"""
Kaivor Task Routing
"""

from config.config import ConfigManager


def run():

    config = ConfigManager()

    routing = config.task_routing()

    print("\n========== TASK ROUTING ==========\n")

    for task, provider in routing.items():

        print(f"{task:<12} -> {provider}")

    print()
