"""
Kaivor Help Command
"""

from core.commands.base_command import BaseCommand


class HelpCommand(BaseCommand):
    """Displays available shell commands."""

    name = "help"
    aliases = []
    help_text = "Display available commands."

    def execute(self, text=None):

        commands = [
            ("help", "Display this help"),
            ("search <text>", "Search current workspace"),
            ("workspace list", "List workspaces"),
            ("workspace current", "Show active workspace"),
            ("workspace create <name>", "Create workspace"),
            ("workspace switch <name>", "Switch workspace"),
            ("note add <title>", "Create note"),
            ("note list", "List notes"),
            ("note open <title>", "Open note"),
            ("note delete <title>", "Delete note"),
            ("clear", "Clear screen"),
            ("exit", "Exit Kaivor"),
        ]

        print()
        print("Available Commands")
        print("-" * 60)

        for command, description in commands:
            print(f"{command:<28} {description}")

        print()
