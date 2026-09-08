"""
Kaivor Clear Command
"""

import os

from core.commands.base_command import BaseCommand


class ClearCommand(BaseCommand):
    """Clear the terminal."""

    name = "clear"
    aliases = ["cls"]
    help_text = "Clear the terminal."

    def execute(self, text=None):
        os.system("clear")
