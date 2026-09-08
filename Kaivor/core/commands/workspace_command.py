"""
Kaivor Workspace Command
"""

from core.commands.base_command import BaseCommand


class WorkspaceCommand(BaseCommand):
    """Handles workspace commands."""

    name = "workspace"
    aliases = []
    help_text = "Workspace management."

    def __init__(self, workspace):
        self.workspace = workspace

    def execute(self, text=None):

        parts = text.split()

        if len(parts) == 1:
            return self.current()

        command = parts[1].lower()

        if command == "list":
            return self.list()

        if command == "current":
            return self.current()

        if command == "create":

            if len(parts) < 3:
                print("Usage: workspace create <name>")
                return

            name = " ".join(parts[2:])

            self.workspace.create(name)

            print()
            print(f'Workspace "{name}" created.')
            print()

            return

        if command == "switch":

            if len(parts) < 3:
                print("Usage: workspace switch <name>")
                return

            name = " ".join(parts[2:])

            self.workspace.switch(name)

            print()
            print(f"Current workspace : {self.workspace.name()}")
            print()

            return

        print("Unknown workspace command.")

    def current(self):

        print()
        print(f"Current workspace : {self.workspace.name()}")
        print()

    def list(self):

        print()
        print("Available Workspaces")
        print("-" * 60)

        for name in self.workspace.list():

            marker = "* " if name == self.workspace.name() else "  "

            print(f"{marker}{name}")

        print()
