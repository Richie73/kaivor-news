"""
Developer Mode Command
"""

from core.commands.base_command import BaseCommand


class DeveloperCommand(BaseCommand):
    """Launch Developer Mode."""

    name = "dev"
    aliases = ["developer"]
    help_text = "Launch Developer Mode."

    def __init__(self, manager):
        self.manager = manager

    def execute(self, text=None):
        self.manager.dashboard_view()
