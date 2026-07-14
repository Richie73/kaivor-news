"""
Kaivor Exit Command
"""

from core.commands.base_command import BaseCommand


class ExitCommand(BaseCommand):
    """Exit Kaivor."""

    name = "exit"
    aliases = ["quit"]
    help_text = "Exit Kaivor."

    def execute(self, text=None):
        raise SystemExit
