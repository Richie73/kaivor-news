"""
Kaivor
Main Application Launcher
"""

import sys

from core.logger import Logger
from core.app import run_application
from core.shell import InteractiveShell

from commands.ai import run as run_ai
from commands.analytics import run as analytics_command
from commands.ask import run as ask_command
from commands.benchmark import run as benchmark_command
from commands.capabilities import run as capabilities_command
from commands.doctor import run as doctor_command
from commands.models import run as models_command
from commands.providers import run as providers_command
from commands.recommend import run as recommend_command
from commands.routing import run as routing_command
from commands.search import run as search_command
from commands.status import run as status_command
from commands.system import run as system_command
from commands.test import run as run_tests
from commands.verify import run as verify_command
from commands.wallet import run as run_wallet


def run_cli():
    """Handle command-line mode."""

    # No command supplied -> launch interactive shell
    if len(sys.argv) <= 1:
        InteractiveShell().run()
        return True

    command = sys.argv[1].lower()

    commands = {
        "ai": run_ai,
        "analytics": analytics_command,
        "ask": ask_command,
        "benchmark": benchmark_command,
        "capabilities": capabilities_command,
        "doctor": doctor_command,
        "models": models_command,
        "providers": providers_command,
        "recommend": recommend_command,
        "routing": routing_command,
        "search": search_command,
        "status": status_command,
        "system": system_command,
        "test": run_tests,
        "verify": verify_command,
        "wallet": run_wallet,
    }

    action = commands.get(command)

    if action is None:
        print(f"Unknown command: {command}")
        return True

    if command in ("search", "ask"):

        if len(sys.argv) < 3:
            print(f"Usage: python kaivor.py {command} <text>")
            return True

        text = " ".join(sys.argv[2:])
        action(text)

    else:
        action()

    return True


def main():
    """Application entry point."""

    Logger.info("Kaivor started")

    if run_cli():
        return

    run_application()


if __name__ == "__main__":
    main()
