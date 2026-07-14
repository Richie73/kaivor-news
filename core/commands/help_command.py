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

        print()
        print("Available Commands")
        print("-" * 60)
        print("help")
        print("clear")
        print("exit")
        print()
        print("search <text>")
        print()
        print("workspace list")
        print("workspace current")
        print("workspace create <name>")
        print("workspace switch <name>")
        print()
