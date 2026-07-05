"""
Kaivor
Main Application Launcher
"""

import sys

from core.logger import Logger
from core.app import run_application

from commands.ai import run as run_ai
from commands.test import run as run_tests
from commands.wallet import run as run_wallet
from commands.doctor import run as doctor_command
from commands.providers import run as providers_command
from commands.system import run as system_command
from commands.status import run as status_command
from commands.benchmark import run as benchmark_command

def run_cli():
    """Handle command-line mode."""

    if len(sys.argv) <= 1:
        return False

    command = sys.argv[1].lower()

    commands = {
    "ai": run_ai,
    "test": run_tests,
    "wallet": run_wallet,
    "doctor": doctor_command,
    "providers": providers_command,
    "system": system_command,
    "status": status_command,
    "benchmark": benchmark_command,
}

    action = commands.get(command)

    if action is None:
        print(f"Unknown command: {command}")
        return True

    action()
    return True


def main():
    Logger.info("Kaivor started")

    if run_cli():
        return

    run_application()


if __name__ == "__main__":
    main()
