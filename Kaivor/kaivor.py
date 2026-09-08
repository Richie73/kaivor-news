"""
Kaivor
Main Application Launcher
"""

import sys

from core.logger import Logger


def run_cli():
    """Handle command-line mode with lazy command imports."""

    if len(sys.argv) <= 1:
        from core.app import run_application
        from core.shell import InteractiveShell
        InteractiveShell().run()
        return True

    command = sys.argv[1].lower()

    # Import only the selected command. This keeps isolated services such as
    # the API gateway from requiring unrelated optional subsystems at startup.
    command_modules = {
        "ai": ("commands.ai", "run"),
        "analytics": ("commands.analytics", "run"),
        "api": ("commands.api", "run"),
        "ask": ("commands.ask", "run"),
        "benchmark": ("commands.benchmark", "run"),
        "capabilities": ("commands.capabilities", "run"),
        "doctor": ("commands.doctor", "run"),
        "models": ("commands.models", "run"),
        "providers": ("commands.providers", "run"),
        "recommend": ("commands.recommend", "run"),
        "routing": ("commands.routing", "run"),
        "search": ("commands.search", "run"),
        "status": ("commands.status", "run"),
        "system": ("commands.system", "run"),
        "test": ("commands.test", "run"),
        "verify": ("commands.verify", "run"),
        "wallet": ("commands.wallet", "run"),
    }

    target = command_modules.get(command)
    if target is None:
        print(f"Unknown command: {command}")
        return True

    module_name, function_name = target
    module = __import__(module_name, fromlist=[function_name])
    action = getattr(module, function_name)

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

    from core.app import run_application
    run_application()


if __name__ == "__main__":
    main()
